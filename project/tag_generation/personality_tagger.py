"""
个性特征标签生成器
基于持仓特征和宏观观点生成个性特征相关标签
"""

import os
import re
import json
from typing import Dict, List

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

# 导入基金类型特性配置
try:
    from ..config.fund_type_characteristics import (
        get_fund_type_prompt_context,
        get_analysis_focus,
        get_fund_type_characteristics
    )
    FUND_TYPE_CONFIG_AVAILABLE = True
except ImportError:
    try:
        from config.fund_type_characteristics import (
            get_fund_type_prompt_context,
            get_analysis_focus,
            get_fund_type_characteristics
        )
        FUND_TYPE_CONFIG_AVAILABLE = True
    except ImportError:
        FUND_TYPE_CONFIG_AVAILABLE = False

# 导入基金类型识别器
try:
    from ..fund_type_identifier import FundTypeIdentifier
    FUND_TYPE_IDENTIFIER_AVAILABLE = True
except ImportError:
    try:
        from fund_type_identifier import FundTypeIdentifier
        FUND_TYPE_IDENTIFIER_AVAILABLE = True
    except ImportError:
        FUND_TYPE_IDENTIFIER_AVAILABLE = False


class PersonalityTagger:
    """个性特征标签生成器"""
    
    def __init__(self):
        """初始化标签生成器"""
        self.use_llm = LLM_AVAILABLE and DEEPSEEK_API_KEY
        self.fund_type_identifier = None
        
        if FUND_TYPE_IDENTIFIER_AVAILABLE:
            try:
                self.fund_type_identifier = FundTypeIdentifier()
            except Exception as e:
                print(f"初始化基金类型识别器失败: {str(e)}")
    
    def generate(self, extracted_data: Dict, fund_name: str = None) -> Dict:
        """
        生成个性特征标签
        
        Args:
            extracted_data: 提取的数据
            fund_name: 基金名称（用于识别基金类型）
            
        Returns:
            个性特征标签
        """
        tags = {}
        
        # 识别基金类型
        fund_type_info = self._identify_fund_type(fund_name)
        fund_type_code = fund_type_info.get('基金类型代码', 'UNKNOWN')
        
        # 获取宏观观点数据
        macro_data = extracted_data.get('宏观观点', {})
        
        # 获取持仓数据
        holding_data = extracted_data.get('持仓数据', {})
        
        # 1. 信用下沉程度
        tags['信用下沉'] = self._analyze_credit_sinking(macro_data, holding_data, fund_type_code)
        
        # 2. 权益风格偏好（含转债双轨适配）
        tags['权益风格'] = self._analyze_equity_style(holding_data, macro_data, fund_type_code)
        
        # 3. 回撤控制严格度（动态切换阈值）
        tags['回撤控制'] = self._analyze_drawdown_control(extracted_data, fund_type_code)
        
        # 4. 利率波段收益能力
        tags['利率波段'] = self._analyze_rate_band(macro_data, holding_data, fund_type_code)
        
        return tags

    # ==========================================
    # 维度一：信用下沉分析
    # ==========================================
    def _analyze_credit_sinking(self, macro_data: Dict, holding_data: Dict, fund_type_code: str = 'UNKNOWN') -> str:
        """分析信用下沉程度（使用LLM综合判断）"""
        if not self.use_llm:
            return self._analyze_credit_sinking_fallback(macro_data, holding_data)
        
        try:
            strategy_text = macro_data.get('投资策略和运作分析', '') if macro_data else ''
            bond_holdings = self._prepare_bond_holdings_for_llm(holding_data)
            fund_type_context = self._get_fund_type_context(fund_type_code)
            
            prompt = self._build_credit_sinking_prompt(strategy_text, bond_holdings, fund_type_context)
            response = self._call_llm(prompt)
            
            if response:
                return self._parse_credit_sinking_response(response)
            else:
                return self._analyze_credit_sinking_fallback(macro_data, holding_data)
        except Exception as e:
            print(f"LLM信用下沉分析失败: {str(e)}")
            return self._analyze_credit_sinking_fallback(macro_data, holding_data)
            
    def _prepare_bond_holdings_for_llm(self, holding_data: Dict) -> str:
        """准备债券持仓数据供LLM分析"""
        if not holding_data:
            return "无债券持仓数据"
        bond_info = []
        
        bond_types = holding_data.get('按债券品种分类的债券投资组合', {})
        if bond_types and isinstance(bond_types, dict):
            bond_info.append("【债券品种分布】")
            for key, value in bond_types.items():
                if isinstance(value, str) and '%' in value:
                    bond_info.append(f"  - {key}: {value}")
        
        top_bonds = holding_data.get('前五名债券投资明细', [])
        if top_bonds and isinstance(top_bonds, list):
            bond_info.append("\n【前五名债券投资明细】")
            for i, bond in enumerate(top_bonds[:5], 1):
                if isinstance(bond, dict):
                    name = bond.get('债券名称', bond.get('名称', '未知'))
                    ratio = bond.get('占净值比例', '未知')
                    rating = bond.get('债券评级', bond.get('评级', '未知'))
                    bond_info.append(f"  {i}. {name} (占比: {ratio}, 评级: {rating})")
        
        return '\n'.join(bond_info) if bond_info else "无债券持仓数据"
        
    def _build_credit_sinking_prompt(self, strategy_text: str, bond_holdings: str, fund_type_context: str = '') -> str:
        fund_type_section = f"\n{fund_type_context}\n" if fund_type_context else ""
        prompt = f"""你是一位专业的债券基金分析师。请基于以下两个维度判断该基金是否存在"信用下沉"行为。
{fund_type_section}
【定义】
信用下沉：基金经理为了获取更高收益，主动投资信用评级较低的债券（如AA+、AA级企业债、城投债、永续债、二级资本债等）。

【维度一：投资策略文本】
{strategy_text if strategy_text else "无"}

【维度二：债券持仓数据】
{bond_holdings}

【判断标准】
- **积极信用下沉**：文本明确提及信用下沉/博弈票息策略 + 持仓中有明显的低评级债券、永续债、次级债或城投债。
- **适度信用下沉**：持仓中有一定比例的信用债下沉特征，但文本未过度强调。
- **高等级为主（信用中性）**：主要持有高等级债券（国债、政金债、AAA级企业债）。对于转债基金，即使持有转债，只要是高评级品种，也属于高等级为主。

请严格按照以下JSON格式输出：
```json
{{
  "文本维度": {{"分析": "..."}},
  "持仓维度": {{"分析": "..."}},
  "综合判断": "积极信用下沉/适度信用下沉/高等级为主（信用中性）",
  "判断理由": "..."
}}
"""
        return prompt

    def _parse_credit_sinking_response(self, response: str) -> str:
        try:
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
                return result.get('综合判断', '高等级为主（信用中性）')
            
            if '积极信用下沉' in response: return '积极信用下沉'
            elif '适度信用下沉' in response: return '适度信用下沉'
            else: return '高等级为主（信用中性）'
        except Exception:
            return '高等级为主（信用中性）'

    def _analyze_credit_sinking_fallback(self, macro_data: Dict, holding_data: Dict) -> str:
        text_score = self._analyze_credit_sinking_text(macro_data)
        holding_score = self._analyze_credit_sinking_holding(holding_data)
        
        if text_score and holding_score: return '积极信用下沉'
        elif holding_score: return '适度信用下沉'
        else: return '高等级为主（信用中性）'

    def _analyze_credit_sinking_text(self, macro_data: Dict) -> bool:
        if not macro_data: return False
        strategy_text = macro_data.get('投资策略和运作分析', '')
        if not strategy_text: return False
        
        credit_sinking_keywords = ['挖掘信用利差', '获取票息收益', '票息', '城投平台', '城投', '地产', '次级债', '永续债', '适度下沉', '信用下沉', '高收益债', '低评级', 'AA+', 'AA', '博弈票息', '信用挖掘', '利差挖掘', '收益增强']
        high_grade_keywords = ['高等级', 'AAA', '防范尾部风险', '规避信用风险', '信用风险可控', '优质信用', '龙头', '央企', '国企']
        
        sinking_count = sum(1 for kw in credit_sinking_keywords if kw in strategy_text)
        high_grade_count = sum(1 for kw in high_grade_keywords if kw in strategy_text)
        return sinking_count >= 2 and sinking_count > high_grade_count

    def _analyze_credit_sinking_holding(self, holding_data: Dict) -> bool:
        if not holding_data: return False
        top_bonds = holding_data.get('前五名债券投资明细', [])
        if not top_bonds or not isinstance(top_bonds, list): return False
        
        credit_sinking_bond_keywords = ['永续债', '二级资本债', '二级', '次级', '城投', '地产', 'AA+', 'AA ', '非AAA', '民企', '私募']
        sinking_bond_count = 0
        for bond in top_bonds[:5]:
            if not isinstance(bond, dict): continue
            bond_name = bond.get('债券名称', '') or bond.get('名称', '')
            bond_rating = bond.get('债券评级', '') or bond.get('评级', '')
            
            for keyword in credit_sinking_bond_keywords:
                if keyword in bond_name or keyword in bond_rating:
                    sinking_bond_count += 1
                    break
            
            if bond_rating in ['AA', 'AA+', 'AA-']:
                sinking_bond_count += 1
                
        return sinking_bond_count >= 2


    # ==========================================
    # 维度二：权益风格偏好（含转债双轨适配）
    # ==========================================
    def _analyze_equity_style(self, holding_data: Dict, macro_data: Dict = None, fund_type_code: str = 'UNKNOWN') -> str:
        has_equity = False
        
        # 1. 转债基金天然自带权益属性，强制视作有权益敞口
        if fund_type_code == 'CONVERTIBLE_BOND':
            has_equity = True
        else:
            # 2. 传统判定：股票仓位大于1%
            asset_allocation = holding_data.get('报告期末基金资产组合情况', {})
            if isinstance(asset_allocation, dict):
                equity_ratio_str = asset_allocation.get('权益投资', '0%')
                try:
                    if float(equity_ratio_str.replace('%', '')) >= 1:
                        has_equity = True
                except: pass
            
            # 3. 如果持有大量可转债(>10%)，也视为有广义权益敞口
            bond_types = holding_data.get('按债券品种分类的债券投资组合', {})
            if isinstance(bond_types, dict):
                cb_ratio_str = bond_types.get('可转债（可交换债）', '0%')
                try:
                    if float(cb_ratio_str.replace('%', '')) >= 10:
                        has_equity = True
                except: pass

        if not has_equity:
            return '无权益持仓'
        
        if not self.use_llm:
            return self._analyze_equity_style_fallback(holding_data, fund_type_code)
        
        try:
            strategy_text = macro_data.get('投资策略和运作分析', '') if macro_data else ''
            # 【核心】将fund_type_code传入，为转债抓取专用持仓
            stock_holdings = self._prepare_stock_holdings_for_llm(holding_data, fund_type_code)
            fund_type_context = self._get_fund_type_context(fund_type_code)
            
            prompt = self._build_equity_style_prompt(strategy_text, stock_holdings, fund_type_context, fund_type_code)
            response = self._call_llm(prompt)
            
            if response:
                return self._parse_equity_style_response(response, fund_type_code)
            else:
                return self._analyze_equity_style_fallback(holding_data, fund_type_code)
        except Exception as e:
            print(f"LLM权益风格分析失败: {str(e)}")
            return self._analyze_equity_style_fallback(holding_data, fund_type_code)

    def _prepare_stock_holdings_for_llm(self, holding_data: Dict, fund_type_code: str = 'UNKNOWN') -> str:
        if not holding_data: return "无相关数据"
        info = []
        
        # 股票行业及明细（传统权益）
        industry_allocation = holding_data.get('按行业分类的境内股票投资组合', [])
        if industry_allocation and isinstance(industry_allocation, list):
            info.append("【股票行业配置】")
            for ind in industry_allocation:
                info.append(f"  - {ind.get('行业名称', '未知')}: {ind.get('占净值比例', '未知')}")
                
        top_stocks = holding_data.get('前十名股票投资明细', [])
        if top_stocks and isinstance(top_stocks, list):
            info.append("\n【前十大重仓股票】")
            for i, stock in enumerate(top_stocks[:10], 1):
                info.append(f"  {i}. {stock.get('股票名称', '')} (占比: {stock.get('占净值比例', '')})")
        
        # 【核心修改】如果是转债基金，必须提取前五大转债作为权益风向标
        if fund_type_code == 'CONVERTIBLE_BOND' or '可转债' in str(holding_data):
            bond_types = holding_data.get('按债券品种分类的债券投资组合', {})
            cb_ratio = bond_types.get('可转债（可交换债）', '0%') if isinstance(bond_types, dict) else '0%'
            info.append(f"\n【可转债核心配置(替代股票属性)】\n  - 整体可转债占比: {cb_ratio}")
            
            top_bonds = holding_data.get('前五名债券投资明细', [])
            if top_bonds and isinstance(top_bonds, list):
                info.append("  - 前五大重仓转债/债券明细:")
                for i, bond in enumerate(top_bonds[:5], 1):
                    info.append(f"    {i}. {bond.get('债券名称', '')} (占比: {bond.get('占净值比例', '')})")

        return '\n'.join(info) if info else "无明显权益或转债持仓"

    def _build_equity_style_prompt(self, strategy_text: str, holdings: str, fund_type_context: str, fund_type_code: str) -> str:
        fund_type_section = f"\n{fund_type_context}\n" if fund_type_context else ""
        
        # 根据赛道动态切换判定标准
        if fund_type_code == 'CONVERTIBLE_BOND':
            criteria = """【判断标准（转债基金专用）】
- **双低策略（偏价值防守）**：偏好低价格、低溢价的转债品种，注重防守性和安全边际，追求稳健收益。
- **高弹性策略（偏成长进攻）**：偏好高溢价、正股高成长的转债品种，注重进攻性和弹性空间，追求超额收益。
- **平衡配置**：在双低和高弹性之间保持均衡配置。

请严格按照以下JSON格式输出：
```json
{{
  "策略文本分析": "从投资策略文本中提取的风格倾向",
  "持仓结构分析": "从持仓数据中观察的风格特征",
  "综合判断": "双低策略（偏价值防守）/高弹性策略（偏成长进攻）/平衡配置",
  "判断理由": "..."
}}
```"""
        else:
            criteria = """【判断标准（传统权益基金）】
- **价值风格**：偏好低估值、高分红、稳健增长的股票（如银行、公用事业、传统制造业）。
- **成长风格**：偏好高增长、高估值、创新驱动的股票（如科技、医药、新能源）。
- **平衡风格**：在价值和成长之间保持均衡配置。

请严格按照以下JSON格式输出：
```json
{{
  "策略文本分析": "从投资策略文本中提取的风格倾向",
  "持仓结构分析": "从持仓数据中观察的风格特征",
  "综合判断": "价值风格/成长风格/平衡风格",
  "判断理由": "..."
}}
```"""
        
        prompt = f"""你是一位专业的基金分析师。请基于以下信息判断该基金的权益投资风格。
{fund_type_section}
【投资策略文本】
{strategy_text if strategy_text else "无"}

【持仓数据】
{holdings}

{criteria}
"""
        return prompt
    
    def _parse_equity_style_response(self, response: str, fund_type_code: str = 'UNKNOWN') -> str:
        """解析权益风格LLM响应"""
        try:
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
                return result.get('综合判断', '平衡风格')
            
            # 转债基金专用关键词
            if fund_type_code == 'CONVERTIBLE_BOND':
                if '双低策略' in response or '价值防守' in response:
                    return '双低策略（偏价值防守）'
                elif '高弹性策略' in response or '成长进攻' in response:
                    return '高弹性策略（偏成长进攻）'
                else:
                    return '平衡配置'
            else:
                # 传统权益基金
                if '价值风格' in response or '价值' in response:
                    return '价值风格'
                elif '成长风格' in response or '成长' in response:
                    return '成长风格'
                else:
                    return '平衡风格'
        except Exception:
            if fund_type_code == 'CONVERTIBLE_BOND':
                return '平衡配置'
            else:
                return '平衡风格'
    
    def _analyze_equity_style_fallback(self, holding_data: Dict, fund_type_code: str = 'UNKNOWN') -> str:
        """权益风格分析的降级方法"""
        # 转债基金默认返回平衡配置
        if fund_type_code == 'CONVERTIBLE_BOND':
            return '平衡配置'
        
        # 传统基金基于行业配置简单判断
        industry_allocation = holding_data.get('按行业分类的境内股票投资组合', [])
        if not industry_allocation:
            return '平衡风格'
        
        value_industries = ['金融业', '房地产业', '建筑业', '采矿业', '电力、热力、燃气及水生产和供应业']
        growth_industries = ['信息传输、软件和信息技术服务业', '科学研究和技术服务业', '卫生和社会工作']
        
        value_ratio = 0
        growth_ratio = 0
        
        for ind in industry_allocation:
            if not isinstance(ind, dict):
                continue
            industry_name = ind.get('行业名称', '')
            ratio_str = ind.get('占净值比例', '0%')
            try:
                ratio = float(ratio_str.replace('%', ''))
                if any(v in industry_name for v in value_industries):
                    value_ratio += ratio
                elif any(g in industry_name for g in growth_industries):
                    growth_ratio += ratio
            except:
                pass
        
        if value_ratio > growth_ratio * 1.5:
            return '价值风格'
        elif growth_ratio > value_ratio * 1.5:
            return '成长风格'
        else:
            return '平衡风格'

    # ==========================================
    # 维度三：回撤控制分析（动态阈值）
    # ==========================================
    def _analyze_drawdown_control(self, extracted_data: Dict, fund_type_code: str = 'UNKNOWN') -> str:
        """分析回撤控制严格度（根据基金类型动态调整阈值）"""
        # 获取净值数据
        performance_data = extracted_data.get('业绩表现', {})
        net_value_data = extracted_data.get('净值数据', {})
        
        # 尝试从不同数据源获取最大回撤
        max_drawdown = None
        
        # 方式1：从业绩表现中获取
        if performance_data and isinstance(performance_data, dict):
            drawdown_str = performance_data.get('最大回撤', '')
            if drawdown_str:
                try:
                    max_drawdown = abs(float(drawdown_str.replace('%', '').replace('－', '-')))
                except:
                    pass
        
        # 方式2：从净值数据中计算
        if max_drawdown is None and net_value_data:
            max_drawdown = self._calculate_max_drawdown(net_value_data)
        
        # 如果没有回撤数据，使用LLM分析
        if max_drawdown is None:
            return self._analyze_drawdown_control_llm(extracted_data, fund_type_code)
        
        # 【核心】根据基金类型动态调整阈值
        if fund_type_code == 'CONVERTIBLE_BOND':
            # 转债基金：高波动品种，阈值放宽至10%
            if max_drawdown <= 5:
                return '极强回撤控制'
            elif max_drawdown <= 10:
                return '较强回撤控制'
            elif max_drawdown <= 15:
                return '中等回撤控制'
            else:
                return '较弱回撤控制'
        else:
            # 纯债/二级债基：低波动品种，阈值严格至5%
            if max_drawdown <= 2:
                return '极强回撤控制'
            elif max_drawdown <= 5:
                return '较强回撤控制'
            elif max_drawdown <= 8:
                return '中等回撤控制'
            else:
                return '较弱回撤控制'
    
    def _calculate_max_drawdown(self, net_value_data: Dict) -> float:
        """从净值数据计算最大回撤"""
        try:
            # 尝试获取净值序列
            nav_list = net_value_data.get('净值序列', [])
            if not nav_list or not isinstance(nav_list, list):
                return None
            
            # 提取净值数值
            values = []
            for item in nav_list:
                if isinstance(item, dict):
                    nav = item.get('单位净值', item.get('净值', None))
                    if nav:
                        try:
                            values.append(float(nav))
                        except:
                            pass
            
            if len(values) < 2:
                return None
            
            # 计算最大回撤
            max_drawdown = 0
            peak = values[0]
            
            for value in values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            return max_drawdown * 100  # 转换为百分比
        except Exception as e:
            print(f"计算最大回撤失败: {str(e)}")
            return None
    
    def _analyze_drawdown_control_llm(self, extracted_data: Dict, fund_type_code: str = 'UNKNOWN') -> str:
        """使用LLM分析回撤控制（当没有量化数据时）"""
        if not self.use_llm:
            return '中等回撤控制'
        
        try:
            macro_data = extracted_data.get('宏观观点', {})
            strategy_text = macro_data.get('投资策略和运作分析', '') if macro_data else ''
            fund_type_context = self._get_fund_type_context(fund_type_code)
            
            prompt = self._build_drawdown_control_prompt(strategy_text, fund_type_context, fund_type_code)
            response = self._call_llm(prompt)
            
            if response:
                return self._parse_drawdown_control_response(response)
            else:
                return '中等回撤控制'
        except Exception as e:
            print(f"LLM回撤控制分析失败: {str(e)}")
            return '中等回撤控制'
    
    def _build_drawdown_control_prompt(self, strategy_text: str, fund_type_context: str, fund_type_code: str) -> str:
        """构建回撤控制分析Prompt"""
        fund_type_section = f"\n{fund_type_context}\n" if fund_type_context else ""
        
        if fund_type_code == 'CONVERTIBLE_BOND':
            threshold_note = "（转债基金阈值：最大回撤≤5%为极强，≤10%为较强，≤15%为中等）"
        else:
            threshold_note = "（纯债/二级债基阈值：最大回撤≤2%为极强，≤5%为较强，≤8%为中等）"
        
        prompt = f"""你是一位专业的基金风控分析师。请基于投资策略文本判断该基金的回撤控制能力。
{fund_type_section}
【投资策略文本】
{strategy_text if strategy_text else "无"}

【判断标准】{threshold_note}
- **极强回撤控制**：策略明确强调严格止损、风险预算管理、动态对冲等风控措施。
- **较强回撤控制**：策略提及风险控制、仓位管理、分散投资等风控手段。
- **中等回撤控制**：策略提及风险但未强调严格风控，或风控措施较为常规。
- **较弱回撤控制**：策略未提及风控，或强调进攻性、高弹性等特征。

请严格按照以下JSON格式输出：
```json
{{
  "风控措施分析": "从策略文本中提取的风控措施",
  "综合判断": "极强回撤控制/较强回撤控制/中等回撤控制/较弱回撤控制",
  "判断理由": "..."
}}
```
"""
        return prompt
    
    def _parse_drawdown_control_response(self, response: str) -> str:
        """解析回撤控制LLM响应"""
        try:
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
                return result.get('综合判断', '中等回撤控制')
            
            if '极强' in response:
                return '极强回撤控制'
            elif '较强' in response:
                return '较强回撤控制'
            elif '较弱' in response:
                return '较弱回撤控制'
            else:
                return '中等回撤控制'
        except Exception:
            return '中等回撤控制'

    # ==========================================
    # 维度四：利率波段收益能力
    # ==========================================
    def _analyze_rate_band(self, macro_data: Dict, holding_data: Dict, fund_type_code: str = 'UNKNOWN') -> str:
        """分析利率波段收益能力"""
        if not self.use_llm:
            return self._analyze_rate_band_fallback(macro_data, holding_data)
        
        try:
            strategy_text = macro_data.get('投资策略和运作分析', '') if macro_data else ''
            bond_holdings = self._prepare_bond_holdings_for_llm(holding_data)
            fund_type_context = self._get_fund_type_context(fund_type_code)
            
            prompt = self._build_rate_band_prompt(strategy_text, bond_holdings, fund_type_context)
            response = self._call_llm(prompt)
            
            if response:
                return self._parse_rate_band_response(response)
            else:
                return self._analyze_rate_band_fallback(macro_data, holding_data)
        except Exception as e:
            print(f"LLM利率波段分析失败: {str(e)}")
            return self._analyze_rate_band_fallback(macro_data, holding_data)
    
    def _build_rate_band_prompt(self, strategy_text: str, bond_holdings: str, fund_type_context: str = '') -> str:
        """构建利率波段分析Prompt"""
        fund_type_section = f"\n{fund_type_context}\n" if fund_type_context else ""
        
        prompt = f"""你是一位专业的债券基金分析师。请基于以下信息判断该基金的利率波段操作能力。
{fund_type_section}
【定义】
利率波段操作：基金经理通过预判利率走势，主动调整久期、杠杆，在利率波动中获取资本利得收益。

【投资策略文本】
{strategy_text if strategy_text else "无"}

【债券持仓数据】
{bond_holdings}

【判断标准】
- **积极波段操作**：策略明确提及利率预判、久期调整、杠杆变化、波段操作等关键词，且持仓显示明显的久期变化特征。
- **适度波段操作**：策略提及利率波段操作，但频率或幅度较为保守。
- **持有到期为主**：策略强调持有到期、票息策略、配置型投资，较少进行波段操作。

请严格按照以下JSON格式输出：
```json
{{
  "策略文本分析": "从策略文本中提取的波段操作特征",
  "持仓结构分析": "从持仓数据中观察的久期特征",
  "综合判断": "积极波段操作/适度波段操作/持有到期为主",
  "判断理由": "..."
}}
```
"""
        return prompt
    
    def _parse_rate_band_response(self, response: str) -> str:
        """解析利率波段LLM响应"""
        try:
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
                return result.get('综合判断', '持有到期为主')
            
            if '积极波段操作' in response:
                return '积极波段操作'
            elif '适度波段操作' in response:
                return '适度波段操作'
            else:
                return '持有到期为主'
        except Exception:
            return '持有到期为主'
    
    def _analyze_rate_band_fallback(self, macro_data: Dict, holding_data: Dict) -> str:
        """利率波段分析的降级方法"""
        if not macro_data:
            return '持有到期为主'
        
        strategy_text = macro_data.get('投资策略和运作分析', '')
        if not strategy_text:
            return '持有到期为主'
        
        # 积极波段关键词
        active_keywords = ['利率波段', '久期调整', '杠杆调整', '利率预判', '波段操作', '资本利得', '利率择时', '久期管理']
        # 适度波段关键词
        moderate_keywords = ['适度波段', '灵活调整', '动态调整', '利率波动']
        # 持有到期关键词
        hold_keywords = ['持有到期', '票息策略', '配置型', '持有策略', '获取票息']
        
        active_count = sum(1 for kw in active_keywords if kw in strategy_text)
        moderate_count = sum(1 for kw in moderate_keywords if kw in strategy_text)
        hold_count = sum(1 for kw in hold_keywords if kw in strategy_text)
        
        if active_count >= 2:
            return '积极波段操作'
        elif active_count >= 1 or moderate_count >= 2:
            return '适度波段操作'
        elif hold_count >= 2:
            return '持有到期为主'
        else:
            return '持有到期为主'

    # ==========================================
    # 辅助方法
    # ==========================================
    def _identify_fund_type(self, fund_name: str = None) -> Dict:
        """识别基金类型"""
        if not fund_name:
            return {'基金类型代码': 'UNKNOWN', '基金类型名称': '未知'}
        
        # 优先根据基金名称判断（更准确）
        if '可转债' in fund_name or '转债' in fund_name:
            return {
                '基金类型': '可转债基金',
                '基金类型代码': 'CONVERTIBLE_BOND',
                '分析重点': ['转债配置', '转股溢价', '正股选择', '双低策略'],
                '置信度': 1.0
            }
        
        # 如果名称判断失败，使用外部识别器
        if self.fund_type_identifier:
            try:
                result = self.fund_type_identifier.identify(fund_name)
                return result
            except Exception as e:
                print(f"基金类型识别失败: {str(e)}")
        
        return {'基金类型代码': 'UNKNOWN', '基金类型名称': '未知'}
    
    def _get_fund_type_context(self, fund_type_code: str) -> str:
        """获取基金类型的上下文信息"""
        if not FUND_TYPE_CONFIG_AVAILABLE:
            return ""
        
        try:
            context = get_fund_type_prompt_context(fund_type_code)
            return context
        except Exception as e:
            print(f"获取基金类型上下文失败: {str(e)}")
            return ""
    
    def _call_llm(self, prompt: str) -> str:
        """调用LLM"""
        if not self.use_llm:
            return None
        
        try:
            client = openai.OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL
            )
            
            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": "你是一位专业的基金分析师，擅长从投资策略和持仓数据中提取关键特征。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
        except Exception as e:
            print(f"LLM调用失败: {str(e)}")
            return None