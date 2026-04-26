"""
标签生成模块
基于提取的数据生成基金经理标签
"""

from .tag_generator import TagGenerator
from .risk_return_tagger import RiskReturnTagger
from .operation_style_tagger import OperationStyleTagger
from .personality_tagger import PersonalityTagger

__all__ = [
    'TagGenerator',
    'RiskReturnTagger',
    'OperationStyleTagger',
    'PersonalityTagger'
]
