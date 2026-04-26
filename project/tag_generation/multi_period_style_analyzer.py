"""
多期风格分析器
分析基金经理的长期和短期投资风格，评估风格稳定性
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np


class MultiPeriodStyleAnalyzer:
    """多期风格分析器"""
    
    def __init__(self, extracted_data_dir: str = None):
        """
        初始化多期风格分析器
        
        Args:
            extracted_data_dir: 提取数据目录
        """
        if extracted_data_dir is None:
            # 默认路径
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            extracted_data_dir = os.path.join(base_dir, 'output', 'fund_analysis', 'extracted_data')
        
        self.extracted_data_dir = extracted_data_dir
    
    def analyze_style_stability(self, fund_name: str, current_report_date: datetime, 
                                current_style_score: float, num_periods: int = 8) -> Dict:
        """
        分析投资风格的稳定性
        
        Args:
            fund_name: 基金名称
            current_report_date: 当前报告期日期
            current_style_score: 当前风格得分
            num_periods: 分析的期数（默认8期，约2年）
            
        Returns:
            风格稳定性分析结果
        """
        try:
            # 获取历史各期的风格得分
            historical_scores = self._get_historical_style_scores(
                fund_name, current_report_date, num_periods
            )
            
            # 添加当前期得分
            all_scores = historical_scores + [current_style_score]
            
            if len(all_scores) < 2:
                return {
                    '长期风格': '数据不足',
                    '短期风格': self._score_to_style(current_style_score),
                    '风格稳定性': '数据不足',
                    '风格演变趋势': '数据不足',
                    '分析期数': len(all_scores)
                }
            
            # 计算短期风格（最近1-2期）
            short_term_score = np.mean(all_scores[-2:]) if len(all_scores) >= 2 else all_scores[-1]
            short_term_style = self._score_to_style(short_term_score)
            
            # 计算长期风格（所有期）
            long_term_score = np.mean(all_scores)
            long_term_style = self._score_to_style(long_term_score)
            
            # 计算风格稳定性
            stability = self._calculate_stability(all_scores)
            
            # 分析风格演变趋势
            trend = self._analyze_trend(all_scores)
            
            # 判断风格一致性
            consistency = self._check_consistency(all_scores)
            
            return {
                '长期风格': long_term_style,
                '长期风格得分': round(long_term_score, 2),
                '短期风格': short_term_style,
                '短期风格得分': round(short_term_score, 2),
                '风格稳定性': stability,
                '风格演变趋势': trend,
                '风格一致性': consistency,
                '分析期数': len(all_scores),
                '各期得分': [round(s, 2) for s in all_scores],
                '风格波动率': round(np.std(all_scores), 2)
            }
            
        except Exception as e:
            print(f"风格稳定性分析失败: {str(e)}")
            return {
                '长期风格': '分析失败',
                '短期风格': '分析失败',
                '风格稳定性': '分析失败',
                '错误信息': str(e)
            }
    
    def _get_historical_style_scores(self, fund_name: str, current_report_date: datetime, 
                                    num_periods: int) -> List[float]:
        """
        获取历史各期的风格得分
        
        Args:
            fund_name: 基金名称
            current_report_date: 当前报告期日期
            num_periods: 期数
            
        Returns:
            历史风格得分列表
        """
        scores = []
        
        try:
            # 获取历史各期的报告日期
            report_dates = self._get_historical_report_dates(current_report_date, num_periods)
            
            for report_date in report_dates:
                # 加载该期的提取数据
                extracted_data = self._load_period_data(fund_name, report_date)
                
                if extracted_data:
                    # 计算该期的风格得分（简化版，只看持仓）
                    score = self._calculate_period_style_score(extracted_data)
                    if score is not None:
                        scores.append(score)
            
            return scores
            
        except Exception as e:
            print(f"获取历史风格得分失败: {str(e)}")
            return []
    
    def _get_historical_report_dates(self, current_date: datetime, num_periods: int) -> List[datetime]:
        """
        获取历史各期的报告日期
        
        Args:
            current_date: 当前报告期日期
            num_periods: 期数
            
        Returns:
            历史报告日期列表
        """
        dates = []
        year = current_date.year
        month = current_date.month
        
        for i in range(1, num_periods + 1):
            # 计算上一期的日期
            month -= 3
            if month <= 0:
                month += 12
                year -= 1
            
            # 确定报告期截止日期
            if month <= 3:
                report_date = datetime(year, 3, 31)
            elif month <= 6:
                report_date = datetime(year, 6, 30)
            elif month <= 9:
                report_date = datetime(year, 9, 30)
            else:
                report_date = datetime(year, 12, 31)
            
            dates.append(report_date)
        
        return dates
    
    def _load_period_data(self, fund_name: str, report_date: datetime) -> Optional[Dict]:
        """
        加载某期的提取数据
        
        Args:
            fund_name: 基金名称
            report_date: 报告期日期
            
        Returns:
            提取数据
        """
        try:
            # 构建文件名
            year = report_date.year
            month = report_date.month
            
            if month == 3:
                report_type = '第1季度报告'
            elif month == 6:
                report_type = '中期报告'
            elif month == 9:
                report_type = '第3季度报告'
            else:
                report_type = '年度报告'
            
            filename = f"{fund_name}{year}年{report_type}_提取结果.md"
            filepath = os.path.join(self.extracted_data_dir, filename)
            
            if not os.path.exists(filepath):
                return None
            
            # 读取并解析MD文件
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取持仓数据
            holding_section = re.search(r'## 4\. 投资组合数据提取器\s*```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            
            if holding_section:
                holding_data = json.loads(holding_section.group(1))
                return {'持仓数据': holding_data}
            
            return None
            
        except Exception as e:
            return None
    
    def _calculate_period_style_score(self, extracted_data: Dict) -> Optional[float]:
        """
        计算某期的风格得分（简化版，只看持仓）
        
        Args:
            extracted_data: 提取数据
            
        Returns:
            风格得分
        """
        try:
            holding_data = extracted_data.get('持仓数据', {})
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
            
            # 简单映射为得分
            if total_risk_ratio >= 20:
                return 0.4
            elif total_risk_ratio >= 10:
                return 0.0
            else:
                return -0.3
            
        except Exception as e:
            return None
    
    def _score_to_style(self, score: float) -> str:
        """
        将得分转换为风格标签
        
        Args:
            score: 风格得分
            
        Returns:
            风格标签
        """
        if score <= -0.3:
            return '左侧布局'
        elif score >= 0.3:
            return '右侧跟随'
        else:
            return '均衡配置'
    
    def _calculate_stability(self, scores: List[float]) -> str:
        """
        计算风格稳定性
        
        Args:
            scores: 各期得分
            
        Returns:
            稳定性评级
        """
        if len(scores) < 3:
            return '数据不足'
        
        # 计算标准差
        std = np.std(scores)
        
        # 计算得分变化范围
        score_range = max(scores) - min(scores)
        
        # 判断稳定性
        if std < 0.15 and score_range < 0.4:
            return '高度稳定'
        elif std < 0.25 and score_range < 0.6:
            return '较为稳定'
        elif std < 0.35:
            return '适度变化'
        else:
            return '风格多变'
    
    def _analyze_trend(self, scores: List[float]) -> str:
        """
        分析风格演变趋势
        
        Args:
            scores: 各期得分（按时间顺序）
            
        Returns:
            趋势描述
        """
        if len(scores) < 3:
            return '数据不足'
        
        # 计算趋势（简单线性回归斜率）
        x = np.arange(len(scores))
        slope = np.polyfit(x, scores, 1)[0]
        
        # 判断趋势
        if slope > 0.05:
            return '向右侧演变'
        elif slope < -0.05:
            return '向左侧演变'
        else:
            return '风格保持'
    
    def _check_consistency(self, scores: List[float]) -> str:
        """
        检查风格一致性
        
        Args:
            scores: 各期得分
            
        Returns:
            一致性描述
        """
        if len(scores) < 3:
            return '数据不足'
        
        # 统计各风格出现次数
        left_count = sum(1 for s in scores if s < -0.3)
        right_count = sum(1 for s in scores if s > 0.3)
        neutral_count = len(scores) - left_count - right_count
        
        # 判断主要风格
        total = len(scores)
        if left_count / total > 0.6:
            return f'一致左侧（{left_count}/{total}期）'
        elif right_count / total > 0.6:
            return f'一致右侧（{right_count}/{total}期）'
        elif neutral_count / total > 0.6:
            return f'一致均衡（{neutral_count}/{total}期）'
        else:
            return f'风格不固定（左{left_count}/右{right_count}/均衡{neutral_count}）'
