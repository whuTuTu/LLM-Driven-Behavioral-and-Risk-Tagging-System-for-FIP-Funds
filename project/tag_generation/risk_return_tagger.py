"""
收益风险标签生成器
基于业绩数据和净值数据生成收益风险相关标签，并转换为定性评估标签（双轨制）
"""

import os
import numpy as np
import pandas as pd
from typing import Dict, Optional
from datetime import datetime, timedelta


class RiskReturnTagger:
    """收益风险标签生成器"""
    
    def __init__(self, nav_data_dir: str = "data/fund_nav"):
        """
        初始化标签生成器
        
        Args:
            nav_data_dir: 净值数据目录
        """
        self.nav_data_dir = nav_data_dir
    
    def generate(self, extracted_data) -> Dict:
        """
        生成收益风险标签

        Args:
            extracted_data: 提取的数据（可以是字典或基金名称字符串）

        Returns:
            定性化后的收益风险标签
        """
        # 获取基金名称（支持字符串或字典参数）
        if isinstance(extracted_data, str):
            fund_name = extracted_data
        else:
            fund_name = extracted_data.get('基金名称', '')
        
        # 1. 计算所有底层量化指标
        if fund_name:
            raw_metrics = self._calculate_nav_metrics(fund_name)
        else:
            raw_metrics = self._get_default_nav_metrics()
            
        # 2. 将冷冰冰的数据转换为“定性标签”（核心逻辑）
        tags = self._generate_qualitative_tags(raw_metrics, fund_name)
        
        return tags

    def _identify_fund_type(self, fund_name: str) -> str:
        """识别基金类型，用于动态分配评价阈值"""
        if not fund_name:
            return 'SECONDARY_BOND'
        if '转债' in fund_name or '可转债' in fund_name:
            return 'CONVERTIBLE_BOND'
        return 'SECONDARY_BOND'

    def _generate_qualitative_tags(self, metrics: Dict, fund_name: str) -> Dict:
        """
        将原始量化数据转换为带有业务研判的定性标签
        """
        fund_type = self._identify_fund_type(fund_name)
        tags = {}

        # ==========================================
        # 1. 长期收益能力 (基于近三年收益率)
        # ==========================================
        ret_3y_str = metrics.get('近三年收益率', 'N/A')
        if ret_3y_str != 'N/A':
            val = float(ret_3y_str.replace('%', ''))
            annual_ret = val / 3.0  # 粗略年化
            
            if fund_type == 'CONVERTIBLE_BOND':
                if annual_ret >= 6.0: tag = "高收益特征"
                elif annual_ret >= 3.0: tag = "中等收益特征"
                else: tag = "低收益特征"
            else: # 二级债基
                if annual_ret >= 4.0: tag = "高收益特征"
                elif annual_ret >= 2.0: tag = "中等收益特征"
                else: tag = "低收益特征"
                
            tags['长期收益能力'] = f"{tag} (近三年{ret_3y_str})"
        else:
            tags['长期收益能力'] = "数据不足"

        # ==========================================
        # 2. 回撤控制水平 (基于最大回撤)
        # ==========================================
        mdd_str = metrics.get('最大回撤', 'N/A')
        if mdd_str != 'N/A':
            val = float(mdd_str.replace('%', ''))
            # 注意：最大回撤是负数，比如 -1.81%
            if fund_type == 'CONVERTIBLE_BOND':
                if val >= -8.0: tag = "回撤控制极佳"
                elif val >= -15.0: tag = "回撤控制良好"
                else: tag = "回撤控制较弱"
            else: # 二级债基
                if val >= -3.0: tag = "回撤控制极佳"
                elif val >= -6.0: tag = "回撤控制良好"
                else: tag = "回撤控制较弱"
                
            tags['回撤控制水平'] = f"{tag} (最大回撤{mdd_str})"
        else:
            tags['回撤控制水平'] = "数据不足"

        # ==========================================
        # 3. 业绩波动特征 (基于近三年标准差)
        # ==========================================
        vol_3y_str = metrics.get('近三年标准差', 'N/A')
        if vol_3y_str != 'N/A':
            val = float(vol_3y_str.replace('%', ''))
            
            if fund_type == 'CONVERTIBLE_BOND':
                if val < 8.0: tag = "稳健低波"
                elif val <= 15.0: tag = "弹性中波"
                else: tag = "高波高弹"
            else: # 二级债基
                if val < 3.0: tag = "稳健低波"
                elif val <= 6.0: tag = "弹性中波"
                else: tag = "高波高弹"
                
            tags['业绩波动特征'] = f"{tag} (年化波动{vol_3y_str})"
        else:
            tags['业绩波动特征'] = "数据不足"

        # ==========================================
        # 4. 风险调整后收益 (基于夏普比率)
        # ==========================================
        sharpe_str = metrics.get('夏普比率', 'N/A')
        if sharpe_str != 'N/A':
            val = float(sharpe_str)
            if val >= 1.0: tag = "性价比极高"
            elif val >= 0.5: tag = "性价比良好"
            else: tag = "性价比一般"
            tags['风险调整后收益'] = f"{tag} (夏普比率{sharpe_str})"
        else:
            tags['风险调整后收益'] = "数据不足"

        # ==========================================
        # 5. 超额获取能力 (基于近三年超额)
        # ==========================================
        exc_3y_str = metrics.get('近三年超额收益', 'N/A')
        if exc_3y_str != 'N/A':
            val = float(exc_3y_str.replace('%', ''))
            if val >= 5.0: tag = "超额获取能力强"
            elif val >= 0.0: tag = "具有超额能力"
            else: tag = "长期跑输基准"
            tags['超额获取能力'] = f"{tag} (近三年超额{exc_3y_str})"
        else:
            tags['超额获取能力'] = "数据不足"

        # ==========================================
        # 6. 胜率特征
        # ==========================================
        win_str = metrics.get('胜率', 'N/A')
        if win_str != 'N/A':
            val = float(win_str.replace('%', ''))
            if val >= 60.0: tag = "极高胜率"
            elif val >= 55.0: tag = "中高胜率"
            else: tag = "一般胜率"
            tags['胜率特征'] = f"{tag} (日胜率{win_str})"
        else:
            tags['胜率特征'] = "数据不足"

        # 将原有的生硬数据折叠保存，供前端或后续报告提取备用
        tags['基础量化指标'] = metrics

        return tags
    
    # -------------------------------------------------------------------------
    # 下方为原有底层数据计算方法，保持不变，仅供 _calculate_nav_metrics 调用
    # -------------------------------------------------------------------------
    def _extract_return_metrics(self, performance_data: Dict) -> Dict:
        metrics = {}
        if performance_data.get('基金分类') == 'A/C类':
            a_class = performance_data.get('A类基金', {})
            metrics['近一年收益率'] = f"{a_class['过去一年收益率']}%" if a_class.get('过去一年收益率') else 'N/A'
            metrics['近两年收益率'] = f"{a_class['过去两年收益率']}%" if a_class.get('过去两年收益率') else 'N/A'
            metrics['近三年收益率'] = f"{a_class['过去三年收益率']}%" if a_class.get('过去三年收益率') else 'N/A'
        else:
            metrics['近一年收益率'] = f"{performance_data['过去一年收益率']}%" if performance_data.get('过去一年收益率') else 'N/A'
            metrics['近两年收益率'] = f"{performance_data['过去两年收益率']}%" if performance_data.get('过去两年收益率') else 'N/A'
            metrics['近三年收益率'] = f"{performance_data['过去三年收益率']}%" if performance_data.get('过去三年收益率') else 'N/A'
        return metrics
    
    def _extract_risk_metrics(self, performance_data: Dict) -> Dict:
        metrics = {}
        if performance_data.get('基金分类') == 'A/C类':
            a_class = performance_data.get('A类基金', {})
            metrics['近一年标准差'] = f"{a_class['过去一年标准差']}%" if a_class.get('过去一年标准差') else 'N/A'
            metrics['近两年标准差'] = f"{a_class['过去两年标准差']}%" if a_class.get('过去两年标准差') else 'N/A'
            metrics['近三年标准差'] = f"{a_class['过去三年标准差']}%" if a_class.get('过去三年标准差') else 'N/A'
        else:
            metrics['近一年标准差'] = f"{performance_data['过去一年标准差']}%" if performance_data.get('过去一年标准差') else 'N/A'
            metrics['近两年标准差'] = f"{performance_data['过去两年标准差']}%" if performance_data.get('过去两年标准差') else 'N/A'
            metrics['近三年标准差'] = f"{performance_data['过去三年标准差']}%" if performance_data.get('过去三年标准差') else 'N/A'
        return metrics
    
    def _calculate_nav_metrics(self, fund_name: str) -> Dict:
        metrics = {}
        try:
            nav_df = self._load_nav_data(fund_name)
            if nav_df is None or nav_df.empty:
                return self._get_default_nav_metrics()
            
            # 1. 计算近一年收益率和标准差
            one_year_df = self._filter_by_years(nav_df, years=1)
            if not one_year_df.empty and len(one_year_df) > 1:
                one_year_return = self._calculate_period_return(one_year_df)
                metrics['近一年收益率'] = f"{one_year_return:.2f}%" if one_year_return is not None else 'N/A'
                one_year_df = self._calculate_daily_returns(one_year_df)
                one_year_volatility = self._calculate_period_volatility(one_year_df)
                metrics['近一年标准差'] = f"{one_year_volatility:.2f}%" if one_year_volatility is not None else 'N/A'
            else:
                metrics['近一年收益率'] = 'N/A'
                metrics['近一年标准差'] = 'N/A'
            
            # 2. 计算近两年收益率和标准差
            two_year_df = self._filter_by_years(nav_df, years=2)
            if not two_year_df.empty and len(two_year_df) > 1:
                two_year_return = self._calculate_period_return(two_year_df)
                metrics['近两年收益率'] = f"{two_year_return:.2f}%" if two_year_return is not None else 'N/A'
                two_year_df = self._calculate_daily_returns(two_year_df)
                two_year_volatility = self._calculate_period_volatility(two_year_df)
                metrics['近两年标准差'] = f"{two_year_volatility:.2f}%" if two_year_volatility is not None else 'N/A'
            else:
                metrics['近两年收益率'] = 'N/A'
                metrics['近两年标准差'] = 'N/A'
            
            # 3. 计算近三年收益率和标准差
            three_year_df = self._filter_by_years(nav_df, years=3)
            if not three_year_df.empty and len(three_year_df) > 1:
                three_year_return = self._calculate_period_return(three_year_df)
                metrics['近三年收益率'] = f"{three_year_return:.2f}%" if three_year_return is not None else 'N/A'
                three_year_df = self._calculate_daily_returns(three_year_df)
                three_year_volatility = self._calculate_period_volatility(three_year_df)
                metrics['近三年标准差'] = f"{three_year_volatility:.2f}%" if three_year_volatility is not None else 'N/A'
            else:
                metrics['近三年收益率'] = 'N/A'
                metrics['近三年标准差'] = 'N/A'
            
            # 4. 计算超额收益
            if not one_year_df.empty and len(one_year_df) > 1 and one_year_return is not None:
                one_year_excess = self._calculate_excess_return(fund_name, one_year_df, one_year_return, years=1)
                metrics['近一年超额收益'] = f"{one_year_excess:.2f}%" if one_year_excess is not None else 'N/A'
            else:
                metrics['近一年超额收益'] = 'N/A'
            
            if not two_year_df.empty and len(two_year_df) > 1 and two_year_return is not None:
                two_year_excess = self._calculate_excess_return(fund_name, two_year_df, two_year_return, years=2)
                metrics['近两年超额收益'] = f"{two_year_excess:.2f}%" if two_year_excess is not None else 'N/A'
            else:
                metrics['近两年超额收益'] = 'N/A'
            
            if not three_year_df.empty and len(three_year_df) > 1 and three_year_return is not None:
                three_year_excess = self._calculate_excess_return(fund_name, three_year_df, three_year_return, years=3)
                metrics['近三年超额收益'] = f"{three_year_excess:.2f}%" if three_year_excess is not None else 'N/A'
            else:
                metrics['近三年超额收益'] = 'N/A'
            
            # 5-10. 计算最大回撤、夏普、卡玛、胜率等 (使用三年数据)
            if not three_year_df.empty and len(three_year_df) > 1:
                max_drawdown = self._calculate_max_drawdown(three_year_df)
                metrics['最大回撤'] = f"{max_drawdown:.2f}%" if max_drawdown is not None else 'N/A'
                
                sharpe_ratio = self._calculate_sharpe_ratio(three_year_df, risk_free_rate=0.025)
                metrics['夏普比率'] = f"{sharpe_ratio:.2f}" if sharpe_ratio is not None else 'N/A'
                
                calmar_ratio = self._calculate_calmar_ratio(three_year_df)
                metrics['卡玛比率'] = f"{calmar_ratio:.2f}" if calmar_ratio is not None else 'N/A'
                
                sortino_ratio = self._calculate_sortino_ratio(three_year_df, risk_free_rate=0.025)
                metrics['索提诺比率'] = f"{sortino_ratio:.2f}" if sortino_ratio is not None else 'N/A'
                
                win_rate = self._calculate_win_rate(three_year_df)
                metrics['胜率'] = f"{win_rate:.2f}%" if win_rate is not None else 'N/A'
            else:
                metrics['最大回撤'] = 'N/A'
                metrics['夏普比率'] = 'N/A'
                metrics['卡玛比率'] = 'N/A'
                metrics['索提诺比率'] = 'N/A'
                metrics['胜率'] = 'N/A'
                
        except Exception as e:
            print(f"计算净值指标失败: {str(e)}")
            return self._get_default_nav_metrics()
        
        return metrics
    
    def _load_nav_data(self, fund_name: str) -> Optional[pd.DataFrame]:
        try:
            nav_file = os.path.join(self.nav_data_dir, f"{fund_name}.xlsx")
            if not os.path.exists(nav_file): return None
            
            df = pd.read_excel(nav_file)
            df = df.replace('--', np.nan)
            df = df.dropna(subset=['复权单位净值（元）'])
            df['日期'] = pd.to_datetime(df['日期'])
            df['复权单位净值（元）'] = pd.to_numeric(df['复权单位净值（元）'], errors='coerce')
            df = df.dropna(subset=['复权单位净值（元）'])
            df = df.sort_values('日期')
            return df
        except Exception:
            return None
    
    def _filter_recent_data(self, df: pd.DataFrame, years: int = 3) -> pd.DataFrame:
        start_date = pd.Timestamp('2022-01-01')
        end_date = pd.Timestamp('2025-12-31')
        return df[(df['日期'] >= start_date) & (df['日期'] <= end_date)]
    
    def _calculate_daily_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['日收益率'] = df['复权单位净值（元）'].pct_change()
        df = df.dropna(subset=['日收益率'])
        return df
    
    def _calculate_max_drawdown(self, df: pd.DataFrame) -> Optional[float]:
        try:
            nav = df['复权单位净值（元）'].values
            running_max = np.maximum.accumulate(nav)
            drawdown = (nav - running_max) / running_max
            max_drawdown = drawdown.min() * 100
            return max_drawdown
        except Exception:
            return None
    
    def _calculate_annual_return(self, df: pd.DataFrame) -> Optional[float]:
        try:
            total_return = (df['复权单位净值（元）'].iloc[-1] / df['复权单位净值（元）'].iloc[0] - 1)
            days = (df['日期'].iloc[-1] - df['日期'].iloc[0]).days
            years = days / 365.25
            annual_return = ((1 + total_return) ** (1 / years) - 1) * 100
            return annual_return
        except Exception:
            return None
    
    def _calculate_annual_volatility(self, df: pd.DataFrame) -> Optional[float]:
        try:
            daily_std = df['日收益率'].std()
            annual_volatility = daily_std * np.sqrt(252) * 100
            return annual_volatility
        except Exception:
            return None
    
    def _calculate_sharpe_ratio(self, df: pd.DataFrame, risk_free_rate: float = 0.025) -> Optional[float]:
        try:
            annual_return = self._calculate_annual_return(df)
            if annual_return is None: return None
            annual_volatility = self._calculate_annual_volatility(df)
            if annual_volatility is None or annual_volatility == 0: return None
            sharpe_ratio = (annual_return / 100 - risk_free_rate) / (annual_volatility / 100)
            return sharpe_ratio
        except Exception:
            return None
    
    def _calculate_calmar_ratio(self, df: pd.DataFrame) -> Optional[float]:
        try:
            annual_return = self._calculate_annual_return(df)
            if annual_return is None: return None
            max_drawdown = self._calculate_max_drawdown(df)
            if max_drawdown is None or max_drawdown == 0: return None
            calmar_ratio = annual_return / abs(max_drawdown)
            return calmar_ratio
        except Exception:
            return None
    
    def _calculate_sortino_ratio(self, df: pd.DataFrame, risk_free_rate: float = 0.025) -> Optional[float]:
        try:
            annual_return = self._calculate_annual_return(df)
            if annual_return is None: return None
            negative_returns = df[df['日收益率'] < 0]['日收益率']
            if negative_returns.empty: return None
            downside_std = np.sqrt((negative_returns ** 2).mean())
            annual_downside_volatility = downside_std * np.sqrt(252)
            if annual_downside_volatility == 0: return None
            sortino_ratio = (annual_return / 100 - risk_free_rate) / annual_downside_volatility
            return sortino_ratio
        except Exception:
            return None
    
    def _calculate_win_rate(self, df: pd.DataFrame) -> Optional[float]:
        try:
            positive_days = (df['日收益率'] > 0).sum()
            total_days = len(df)
            if total_days == 0: return None
            win_rate = (positive_days / total_days) * 100
            return win_rate
        except Exception:
            return None
    
    def _get_default_nav_metrics(self) -> Dict:
        return {
            '近一年收益率': 'N/A', '近两年收益率': 'N/A', '近三年收益率': 'N/A',
            '近一年标准差': 'N/A', '近两年标准差': 'N/A', '近三年标准差': 'N/A',
            '最大回撤': 'N/A', '夏普比率': 'N/A', '卡玛比率': 'N/A',
            '索提诺比率': 'N/A', '胜率': 'N/A', '近一年超额收益': 'N/A',
            '近两年超额收益': 'N/A', '近三年超额收益': 'N/A'
        }
    
    def _calculate_excess_return(self, fund_name: str, fund_df: pd.DataFrame, fund_return: float, years: int) -> Optional[float]:
        try:
            benchmark_return = self._get_benchmark_return_from_nav(fund_name, fund_df, years)
            if benchmark_return is not None:
                return fund_return - benchmark_return
            
            benchmark_df = self._load_benchmark_data(fund_name)
            if benchmark_df is None or benchmark_df.empty: return None
            
            start_date = fund_df['日期'].min()
            end_date = fund_df['日期'].max()
            benchmark_period = benchmark_df[(benchmark_df['日期'] >= start_date) & (benchmark_df['日期'] <= end_date)].copy()
            if benchmark_period.empty or len(benchmark_period) < 2: return None
            
            benchmark_return = self._calculate_period_return(benchmark_period)
            if benchmark_return is None: return None
            
            return fund_return - benchmark_return
        except Exception:
            return None
    
    def _get_benchmark_return_from_nav(self, fund_name: str, fund_df: pd.DataFrame, years: int) -> Optional[float]:
        try:
            nav_file = os.path.join(self.nav_data_dir, f"{fund_name}.xlsx")
            if not os.path.exists(nav_file): return None
            
            df = pd.read_excel(nav_file)
            benchmark_col = next((col for col in df.columns if '业绩比较基准收益率' in str(col)), None)
            if benchmark_col is None: return None
            
            df = df.replace('--', np.nan)
            df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
            df[benchmark_col] = pd.to_numeric(df[benchmark_col], errors='coerce')
            df = df.dropna(subset=['日期', benchmark_col]).sort_values('日期')
            
            start_date, end_date = fund_df['日期'].min(), fund_df['日期'].max()
            period_df = df[(df['日期'] >= start_date) & (df['日期'] <= end_date)].copy()
            if period_df.empty or len(period_df) < 2: return None
            
            return period_df.iloc[-1][benchmark_col] - period_df.iloc[0][benchmark_col]
        except Exception:
            return None
    
    def _load_benchmark_data(self, fund_name: str) -> Optional[pd.DataFrame]:
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            benchmark_file = os.path.join(base_dir, 'data', '指数.xlsx')
            if not os.path.exists(benchmark_file): return None
            
            df = pd.read_excel(benchmark_file).replace('--', np.nan)
            if all(col in df.columns for col in ['Indexcd', 'Idxtrd01', 'Idxtrd05']):
                df = df.iloc[2:].copy()
                df = df.rename(columns={'Idxtrd01': '日期', 'Idxtrd05': '复权单位净值（元）'})
                df = df[['日期', '复权单位净值（元）']].copy()
            else:
                date_col = next((c for c in df.columns if '日期' in str(c) or 'date' in str(c).lower()), None)
                nav_col = next((c for c in df.columns if '收盘' in str(c) or '净值' in str(c) or 'close' in str(c).lower()), None)
                if date_col is None or nav_col is None:
                    if len(df.columns) >= 2: date_col, nav_col = df.columns[0], df.columns[1]
                    else: return None
                df = df.rename(columns={date_col: '日期', nav_col: '复权单位净值（元）'})
            
            df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
            df['复权单位净值（元）'] = pd.to_numeric(df['复权单位净值（元）'], errors='coerce')
            df = df.dropna(subset=['日期', '复权单位净值（元）']).sort_values('日期')
            return df
        except Exception:
            return None
            
    def _filter_by_years(self, df: pd.DataFrame, years: int) -> pd.DataFrame:
        try:
            latest_date = df['日期'].max()
            start_date = latest_date - pd.DateOffset(years=years)
            return df[df['日期'] >= start_date].copy()
        except Exception:
            return pd.DataFrame()
    
    def _calculate_period_return(self, df: pd.DataFrame) -> Optional[float]:
        """计算区间收益率"""
        try:
            if df.empty or len(df) < 2:
                return None
            start_nav = df['复权单位净值（元）'].iloc[0]
            end_nav = df['复权单位净值（元）'].iloc[-1]
            if start_nav == 0:
                return None
            period_return = (end_nav / start_nav - 1) * 100
            return period_return
        except Exception:
            return None
    
    def _calculate_period_volatility(self, df: pd.DataFrame) -> Optional[float]:
        """计算区间年化波动率"""
        try:
            if df.empty or '日收益率' not in df.columns:
                return None
            daily_std = df['日收益率'].std()
            if pd.isna(daily_std):
                return None
            annual_volatility = daily_std * np.sqrt(252) * 100
            return annual_volatility
        except Exception:
            return None