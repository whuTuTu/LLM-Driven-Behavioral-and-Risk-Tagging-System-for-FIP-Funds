"""
操作风格标签生成器
基于文本、持仓两维度判断左侧/右侧投资风格（含二级债/转债双轨适配）
"""

import os
import json
import re
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Optional

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# LLM配置
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')

try:
    import openai
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

# 导入指数数据加载器
try:
    from ..data_extraction.index_data_loader import get_index_loader
    INDEX_LOADER_AVAILABLE = True
except ImportError:
    try:
        from data_extraction.index_data_loader import get_index_loader
        INDEX_LOADER_AVAILABLE = True
    except ImportError:
        INDEX_LOADER_AVAILABLE = False

# 导入历史持仓数据加载器
try:
    from ..data_extraction.historical_holding_loader import get_historical_holding_loader
    HISTORICAL_HOLDING_LOADER_AVAILABLE = True
except ImportError:
    try:
        from data_extraction.historical_holding_loader import get_historical_holding_loader
        HISTORICAL_HOLDING_LOADER_AVAILABLE = True
    except ImportError:
        HISTORICAL_HOLDING_LOADER_AVAILABLE = False

# 导入基金类型识别器（核心隔离依赖）
try:
    from ..fund_type_identifier import FundTypeIdentifier
    FUND_TYPE_IDENTIFIER_AVAILABLE = True
except ImportError:
    try:
        from fund_type_identifier import FundTypeIdentifier
        FUND_TYPE_IDENTIFIER_AVAILABLE = True
    except ImportError:
        FUND_TYPE_IDENTIFIER_AVAILABLE = False


class OperationStyleTagger:
    """操作风格标签生成器"""
    
    def __init__(self):
        """初始化标签生成器"""
        self.use_llm = LLM_AVAILABLE and DEEPSEEK_API_KEY
        self.index_loader = None
        self.historical_holding_loader = None
        self.fund_type_identifier = None
        
        if INDEX_LOADER_AVAILABLE:
            try: self.index_loader = get_index_loader()
            except Exception as e: print(f"初始化指数数据加载器失败: {str(e)}")
        
        if HISTORICAL_HOLDING_LOADER_AVAILABLE:
            try: self.historical_holding_loader = get_historical_holding_loader()
            except Exception as e: print(f"初始化历史持仓数据加载器失败: {str(e)}")
            
        if FUND_TYPE_IDENTIFIER_AVAILABLE:
            try: self.fund_type_identifier = FundTypeIdentifier()
            except Exception as e: print(f"初始化基金类型识别器失败: {str(e)}")
    
    def generate(self, extracted_data: Dict, fund_name: str = None) -> Dict:
        """生成操作风格标签"""
        tags = {}
        report_date = self._parse_report_date(extracted_data, fund_name)
        clean_fund_name = self._extract_fund_name(fund_name)
        
        # 1. 识别基金类型，实现双轨隔离
        fund_type_info = self._identify_fund_type(clean_fund_name)
        fund_type_code = fund_type_info.get('基金类型代码', 'UNKNOWN')
        
        # 2. 传入类型代码进行精细化打分
        style_result = self._determine_investment_style_with_scores(extracted_data, report_date, clean_fund_name, fund_type_code)
        
        tags['投资风格'] = style_result['投资风格']
        tags['文本维度得分'] = style_result.get('文本维度得分')
        tags['持仓维度得分'] = style_result.get('持仓维度得分')
        tags['综合得分'] = style_result.get('综合得分')
        
        return tags
    
    def _identify_fund_type(self, fund_name: str) -> Dict:
        """识别基金类型（赛道分流）"""
        if not fund_name: return {'基金类型代码': 'UNKNOWN'}
        
        if self.fund_type_identifier:
            try: return self.fund_type_identifier.identify(fund_name)
            except: pass
            
        # 降级：关键词路由匹配
        if '可转债' in fund_name or '转债' in fund_name:
            return {'基金类型代码': 'CONVERTIBLE_BOND'}
        elif '二级债' in fund_name or '增强债' in fund_name or '丰利' in fund_name:
            return {'基金类型代码': 'SECONDARY_BOND'}
        return {'基金类型代码': 'BOND'}
    
    def _extract_fund_name(self, fund_name: str = None) -> Optional[str]:
        if not fund_name: return None
        clean_name = re.sub(r'\d{4}年?', '', fund_name)
        report_types = ['年度报告', '年报', '中期报告', '半年报', '第1季度', '第2季度', '第3季度', '第4季度', '一季报', '三季报', '季报', '报告']
        for report_type in report_types:
            clean_name = clean_name.replace(report_type, '')
        clean_name = re.sub(r'[\s\-_]+', '', clean_name).strip()
        return clean_name if clean_name else None
    
    def _parse_report_date(self, extracted_data: Dict, fund_name: str = None) -> Optional[datetime]:
        try:
            if fund_name:
                year_match = re.search(r'(\d{4})年', fund_name)
                if year_match:
                    year = int(year_match.group(1))
                    if '年度报告' in fund_name or '年报' in fund_name: return datetime(year, 12, 31)
                    elif '中期报告' in fund_name or '半年报' in fund_name: return datetime(year, 6, 30)
                    elif '第1季度' in fund_name or '一季报' in fund_name: return datetime(year, 3, 31)
                    elif '第2季度' in fund_name: return datetime(year, 6, 30)
                    elif '第3季度' in fund_name or '三季报' in fund_name: return datetime(year, 9, 30)
                    elif '第4季度' in fund_name: return datetime(year, 12, 31)
            return None
        except Exception as e:
            print(f"解析报告期日期失败: {str(e)}")
            return None
    
    def _determine_investment_style_with_scores(self, extracted_data: Dict, report_date: Optional[datetime] = None, fund_name: str = None, fund_type_code: str = 'UNKNOWN') -> Dict:
        scores = []
        weights = []
        
        # 传入 fund_type_code 实现双轨解析
        text_score = self._analyze_text_dimension(extracted_data, fund_type_code)
        if text_score is not None:
            scores.append(text_score)
            weights.append(0.4)
        
        # 传入 fund_type_code 实现动态阈值
        holding_score = self._analyze_holding_dimension(extracted_data, report_date, fund_name, fund_type_code)
        if holding_score is not None:
            scores.append(holding_score)
            weights.append(0.6)
        
        if not scores:
            return {'投资风格': '数据不足', '文本维度得分': None, '持仓维度得分': None, '综合得分': None}
        
        weighted_score = sum(s * w for s, w in zip(scores, weights)) / sum(weights)
        investment_style = '均衡配置（择时不明显）'
        
        if text_score is not None and holding_score is not None:
            text_direction = 'left' if text_score <= -0.3 else ('right' if text_score >= 0.3 else 'neutral')
            holding_direction = 'left' if holding_score <= -0.3 else ('right' if holding_score >= 0.3 else 'neutral')
            
            if text_direction == holding_direction and text_direction != 'neutral':
                investment_style = '强左侧布局（知行合一）' if text_direction == 'left' else '强右侧跟随（知行合一）'
            elif text_direction != holding_direction and text_direction != 'neutral' and holding_direction != 'neutral':
                if weighted_score <= -0.3: investment_style = '左侧布局（风格漂移预警）'
                elif weighted_score >= 0.3: investment_style = '右侧跟随（风格漂移预警）'
                else: investment_style = '均衡配置（风格漂移预警）'
        
        if investment_style == '均衡配置（择时不明显）':
            if weighted_score <= -0.3: investment_style = '左侧布局（逆向投资）'
            elif weighted_score >= 0.3: investment_style = '右侧跟随（趋势投资）'
        
        return {
            '投资风格': investment_style,
            '文本维度得分': round(text_score, 3) if text_score is not None else None,
            '持仓维度得分': round(holding_score, 3) if holding_score is not None else None,
            '综合得分': round(weighted_score, 3)
        }
    
    def _analyze_text_dimension(self, extracted_data: Dict, fund_type_code: str) -> Optional[float]:
        """文本维度分析：根据基金类型应用定制化Prompt"""
        try:
            macro_data = extracted_data.get('宏观观点', {})
            if not macro_data: return None
            if not self.use_llm: return self._keyword_based_analysis(macro_data, fund_type_code)
            
            # 【核心修改】动态生成赛道专属判定标准
            if fund_type_code == 'CONVERTIBLE_BOND':
                criteria = """
【转债专属左侧/防守特征】：偏好双低策略（低价低溢价率）、注重债底保护、左侧潜伏偏债型转债、防守反击、逢低布局大盘银行转债、主动降低弹性暴露。
【转债专属右侧/进攻特征】：追逐高弹性偏股型转债、顺势加仓高溢价率转债、强烈的正股替代（Delta跟随）、积极参与条款博弈（强赎/下修）、高位满仓运行。
"""
            else:
                criteria = """
【二级债/纯债左侧/防守特征】：逆向投资、逢低买入股票、提前潜伏、底部区间、低估值防御、注重安全边际、防守反击、绝对收益导向、严控回撤。
【二级债/纯债右侧/进攻特征】：顺势而为、追逐趋势、顺周期、高弹性进攻、动能突破、顶格配置20%权益仓位、顺应景气度。
"""

            prompt = f"""
请深度分析以下基金经理的投资策略和运作分析，判断其操作风格是偏向"左侧布局（逆向防守）"还是"右侧跟随（顺势进攻）"。

投资策略和运作分析：
{json.dumps(macro_data, ensure_ascii=False, indent=2)}
{criteria}

请严格根据上述文本流露的意图，给出一个风格得分（-1.0 到 1.0 之间）：
- -1.0：绝对左侧（极度逆向/严密防守）
- 0.0：均衡配置（无明显方向）
- 1.0：绝对右侧（极度顺势/极致进攻）

只返回得分数字，不要其他解释。
"""
            client = openai.OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": "你是一位专业的金融量化分析师，擅长捕捉不同赛道基金经理隐含的操作风格。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=10
            )
            
            result = response.choices[0].message.content.strip()
            score = float(result)
            return max(-1.0, min(1.0, score))
        except Exception as e:
            print(f"文本维度分析失败: {str(e)}")
            return None
    
    def _keyword_based_analysis(self, macro_data: Dict, fund_type_code: str) -> Optional[float]:
        try:
            text = json.dumps(macro_data, ensure_ascii=False)
            if fund_type_code == 'CONVERTIBLE_BOND':
                left_keywords = ['双低', '债底', '防守', '中低价', '偏债型', '安全垫', '保护']
                right_keywords = ['顺势', '高弹性', '偏股型', '正股替代', '条款博弈', '跟随', '动能']
            else:
                left_keywords = ['逆向', '左侧', '底部', '低估值', '防守', '跌出价值', '潜伏', '严控回撤']
                right_keywords = ['顺势', '右侧', '趋势', '景气度', '突破', '确认', '追涨', '顺周期', '进攻']
                
            left_count = sum(1 for kw in left_keywords if kw in text)
            right_count = sum(1 for kw in right_keywords if kw in text)
            total = left_count + right_count
            if total == 0: return None
            return (right_count - left_count) / total
        except Exception:
            return None
    
    def _analyze_holding_dimension(self, extracted_data: Dict, report_date: Optional[datetime] = None, fund_name: str = None, fund_type_code: str = 'UNKNOWN') -> Optional[float]:
        try:
            holding_data = extracted_data.get('持仓数据', {})
            if not holding_data: return None
            
            equity_ratio = self._extract_equity_ratio_from_industry(holding_data)
            if equity_ratio == 0.0:
                asset_allocation = holding_data.get('报告期末基金资产组合情况', {})
                equity_ratio = self._extract_ratio(asset_allocation.get('权益投资', '0%'))
            
            convertible_ratio = self._extract_convertible_ratio(holding_data)
            current_risk_ratio = equity_ratio + convertible_ratio
            
            print(f"持仓维度分析: 权益投资={equity_ratio:.2f}%, 可转债={convertible_ratio:.2f}%, 总风险资产={current_risk_ratio:.2f}%")
            
            if not self.index_loader or not report_date: return None
            
            prev_quarter_change = self.index_loader.get_previous_quarter_index_change(report_date)
            if prev_quarter_change is None: return None
            _, _, prev_change_pct = prev_quarter_change
            
            prev_risk_ratio = self._get_previous_quarter_risk_ratio(fund_name, report_date)
            if prev_risk_ratio is None: return None
            
            delta_risk_ratio = current_risk_ratio - prev_risk_ratio
            print(f"持仓维度分析: 上一季度指数涨跌={prev_change_pct:.2f}%, 当前占比={current_risk_ratio:.2f}%, 上期={prev_risk_ratio:.2f}%, 变化={delta_risk_ratio:.2f}%")
            
            # 【核心修改】传入 fund_type_code，计算定制化的高危阈值
            score = self._calculate_style_score(prev_change_pct, delta_risk_ratio, current_risk_ratio, fund_type_code)
            print(f"持仓维度分析: 最终打分={score}")
            return score
        except Exception as e:
            print(f"持仓维度分析失败: {str(e)}")
            return None
    
    def _calculate_style_score(self, index_change: float, position_change: float, current_risk_ratio: float = 0.0, fund_type_code: str = 'UNKNOWN') -> float:
        """
        根据指数变化、仓位变化及绝对仓位水平计算得分。
        【核心修复】：彻底隔离二级债基与转债基金的“高危满仓（天花板）”标准。
        """
        # 动态判定满仓天花板
        if fund_type_code == 'CONVERTIBLE_BOND':
            is_high_risk = current_risk_ratio >= 85.0  # 转债基金常年重仓转债，达到 85% 甚至 90% 才算高危/满仓
        else:
            is_high_risk = current_risk_ratio >= 18.0  # 二级债基逼近 20% 契约上限即为满仓进攻

        if index_change < -5:
            if position_change > 1: return -0.8
            elif position_change >= -1: return -0.4
            elif position_change >= -3: return 0.0
            else: return 0.8
        elif index_change > 5:
            if position_change > 3: return 0.8
            elif position_change >= 1: 
                return 0.4 if is_high_risk else 0.0
            elif position_change >= -1: 
                # 大涨市中保持满仓天花板，属于右侧持筹待涨；否则视为左侧被动微调
                return 0.2 if is_high_risk else -0.4
            else: return -0.8
        else:
            # 震荡市
            if position_change > 2: return 0.4
            elif position_change < -2: return -0.4
            else:
                # 震荡市中始终保持满仓/高弹性，体现了极强的进攻意图
                return 0.3 if is_high_risk else 0.0
    
    def _get_previous_quarter_risk_ratio(self, fund_name: str, current_report_date: datetime) -> Optional[float]:
        try:
            year = current_report_date.year
            month = current_report_date.month
            
            if month == 3: prev_date = datetime(year - 1, 12, 31)
            elif month == 6: prev_date = datetime(year, 3, 31)
            elif month == 9: prev_date = datetime(year, 6, 30)
            elif month == 12: prev_date = datetime(year, 9, 30)
            else: return None
            
            if fund_name:
                if prev_date.month == 3: report_type = "第1季度报告"
                elif prev_date.month == 6: report_type = "第2季度报告"
                elif prev_date.month == 9: report_type = "第3季度报告"
                else: report_type = "第4季度报告"
                prev_filename = f"{fund_name}{prev_date.year}年{report_type}_提取结果.md"
            else: return None
            
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            filepath = os.path.join(base_dir, 'output', 'fund_analysis', 'extracted_data', prev_filename)
            
            if not os.path.exists(filepath): return None
            
            with open(filepath, 'r', encoding='utf-8') as f: content = f.read()
            holding_match = re.search(r'## 4\. 投资组合数据提取器\s*```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if not holding_match: return None
            
            holding_data = json.loads(holding_match.group(1))
            equity_ratio = self._extract_equity_ratio_from_industry(holding_data)
            if equity_ratio == 0.0:
                asset_allocation = holding_data.get('报告期末基金资产组合情况', {})
                equity_ratio = self._extract_ratio(asset_allocation.get('权益投资', '0%'))
            
            convertible_ratio = self._extract_convertible_ratio(holding_data)
            return equity_ratio + convertible_ratio
        except Exception:
            return None
            
    def _extract_ratio(self, ratio_str: str) -> float:
        try:
            if not ratio_str or ratio_str == 'N/A': return 0.0
            return float(ratio_str.replace('%', '').strip())
        except Exception:
            return 0.0
            
    def _extract_convertible_ratio(self, holding_data: Dict) -> float:
        try:
            bond_portfolio = holding_data.get('按债券品种分类的债券投资组合', {})
            for key in ['可转债（可交换债）', '可转债', '可交换债']:
                if key in bond_portfolio:
                    return self._extract_ratio(bond_portfolio[key])
            return 0.0
        except Exception:
            return 0.0
            
    def _extract_equity_ratio_from_industry(self, holding_data: Dict) -> float:
        try:
            industry_allocation = holding_data.get('按行业分类的境内股票投资组合', [])
            if not industry_allocation or not isinstance(industry_allocation, list): return 0.0
            
            for item in industry_allocation:
                if isinstance(item, dict) and '合计' in item.get('行业名称', ''):
                    return self._extract_ratio(item.get('占净值比例', '0%'))
            
            total_ratio = 0.0
            for item in industry_allocation:
                if isinstance(item, dict):
                    total_ratio += self._extract_ratio(item.get('占净值比例', '0%'))
            return total_ratio
        except Exception:
            return 0.0