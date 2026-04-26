"""
基础提取器类
提供PDF文本提取、章节识别等通用功能
"""

import os
import re
import PyPDF2
from typing import Dict, Optional
from abc import ABC, abstractmethod


class BaseExtractor(ABC):
    """基础提取器抽象类"""
    
    def __init__(self):
        """初始化提取器"""
        pass
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        从PDF文件中提取文本
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            提取的文本内容
        """
        text = ""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"提取PDF文本失败 {pdf_path}: {e}")
        
        return text
    
    def parse_report_info(self, filename: str) -> Dict:
        """
        解析报告文件名，提取基金名称和报告类型
        
        Args:
            filename: 文件名
            
        Returns:
            包含基金名称、报告类型、年份等信息的字典
        """
        info = {}
        
        # 提取基金名称
        match = re.search(r'(.+?)\d{4}年', filename)
        if match:
            info['fund_name'] = match.group(1)
        
        # 提取年份
        match = re.search(r'(\d{4})年', filename)
        if match:
            info['year'] = match.group(1)
        
        # 提取报告类型
        if '第1季度' in filename:
            info['report_type'] = 'Q1'
            info['period'] = '第一季度'
        elif '第2季度' in filename:
            info['report_type'] = 'Q2'
            info['period'] = '第二季度'
        elif '第3季度' in filename:
            info['report_type'] = 'Q3'
            info['period'] = '第三季度'
        elif '第4季度' in filename:
            info['report_type'] = 'Q4'
            info['period'] = '第四季度'
        elif '中期报告' in filename:
            info['report_type'] = 'Semi-Annual'
            info['period'] = '中期'
        elif '年度报告' in filename:
            info['report_type'] = 'Annual'
            info['period'] = '年度'
        
        return info
    
    def _extract_section_by_number(self, text: str, section_num: str, next_section_num: str) -> str:
        """
        根据章节编号提取完整章节内容
        
        Args:
            text: 报告全文
            section_num: 章节编号（如 '§4'）
            next_section_num: 下一章节编号（如 '§5'）
            
        Returns:
            章节内容
        """
        pattern = rf'{re.escape(section_num)}\s*[^\n]+(.*?)(?={re.escape(next_section_num)}\s|$)'
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        return ""
    
    def _extract_subsection(self, section_text: str, subsection_num: str) -> str:
        """
        从章节中提取子章节内容
        
        Args:
            section_text: 章节文本
            subsection_num: 子章节编号（如 '4.1'）
            
        Returns:
            子章节内容
        """
        if not section_text:
            return ""
        
        pattern = rf'{re.escape(subsection_num)}[^\n]+(.*?)(?=\d+\.\d+\s|$)'
        match = re.search(pattern, section_text, re.DOTALL)
        
        if match:
            return match.group(1).strip()
        return ""
    
    @abstractmethod
    def extract(self, text: str, report_type: str = 'Q1') -> Dict:
        """
        提取数据的抽象方法，子类必须实现
        
        Args:
            text: 报告文本
            report_type: 报告类型
            
        Returns:
            提取的数据字典
        """
        pass
