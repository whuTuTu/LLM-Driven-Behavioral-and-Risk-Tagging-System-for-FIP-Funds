"""
宏观观点提取器（改进版）
按章节划分提取，支持不同报告类型
"""

import re
from typing import Dict
from .base_extractor import BaseExtractor


class MacroViewExtractor(BaseExtractor):
    """基金经理宏观研判和大类资产观点提取器"""
    
    def __init__(self, fund_type: str = 'UNKNOWN'):
        """
        初始化提取器
        
        Args:
            fund_type: 基金类型代码（SECONDARY_BOND/CONVERTIBLE_BOND/UNKNOWN）
        """
        super().__init__()
        self.fund_type = fund_type
    
    def set_fund_type(self, fund_type: str):
        """
        设置基金类型
        
        Args:
            fund_type: 基金类型代码
        """
        self.fund_type = fund_type
    
    def extract(self, text: str, report_type: str = 'Q1') -> Dict:
        """
        提取基金经理宏观研判和大类资产观点的原始文本
        
        Args:
            text: 报告文本
            report_type: 报告类型
            
        Returns:
            提取的原始文本数据
        """
        # 1. 提取投资策略和运作分析章节
        strategy_text = self._extract_strategy_section(text, report_type)
        
        # 2. 提取宏观经济展望章节（如果有）
        macro_outlook_text = self._extract_macro_outlook_section(text, report_type)
        
        # 3. 返回原始文本数据
        macro_data = {
            "投资策略和运作分析": strategy_text,
            "宏观经济展望": macro_outlook_text,
            "报告类型": report_type,
            "基金类型": self.fund_type
        }
        
        return macro_data
    
    def _extract_strategy_section(self, text: str, report_type: str) -> str:
        """
        提取投资策略和运作分析章节（按章节划分）
        
        Args:
            text: 报告全文
            report_type: 报告类型
            
        Returns:
            投资策略章节文本
        """
        # 提取§4 管理人报告章节
        # 注意：年度报告和中期报告有目录页，第一个§4是目录，需要找第二个
        # 注意：目录页的§4标题可能包含点号，如"§4管理人报告..........................................."
        # 【修复】支持两种格式：
        # 1. 旧格式: §4 管理人报告
        # 2. 新格式(2025年起): 管理人报告 (无§符号)
        section4_matches = list(re.finditer(r'§4\s*管理人报告[^\n]*\s*(.*?)(?=§5|$)', text, re.DOTALL))
        
        # 如果旧格式未匹配，尝试新格式
        if not section4_matches:
            section4_matches = list(re.finditer(r'管理人报告\s*(.*?)(?=托管人报告|$)', text, re.DOTALL))
        
        if not section4_matches:
            return ""
        
        # 如果有多个匹配，选择内容最长的那个（跳过目录页）
        section4_text = max([m.group(1) for m in section4_matches], key=len)
        
        # 根据报告类型提取4.4章节
        # 匹配章节标题，然后提取到下一个子章节或章节结束
        # 注意：PDF中章节编号后可能有空格也可能没有
        # 注意：季度报告标题有"的"字，中期/年度报告标题没有"的"字
        
        # 季度报告匹配模式
        quarterly_pattern = r'4\.4\s*报告期内基金的投资策略和运作分析\s*(.*?)(?=4\.5\s*报告期内基金的业绩表现|$)'
        # 年度/中期报告匹配模式
        annual_pattern = r'4\.4\.1\s*报告期内基金投资策略和运作分析\s*(.*?)(?=4\.4\.2\s*报告期内基金的业绩表现|$)'
        
        strategy_match = None
        
        if report_type in ['Q1', 'Q2', 'Q3', 'Q4']:
            # 先尝试季度报告模式
            strategy_match = re.search(quarterly_pattern, section4_text, re.DOTALL)
            # 如果匹配失败，尝试年度报告模式（有些季报格式类似年报）
            if not strategy_match:
                strategy_match = re.search(annual_pattern, section4_text, re.DOTALL)
        elif report_type in ['Semi-Annual', 'Annual']:
            # 先尝试年度报告模式
            strategy_match = re.search(annual_pattern, section4_text, re.DOTALL)
            # 如果匹配失败，尝试季度报告模式
            if not strategy_match:
                strategy_match = re.search(quarterly_pattern, section4_text, re.DOTALL)
        
        if strategy_match:
            return strategy_match.group(1).strip()
        
        return ""
    
    def _extract_macro_outlook_section(self, text: str, report_type: str) -> str:
        """
        提取宏观经济展望章节
        
        Args:
            text: 报告全文
            report_type: 报告类型
            
        Returns:
            宏观经济展望章节文本
        """
        # 提取§4 管理人报告章节
        # 注意：年度报告和中期报告有目录页，第一个§4是目录，需要找第二个
        # 注意：目录页的§4标题可能包含点号，如"§4管理人报告..........................................."
        # 【修复】支持两种格式：
        # 1. 旧格式: §4 管理人报告
        # 2. 新格式(2025年起): 管理人报告 (无§符号)
        section4_matches = list(re.finditer(r'§4\s*管理人报告[^\n]*\s*(.*?)(?=§5|$)', text, re.DOTALL))
        
        # 如果旧格式未匹配，尝试新格式
        if not section4_matches:
            section4_matches = list(re.finditer(r'管理人报告\s*(.*?)(?=托管人报告|$)', text, re.DOTALL))
        
        if not section4_matches:
            return ""
        
        # 如果有多个匹配，选择内容最长的那个（跳过目录页）
        section4_text = max([m.group(1) for m in section4_matches], key=len)

        strategy_match = None
        
        if report_type in ['Q1', 'Q2', 'Q3', 'Q4']:
            # 季度报告通常没有宏观经济展望章节
            return ""
        elif report_type in ['Semi-Annual', 'Annual']:
            strategy_match = re.search(
                r'4\.5\s*管理人对宏观经济、证券市场及行业走势的简要展望\s*(.*?)(?=4\.6|$)', 
                section4_text, 
                re.DOTALL
            )
        
        if strategy_match:
            return strategy_match.group(1).strip()
        
        return ""
