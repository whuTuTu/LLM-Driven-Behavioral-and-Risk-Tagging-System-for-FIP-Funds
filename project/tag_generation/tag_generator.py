"""
标签生成器主类
协调各个子标签生成器，生成完整的基金经理标签体系
"""

import os
import json
from typing import Dict
from .risk_return_tagger import RiskReturnTagger
from .operation_style_tagger import OperationStyleTagger
from .personality_tagger import PersonalityTagger


class TagGenerator:
    """标签生成器"""
    
    def __init__(self, nav_data_dir: str = None):
        """
        初始化标签生成器
        
        Args:
            nav_data_dir: 净值数据目录
        """
        # 如果没有指定净值数据目录，使用默认路径
        if nav_data_dir is None:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            nav_data_dir = os.path.join(project_root, 'data', 'fund_nav')
        
        self.risk_return_tagger = RiskReturnTagger(nav_data_dir)
        self.operation_style_tagger = OperationStyleTagger()
        self.personality_tagger = PersonalityTagger()
    
    def generate_tags(self, fund_name: str, extracted_data: Dict) -> Dict:
        """
        生成基金经理标签体系
        
        Args:
            fund_name: 基金名称
            extracted_data: 提取的数据
            
        Returns:
            完整的标签体系
        """
        tags = {
            "基金名称": fund_name,
            "收益风险标签": {},
            "操作风格标签": {},
            "个性特征标签": {}
        }
        
        # 1. 生成收益风险标签
        tags["收益风险标签"] = self.risk_return_tagger.generate(extracted_data)
        
        # 2. 生成操作风格标签
        tags["操作风格标签"] = self.operation_style_tagger.generate(extracted_data, fund_name)
        
        # 3. 生成个性特征标签
        tags["个性特征标签"] = self.personality_tagger.generate(extracted_data)
        
        return tags
    
    def generate_profile(self, fund_name: str, tags: Dict) -> str:
        """
        生成基金经理画像描述

        Args:
            fund_name: 基金名称
            tags: 标签体系

        Returns:
            画像描述文本
        """
        # 提取收益风险标签
        risk_return = tags.get('收益风险标签', {})
        metrics = risk_return.get('基础量化指标', {})

        # 提取波动特征（从"弹性中波 (年化波动10.05%)"中提取"中波"）
        volatility_feature = risk_return.get('业绩波动特征', '中波')
        if '低波' in volatility_feature:
            volatility_level = '低波'
        elif '高波' in volatility_feature:
            volatility_level = '高波'
        else:
            volatility_level = '中波'

        # 提取操作风格标签
        operation = tags.get('操作风格标签', {})
        investment_style = operation.get('投资风格', '左侧布局')
        if '左侧' in investment_style:
            position_style = '左侧布局'
        elif '右侧' in investment_style:
            position_style = '右侧跟随'
        else:
            position_style = '均衡配置'

        # 提取个性特征标签
        personality = tags.get('个性特征标签', {})

        # 处理权益风格描述
        equity_style = personality.get('权益风格', '均衡配置')
        if '无权益持仓' in equity_style:
            equity_desc = '以纯债配置为主'
        else:
            equity_desc = f'权益端偏好{equity_style}风格'

        profile = f"""
【{fund_name}基金经理画像】

该基金经理属于{volatility_level}型投资风格，注重风险控制与收益平衡。

核心特征：
• 收益风险：{volatility_level}特征明显，过去一年收益率{metrics.get('近一年收益率', 'N/A')}，过去三年收益率{metrics.get('近三年收益率', 'N/A')}，最大回撤{metrics.get('最大回撤', 'N/A')}。风险调整后收益表现{risk_return.get('风险调整后收益', '稳健')}。

• 操作风格：{position_style}为主，{investment_style}，注重估值安全边际，善于在市场波动中把握配置机会。

• 个性特征：{personality.get('回撤控制', '中等回撤控制')}的回撤控制能力，{personality.get('信用下沉', '高等级为主')}信用下沉，{equity_desc}。利率波段操作{personality.get('利率波段', '持有到期为主')}。

投资理念：追求绝对收益，注重下行保护，在固收底仓基础上适度增强收益。
"""

        return profile.strip()
    
    def save_tags(self, fund_name: str, tags: Dict, output_dir: str):
        """
        保存标签数据
        
        Args:
            fund_name: 基金名称
            tags: 标签数据
            output_dir: 输出目录
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存JSON
        filename = os.path.join(output_dir, f"{fund_name}_标签体系.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(tags, f, ensure_ascii=False, indent=2)
        
        print(f"  - 标签数据已保存: {filename}")
    
    def save_profile(self, fund_name: str, profile: str, output_dir: str):
        """
        保存画像描述
        
        Args:
            fund_name: 基金名称
            profile: 画像描述
            output_dir: 输出目录
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存TXT
        filename = os.path.join(output_dir, f"{fund_name}_画像描述.txt")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(profile)
        
        print(f"  - 画像描述已保存: {filename}")
