"""
基金类型识别器
根据基金名称识别基金类型，为后续分析提供针对性指导
"""

import os
import pandas as pd
from typing import Dict, List, Optional


class FundTypeIdentifier:
    """基金类型识别器"""
    
    def __init__(self, fund_list_file: str = None):
        """初始化识别器
        
        Args:
            fund_list_file: 基金列表Excel文件路径
        """
        # 基金列表数据
        self.fund_list_df = None
        
        if fund_list_file is None:
            # 默认路径
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            fund_list_file = os.path.join(base_dir, 'input', '筛选后的基金列表.xlsx')
        
        # 加载基金列表
        self._load_fund_list(fund_list_file)
        
        # 基金类型关键词映射（作为备用方案）
        self.type_keywords = {
            'SECONDARY_BOND': {
                'keywords': ['二级债', '可转债', '增强债', '双利债', '混合债券型基金(二级)'],
                'name': '二级债基/可转债基金',
                'analysis_focus': ['股票仓位', '转债配置', '择时能力', '风格轮动']
            },
            'PRIMARY_STOCK': {
                'keywords': ['股票', '权益', '价值', '成长', '混合', '灵活配置'],
                'name': '股票型/混合型基金',
                'analysis_focus': ['行业配置', '选股能力', '仓位管理', '风格偏好']
            },
            'INDEX_FUND': {
                'keywords': ['指数', 'ETF', 'LOF'],
                'name': '指数型基金',
                'analysis_focus': ['跟踪误差', '指数选择', '增强策略']
            },
            'MONEY_MARKET': {
                'keywords': ['货币', '现金'],
                'name': '货币市场基金',
                'analysis_focus': ['收益率', '流动性管理']
            },
            'QDII': {
                'keywords': ['QDII', '海外', '港股', '美股'],
                'name': 'QDII基金',
                'analysis_focus': ['海外配置', '汇率风险', '区域选择']
            }
        }
    
    def _load_fund_list(self, fund_list_file: str):
        """加载基金列表数据
        
        Args:
            fund_list_file: Excel文件路径
        """
        try:
            if os.path.exists(fund_list_file):
                self.fund_list_df = pd.read_excel(fund_list_file)
                print(f"已加载基金列表: {len(self.fund_list_df)} 条记录")
            else:
                print(f"基金列表文件不存在: {fund_list_file}")
        except Exception as e:
            print(f"加载基金列表失败: {str(e)}")
            self.fund_list_df = None
    
    def identify(self, fund_name: str) -> Dict:
        """
        识别基金类型
        
        Args:
            fund_name: 基金名称
            
        Returns:
            基金类型信息字典
        """
        # 默认结果
        result = {
            '基金类型': '未知',
            '基金类型代码': 'UNKNOWN',
            '分析重点': ['综合分析'],
            '置信度': 0.0
        }
        
        # 优先从Excel中匹配
        if self.fund_list_df is not None:
            excel_result = self._identify_from_excel(fund_name)
            if excel_result:
                return excel_result
        
        # 备用方案：遍历类型关键词进行匹配
        # 特殊处理：优先识别"可转债"关键词
        if '可转债' in fund_name:
            return {
                '基金类型': '可转债基金',
                '基金类型代码': 'SECONDARY_BOND',
                '分析重点': ['转债配置', '择时能力', '风格轮动'],
                '置信度': 1.0
            }
        
        # 其他关键词匹配
        for type_code, type_info in self.type_keywords.items():
            for keyword in type_info['keywords']:
                if keyword in fund_name:
                    result = {
                        '基金类型': type_info['name'],
                        '基金类型代码': type_code,
                        '分析重点': type_info['analysis_focus'],
                        '置信度': 1.0
                    }
                    return result
        
        # 如果没有匹配到，尝试更宽松的匹配
        # 检查是否包含"债券"关键词
        if '债券' in fund_name or '债' in fund_name:
            result = {
                '基金类型': '债券型基金',
                '基金类型代码': 'BOND',
                '分析重点': ['久期管理', '信用分析', '利率波段'],
                '置信度': 0.8
            }
        # 检查是否包含"股票"关键词
        elif '股票' in fund_name or '权益' in fund_name:
            result = {
                '基金类型': '股票型基金',
                '基金类型代码': 'STOCK',
                '分析重点': ['行业配置', '选股能力', '仓位管理'],
                '置信度': 0.8
            }
        
        return result
    
    def _identify_from_excel(self, fund_name: str) -> Optional[Dict]:
        """从Excel中识别基金类型
        
        Args:
            fund_name: 基金名称
            
        Returns:
            基金类型信息字典，如果未找到返回None
        """
        try:
            # 清理基金名称
            # 1. 移除"型证券投资基金"后缀
            clean_name = fund_name.replace('型证券投资基金', '').replace('证券投资基金', '')
            # 2. 移除A/C类后缀
            clean_name = clean_name.replace('A', '').replace('C', '').strip()
            
            # 在Excel中查找匹配的基金
            # 尝试多种匹配方式
            match = None
            
            # 方式1：精确匹配
            match = self.fund_list_df[self.fund_list_df['名称'] == clean_name]
            
            # 方式2：移除"债券"后匹配（如"方正富邦丰利债券" -> "方正富邦丰利债券A"）
            if match.empty:
                # 尝试在Excel名称中查找clean_name的核心部分
                # 例如：clean_name="方正富邦丰利"，Excel中有"方正富邦丰利债券A"
                for idx, row in self.fund_list_df.iterrows():
                    excel_name = row['名称']
                    # 移除A/C后缀
                    excel_name_clean = excel_name.replace('A', '').replace('C', '').strip()
                    
                    # 检查是否包含核心部分
                    if clean_name in excel_name_clean or excel_name_clean in clean_name:
                        match = self.fund_list_df.iloc[[idx]]
                        break
            
            # 方式3：部分匹配（最后手段）
            if match.empty:
                # 提取基金名称的核心部分（前几个字）
                if len(clean_name) > 4:
                    core_name = clean_name[:4]  # 如"方正富邦"
                    match = self.fund_list_df[self.fund_list_df['名称'].str.contains(core_name, na=False)]
            
            if not match.empty:
                # 获取投资类型
                invest_type = match.iloc[0]['投资类型']
                
                # 映射到基金类型代码
                type_mapping = {
                    '混合债券型基金(二级)': {
                        '基金类型': '二级债基',
                        '基金类型代码': 'SECONDARY_BOND',
                        '分析重点': ['股票仓位', '转债配置', '择时能力', '风格轮动'],
                        '置信度': 1.0
                    },
                    '可转债基金': {
                        '基金类型': '可转债基金',
                        '基金类型代码': 'SECONDARY_BOND',
                        '分析重点': ['转债配置', '择时能力', '风格轮动'],
                        '置信度': 1.0
                    }
                }
                
                if invest_type in type_mapping:
                    return type_mapping[invest_type]
            
            return None
            
        except Exception as e:
            print(f"从Excel识别基金类型失败: {str(e)}")
            return None
    
    def get_analysis_guidance(self, fund_type_code: str) -> Dict:
        """
        获取分析指导建议
        
        Args:
            fund_type_code: 基金类型代码
            
        Returns:
            分析指导建议
        """
        guidance = {
            'SECONDARY_BOND': {
                '宏观关注点': ['股市走势', '转债估值', '利率环境'],
                '持仓关注点': ['股票仓位', '转债配置', '债券久期'],
                '业绩归因': ['股票贡献', '转债贡献', '债券贡献']
            },
            'PRIMARY_STOCK': {
                '宏观关注点': ['经济周期', '行业景气', '市场情绪'],
                '持仓关注点': ['行业分布', '重仓股', '仓位水平'],
                '业绩归因': ['行业配置', '个股选择', '仓位择时']
            },
            'INDEX_FUND': {
                '宏观关注点': ['指数走势', '成分股变化'],
                '持仓关注点': ['跟踪误差', '成分股权重'],
                '业绩归因': ['跟踪误差', '增强收益']
            },
            'MONEY_MARKET': {
                '宏观关注点': ['短期利率', '流动性环境'],
                '持仓关注点': ['久期', '信用评级'],
                '业绩归因': ['利息收入', '资本利得']
            },
            'QDII': {
                '宏观关注点': ['海外经济', '汇率走势', '地缘政治'],
                '持仓关注点': ['区域配置', '行业分布', '汇率对冲'],
                '业绩归因': ['区域配置', '汇率影响', '个股选择']
            }
        }
        
        return guidance.get(fund_type_code, {
            '宏观关注点': ['综合分析'],
            '持仓关注点': ['综合分析'],
            '业绩归因': ['综合分析']
        })
    
    def get_all_types(self) -> List[Dict]:
        """
        获取所有支持的基金类型
        
        Returns:
            基金类型列表
        """
        types = []
        for type_code, type_info in self.type_keywords.items():
            types.append({
                '代码': type_code,
                '名称': type_info['name'],
                '关键词': type_info['keywords'],
                '分析重点': type_info['analysis_focus']
            })
        return types


def main():
    """测试函数"""
    identifier = FundTypeIdentifier()
    
    # 测试基金名称
    test_funds = [
        '方正富邦丰利债券型证券投资基金',
        '华夏可转债增强债券型证券投资基金',
        '易方达中小盘混合型证券投资基金',
        '华夏沪深300指数增强型证券投资基金',
        '天弘余额宝货币市场基金'
    ]
    
    print("=" * 80)
    print("基金类型识别测试")
    print("=" * 80)
    
    for fund_name in test_funds:
        result = identifier.identify(fund_name)
        print(f"\n基金名称: {fund_name}")
        print(f"基金类型: {result['基金类型']}")
        print(f"类型代码: {result['基金类型代码']}")
        print(f"分析重点: {', '.join(result['分析重点'])}")
        print(f"置信度: {result['置信度']}")
        
        # 获取分析指导
        guidance = identifier.get_analysis_guidance(result['基金类型代码'])
        print(f"宏观关注点: {', '.join(guidance['宏观关注点'])}")
        print(f"持仓关注点: {', '.join(guidance['持仓关注点'])}")


if __name__ == '__main__':
    main()
