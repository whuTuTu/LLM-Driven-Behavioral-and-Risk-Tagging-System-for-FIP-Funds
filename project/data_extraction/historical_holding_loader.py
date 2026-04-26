"""
历史持仓数据加载器
用于加载和查询历史持仓数据，计算仓位变化
"""

import os
import re
import json
from datetime import datetime
from typing import Dict, Optional, Tuple
import pandas as pd


class HistoricalHoldingLoader:
    """历史持仓数据加载器"""
    
    def __init__(self, extracted_data_dir: str = None):
        """
        初始化历史持仓数据加载器
        
        Args:
            extracted_data_dir: 提取数据目录
        """
        if extracted_data_dir is None:
            # 默认路径
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            extracted_data_dir = os.path.join(base_dir, 'output', 'fund_analysis', 'extracted_data')
        
        self.extracted_data_dir = extracted_data_dir
        self.holding_cache = {}  # 缓存已加载的持仓数据
    
    def _parse_report_info(self, filename: str) -> Optional[Tuple[str, datetime]]:
        """
        从文件名解析基金名称和报告期日期
        
        Args:
            filename: 文件名
            
        Returns:
            (基金名称, 报告期日期)
        """
        try:
            # 移除"_提取结果.md"后缀
            name = filename.replace('_提取结果.md', '')
            
            # 匹配年份
            year_match = re.search(r'(\d{4})年', name)
            if not year_match:
                return None
            
            year = int(year_match.group(1))
            
            # 匹配报告类型并确定日期
            if '年度报告' in name or '年报' in name:
                report_date = datetime(year, 12, 31)
            elif '中期报告' in name or '半年报' in name:
                report_date = datetime(year, 6, 30)
            elif '第1季度' in name or '一季报' in name:
                report_date = datetime(year, 3, 31)
            elif '第2季度' in name:
                report_date = datetime(year, 6, 30)
            elif '第3季度' in name or '三季报' in name:
                report_date = datetime(year, 9, 30)
            elif '第4季度' in name:
                report_date = datetime(year, 12, 31)
            else:
                return None
            
            # 提取基金名称（移除年份和报告类型）
            fund_name = re.sub(r'\d{4}年.*$', '', name).strip()
            
            return (fund_name, report_date)
            
        except Exception as e:
            print(f"解析报告信息失败: {str(e)}")
            return None
    
    def _load_holding_data(self, filename: str) -> Optional[Dict]:
        """
        加载单个文件的持仓数据
        
        Args:
            filename: 文件名
            
        Returns:
            持仓数据字典
        """
        try:
            filepath = os.path.join(self.extracted_data_dir, filename)
            
            if not os.path.exists(filepath):
                return None
            
            # 读取markdown文件
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取持仓数据部分
            # 查找"## 4. 投资组合数据提取器"部分
            holding_section = re.search(r'## 4\. 投资组合数据提取器\s*```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            
            if not holding_section:
                return None
            
            # 解析JSON
            holding_data = json.loads(holding_section.group(1))
            
            return holding_data
            
        except Exception as e:
            print(f"加载持仓数据失败 {filename}: {str(e)}")
            return None
    
    def _extract_risk_asset_ratio(self, holding_data: Dict) -> Optional[float]:
        """
        从持仓数据中提取风险资产占比
        
        Args:
            holding_data: 持仓数据
            
        Returns:
            风险资产占比（股票+可转债）
        """
        try:
            # 获取资产组合情况
            asset_allocation = holding_data.get('报告期末基金资产组合情况', {})
            
            if not asset_allocation:
                return None
            
            # 提取权益投资占比
            equity_ratio_str = asset_allocation.get('权益投资', '0%')
            equity_match = re.search(r'(\d+\.\d+)', equity_ratio_str)
            equity_ratio = float(equity_match.group(1)) if equity_match else 0.0
            
            # 提取可转债占比
            bond_portfolio = holding_data.get('按债券品种分类的债券投资组合', {})
            convertible_ratio = 0.0
            
            for key in ['可转债（可交换债）', '可转债', '可交换债']:
                if key in bond_portfolio:
                    convertible_match = re.search(r'(\d+\.\d+)', str(bond_portfolio[key]))
                    if convertible_match:
                        convertible_ratio = float(convertible_match.group(1))
                        break
            
            # 总风险资产占比
            total_risk_ratio = equity_ratio + convertible_ratio
            
            return total_risk_ratio
            
        except Exception as e:
            print(f"提取风险资产占比失败: {str(e)}")
            return None
    
    def get_previous_quarter_holding(self, fund_name: str, current_report_date: datetime) -> Optional[Tuple[datetime, float]]:
        """
        获取上一季度的持仓数据
        
        Args:
            fund_name: 基金名称
            current_report_date: 当前报告期日期
            
        Returns:
            (上一季度报告期日期, 风险资产占比)
        """
        try:
            # 确定上一季度的报告期日期
            year = current_report_date.year
            month = current_report_date.month
            
            if month <= 3:
                # 第一季度报告，上一季度是去年Q3（三季报）
                prev_report_date = datetime(year - 1, 9, 30)
            elif month <= 6:
                # 第二季度报告（一季报），上一季度是去年Q4（年报）
                prev_report_date = datetime(year - 1, 12, 31)
            elif month <= 9:
                # 第三季度报告（半年报），上一季度是今年Q1（一季报）
                prev_report_date = datetime(year, 3, 31)
            else:
                # 第四季度报告（三季报），上一季度是今年Q2（半年报）
                prev_report_date = datetime(year, 6, 30)
            
            # 构建上一季度报告的文件名
            prev_filename = self._construct_filename(fund_name, prev_report_date)
            
            if prev_filename is None:
                return None
            
            # 加载持仓数据
            holding_data = self._load_holding_data(prev_filename)
            
            if holding_data is None:
                return None
            
            # 提取风险资产占比
            risk_ratio = self._extract_risk_asset_ratio(holding_data)
            
            if risk_ratio is None:
                return None
            
            return (prev_report_date, risk_ratio)
            
        except Exception as e:
            print(f"获取上一季度持仓失败: {str(e)}")
            return None
    
    def _construct_filename(self, fund_name: str, report_date: datetime) -> Optional[str]:
        """
        构建报告文件名
        
        Args:
            fund_name: 基金名称
            report_date: 报告期日期
            
        Returns:
            文件名
        """
        try:
            year = report_date.year
            month = report_date.month
            
            # 确定报告类型
            if month == 3:
                report_type = '第1季度报告'
            elif month == 6:
                # 需要区分一季报和半年报，这里假设是半年报
                report_type = '中期报告'
            elif month == 9:
                report_type = '第3季度报告'
            elif month == 12:
                report_type = '年度报告'
            else:
                return None
            
            filename = f"{fund_name}{year}年{report_type}_提取结果.md"
            
            # 检查文件是否存在
            filepath = os.path.join(self.extracted_data_dir, filename)
            if not os.path.exists(filepath):
                # 尝试其他可能的命名方式
                if month == 6:
                    # 尝试一季报
                    alt_filename = f"{fund_name}{year}年第2季度报告_提取结果.md"
                    alt_filepath = os.path.join(self.extracted_data_dir, alt_filename)
                    if os.path.exists(alt_filepath):
                        return alt_filename
                return None
            
            return filename
            
        except Exception as e:
            print(f"构建文件名失败: {str(e)}")
            return None


# 全局单例
_historical_holding_loader = None


def get_historical_holding_loader() -> HistoricalHoldingLoader:
    """获取历史持仓数据加载器单例"""
    global _historical_holding_loader
    if _historical_holding_loader is None:
        _historical_holding_loader = HistoricalHoldingLoader()
    return _historical_holding_loader
