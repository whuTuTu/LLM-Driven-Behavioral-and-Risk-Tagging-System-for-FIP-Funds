"""
指数数据加载器
用于读取和查询上证综合指数数据
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple


class IndexDataLoader:
    """指数数据加载器"""
    
    def __init__(self, index_file: str = None):
        """
        初始化指数数据加载器
        
        Args:
            index_file: 指数数据文件路径
        """
        if index_file is None:
            # 默认路径
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            index_file = os.path.join(base_dir, 'data', '指数.xlsx')
        
        self.index_file = index_file
        self.index_data = None
        self._load_index_data()
    
    def _load_index_data(self):
        """加载指数数据"""
        try:
            if not os.path.exists(self.index_file):
                print(f"指数数据文件不存在: {self.index_file}")
                return
            
            # 读取Excel文件，跳过前两行（标题行）
            df = pd.read_excel(self.index_file, skiprows=2)
            df.columns = ['指数代码', '交易日期', '收盘价']
            
            # 转换日期格式
            df['交易日期'] = pd.to_datetime(df['交易日期'])
            
            # 按日期排序
            df = df.sort_values('交易日期').reset_index(drop=True)
            
            self.index_data = df
            print(f"成功加载指数数据，共 {len(df)} 条记录")
            print(f"数据范围: {df['交易日期'].min().strftime('%Y-%m-%d')} 至 {df['交易日期'].max().strftime('%Y-%m-%d')}")
            
        except Exception as e:
            print(f"加载指数数据失败: {str(e)}")
            self.index_data = None
    
    def get_index_price(self, date: datetime) -> Optional[float]:
        """
        获取指定日期的指数收盘价
        
        Args:
            date: 查询日期
            
        Returns:
            指数收盘价，如果不存在则返回None
        """
        if self.index_data is None:
            return None
        
        try:
            # 查找最近的交易日
            mask = self.index_data['交易日期'] <= date
            if not mask.any():
                return None
            
            # 获取最近的交易日数据
            latest_date = self.index_data[mask]['交易日期'].max()
            price = self.index_data[self.index_data['交易日期'] == latest_date]['收盘价'].values[0]
            
            return float(price)
            
        except Exception as e:
            print(f"获取指数价格失败: {str(e)}")
            return None
    
    def get_quarter_index_change(self, report_date: datetime) -> Optional[Tuple[float, float]]:
        """
        获取报告期对应季度的指数涨跌幅
        
        Args:
            report_date: 报告期日期
            
        Returns:
            (季度初价格, 季度末价格, 涨跌幅%)，如果数据不足则返回None
        """
        if self.index_data is None:
            return None
        
        try:
            # 确定季度初和季度末日期
            year = report_date.year
            month = report_date.month
            
            # 根据报告期月份确定季度
            if month <= 3:
                # 第一季度报告（通常是年报，截止日期为12月31日）
                quarter_start = datetime(year - 1, 10, 1)
                quarter_end = datetime(year - 1, 12, 31)
            elif month <= 6:
                # 第二季度报告（一季报，截止日期为3月31日）
                quarter_start = datetime(year, 1, 1)
                quarter_end = datetime(year, 3, 31)
            elif month <= 9:
                # 第三季度报告（半年报，截止日期为6月30日）
                quarter_start = datetime(year, 4, 1)
                quarter_end = datetime(year, 6, 30)
            else:
                # 第四季度报告（三季报，截止日期为9月30日）
                quarter_start = datetime(year, 7, 1)
                quarter_end = datetime(year, 9, 30)
            
            # 获取季度初价格
            start_price = self.get_index_price(quarter_start)
            if start_price is None:
                return None
            
            # 获取季度末价格
            end_price = self.get_index_price(quarter_end)
            if end_price is None:
                return None
            
            # 计算涨跌幅
            change_pct = (end_price - start_price) / start_price * 100
            
            return (start_price, end_price, change_pct)
            
        except Exception as e:
            print(f"获取季度指数变化失败: {str(e)}")
            return None
    
    def get_previous_quarter_index_change(self, report_date: datetime) -> Optional[Tuple[float, float]]:
        """
        获取上一季度的指数涨跌幅
        
        Args:
            report_date: 报告期日期
            
        Returns:
            (季度初价格, 季度末价格, 涨跌幅%)，如果数据不足则返回None
        """
        if self.index_data is None:
            return None
        
        try:
            # 确定上一季度的日期范围
            year = report_date.year
            month = report_date.month
            
            # 根据报告期月份确定上一季度
            if month <= 3:
                # 第一季度报告，上一季度是去年Q3
                quarter_start = datetime(year - 1, 7, 1)
                quarter_end = datetime(year - 1, 9, 30)
            elif month <= 6:
                # 第二季度报告，上一季度是去年Q4
                quarter_start = datetime(year - 1, 10, 1)
                quarter_end = datetime(year - 1, 12, 31)
            elif month <= 9:
                # 第三季度报告，上一季度是今年Q1
                quarter_start = datetime(year, 1, 1)
                quarter_end = datetime(year, 3, 31)
            else:
                # 第四季度报告，上一季度是今年Q2
                quarter_start = datetime(year, 4, 1)
                quarter_end = datetime(year, 6, 30)
            
            # 获取季度初价格
            start_price = self.get_index_price(quarter_start)
            if start_price is None:
                return None
            
            # 获取季度末价格
            end_price = self.get_index_price(quarter_end)
            if end_price is None:
                return None
            
            # 计算涨跌幅
            change_pct = (end_price - start_price) / start_price * 100
            
            return (start_price, end_price, change_pct)
            
        except Exception as e:
            print(f"获取上一季度指数变化失败: {str(e)}")
            return None


# 全局单例
_index_loader = None


def get_index_loader() -> IndexDataLoader:
    """获取指数数据加载器单例"""
    global _index_loader
    if _index_loader is None:
        _index_loader = IndexDataLoader()
    return _index_loader
