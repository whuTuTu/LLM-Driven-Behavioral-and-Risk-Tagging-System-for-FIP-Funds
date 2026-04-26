"""
基金类型特性配置
定义二级债基和转债基金等不同类型基金的特性差异
"""

# 基金类型特性配置
FUND_TYPE_CHARACTERISTICS = {
    'SECONDARY_BOND': {
        'name': '二级债基',
        'description': '混合债券型基金(二级)，可投资股票和债券',
        
        # 资产配置限制
        'asset_constraints': {
            'equity_max': 20,  # 股票仓位上限20%
            'equity_typical': (5, 15),  # 典型股票仓位范围5%-15%
            'convertible_max': None,  # 可转债无明确上限
            'convertible_typical': (0, 10),  # 典型可转债仓位范围0%-10%
        },
        
        # 收益风险特征
        'risk_return': {
            'volatility_level': '中低波',  # 波动水平
            'drawdown_target': (2, 5),  # 目标回撤范围2%-5%
            'return_source': ['债券票息', '利率波段', '股票增强', '转债增强'],
            'risk_source': ['利率风险', '信用风险', '权益风险'],
        },
        
        # 分析重点
        'analysis_focus': {
            'primary': ['股票仓位管理', '转债配置策略', '债券久期管理'],
            'secondary': ['信用下沉', '利率波段', '风格轮动'],
            'metrics': ['权益仓位变化', '转债仓位变化', '债券久期'],
        },
        
        # Prompt增强信息
        'prompt_context': """
【二级债基特性】
- 契约限制：股票仓位≤20%，主要收益来源为债券票息+权益增强
- 风险特征：中低波动，目标回撤2%-5%，追求绝对收益
- 操作重点：股票仓位择时、转债配置、债券久期管理
- 典型仓位：股票5%-15%，可转债0%-10%，债券70%-90%
- 收益来源：债券票息(主要) + 利率波段 + 股票增强 + 转债增强
- 风险来源：利率风险 + 信用风险 + 权益风险(次要)
""",
    },
    
    'CONVERTIBLE_BOND': {
        'name': '可转债基金',
        'description': '主要投资可转债，兼具股性和债性',
        
        # 资产配置限制
        'asset_constraints': {
            'equity_max': None,  # 无明确股票仓位限制
            'equity_typical': (0, 5),  # 典型股票仓位范围0%-5%
            'convertible_min': 60,  # 可转债仓位下限60%
            'convertible_typical': (60, 95),  # 典型可转债仓位范围60%-95%
        },
        
        # 收益风险特征
        'risk_return': {
            'volatility_level': '中高波',  # 波动水平
            'drawdown_target': (5, 15),  # 目标回撤范围5%-15%
            'return_source': ['转债股性收益', '转债债性保护', '正股上涨'],
            'risk_source': ['正股下跌风险', '转债估值风险', '流动性风险'],
        },
        
        # 分析重点
        'analysis_focus': {
            'primary': ['转债仓位管理', '转债估值分析', '正股选择'],
            'secondary': ['偏股型/偏债型配置', '转股溢价率', '纯债溢价率'],
            'metrics': ['转债仓位', '平均转股溢价率', '偏股型转债占比'],
        },
        
        # Prompt增强信息
        'prompt_context': """
【可转债基金特性】
- 契约限制：可转债仓位≥60%，主要投资可转债
- 风险特征：中高波动，目标回撤5%-15%，收益弹性大
- 操作重点：转债仓位管理、转债估值分析、偏股型/偏债型配置
- 典型仓位：可转债60%-95%，股票0%-5%，债券0%-30%
- 收益来源：转债股性收益(主要) + 转债债性保护 + 正股上涨
- 风险来源：正股下跌风险 + 转债估值风险 + 流动性风险
- 特殊关注：转股溢价率、纯债溢价率、偏股型转债占比
""",
    },
    
    'PRIMARY_BOND': {
        'name': '纯债型基金',
        'description': '主要投资债券，不投资股票和可转债',
        
        # 资产配置限制
        'asset_constraints': {
            'equity_max': 0,  # 不投资股票
            'convertible_max': 0,  # 不投资可转债
            'bond_min': 80,  # 债券仓位下限80%
        },
        
        # 收益风险特征
        'risk_return': {
            'volatility_level': '低波',  # 波动水平
            'drawdown_target': (1, 3),  # 目标回撤范围1%-3%
            'return_source': ['债券票息', '利率波段', '信用利差'],
            'risk_source': ['利率风险', '信用风险'],
        },
        
        # 分析重点
        'analysis_focus': {
            'primary': ['久期管理', '信用分析', '利率波段'],
            'secondary': ['杠杆策略', '期限结构'],
            'metrics': ['组合久期', '信用评级分布', '杠杆率'],
        },
        
        # Prompt增强信息
        'prompt_context': """
【纯债型基金特性】
- 契约限制：不投资股票和可转债，主要投资债券
- 风险特征：低波动，目标回撤1%-3%，追求稳健收益
- 操作重点：久期管理、信用分析、利率波段
- 典型仓位：债券80%-100%，无股票和可转债
- 收益来源：债券票息(主要) + 利率波段 + 信用利差
- 风险来源：利率风险 + 信用风险
""",
    },
}


def get_fund_type_characteristics(fund_type_code: str) -> dict:
    """
    获取基金类型特性
    
    Args:
        fund_type_code: 基金类型代码
        
    Returns:
        基金类型特性字典
    """
    return FUND_TYPE_CHARACTERISTICS.get(fund_type_code, {})


def get_fund_type_prompt_context(fund_type_code: str) -> str:
    """
    获取基金类型的Prompt上下文信息
    
    Args:
        fund_type_code: 基金类型代码
        
    Returns:
        Prompt上下文字符串
    """
    characteristics = get_fund_type_characteristics(fund_type_code)
    return characteristics.get('prompt_context', '')


def get_analysis_focus(fund_type_code: str) -> dict:
    """
    获取基金类型的分析重点
    
    Args:
        fund_type_code: 基金类型代码
        
    Returns:
        分析重点字典
    """
    characteristics = get_fund_type_characteristics(fund_type_code)
    return characteristics.get('analysis_focus', {
        'primary': ['综合分析'],
        'secondary': [],
        'metrics': []
    })


def get_asset_constraints(fund_type_code: str) -> dict:
    """
    获取基金类型的资产配置限制
    
    Args:
        fund_type_code: 基金类型代码
        
    Returns:
        资产配置限制字典
    """
    characteristics = get_fund_type_characteristics(fund_type_code)
    return characteristics.get('asset_constraints', {})


def get_risk_return_characteristics(fund_type_code: str) -> dict:
    """
    获取基金类型的收益风险特征
    
    Args:
        fund_type_code: 基金类型代码
        
    Returns:
        收益风险特征字典
    """
    characteristics = get_fund_type_characteristics(fund_type_code)
    return characteristics.get('risk_return', {})


# 基金类型对比分析
FUND_TYPE_COMPARISON = """
## 二级债基 vs 可转债基金 对比分析

### 1. 资产配置差异
- **二级债基**：股票≤20%，可转债0%-10%，债券70%-90%
- **可转债基金**：可转债≥60%，股票0%-5%，债券0%-30%

### 2. 收益风险特征差异
- **二级债基**：中低波动，回撤2%-5%，追求绝对收益
- **可转债基金**：中高波动，回撤5%-15%，收益弹性大

### 3. 主要收益来源差异
- **二级债基**：债券票息(主要) + 利率波段 + 股票增强 + 转债增强
- **可转债基金**：转债股性收益(主要) + 转债债性保护 + 正股上涨

### 4. 主要风险来源差异
- **二级债基**：利率风险 + 信用风险 + 权益风险(次要)
- **可转债基金**：正股下跌风险 + 转债估值风险 + 流动性风险

### 5. 操作重点差异
- **二级债基**：股票仓位择时、转债配置、债券久期管理
- **可转债基金**：转债仓位管理、转债估值分析、偏股型/偏债型配置

### 6. 分析指标差异
- **二级债基**：权益仓位变化、转债仓位变化、债券久期
- **可转债基金**：转债仓位、平均转股溢价率、偏股型转债占比

### 7. 投资风格判断差异
- **二级债基**：
  - 左侧：市场下跌时增加股票/转债仓位
  - 右侧：市场上涨时增加股票/转债仓位
  - 关注：股票仓位变化与市场走势的关系
  
- **可转债基金**：
  - 左侧：市场下跌时增加偏股型转债配置
  - 右侧：市场上涨时增加偏股型转债配置
  - 关注：转债结构变化与市场走势的关系

### 8. 信用下沉分析差异
- **二级债基**：主要分析债券持仓的信用评级分布
- **可转债基金**：转债本身信用评级相对不重要，更关注正股质量

### 9. 回撤控制分析差异
- **二级债基**：目标回撤2%-5%，严控回撤是核心
- **可转债基金**：目标回撤5%-15%，接受更大波动换取收益弹性

### 10. 利率波段分析差异
- **二级债基**：利率波段是重要收益来源，久期管理关键
- **可转债基金**：利率影响相对次要，更关注正股和转债估值
"""


if __name__ == '__main__':
    # 测试
    print("=" * 80)
    print("基金类型特性测试")
    print("=" * 80)
    
    for fund_type_code in ['SECONDARY_BOND', 'CONVERTIBLE_BOND', 'PRIMARY_BOND']:
        print(f"\n基金类型: {fund_type_code}")
        print("-" * 80)
        
        characteristics = get_fund_type_characteristics(fund_type_code)
        print(f"名称: {characteristics.get('name')}")
        print(f"描述: {characteristics.get('description')}")
        
        print("\n资产配置限制:")
        constraints = get_asset_constraints(fund_type_code)
        for key, value in constraints.items():
            print(f"  - {key}: {value}")
        
        print("\n收益风险特征:")
        risk_return = get_risk_return_characteristics(fund_type_code)
        for key, value in risk_return.items():
            print(f"  - {key}: {value}")
        
        print("\n分析重点:")
        analysis_focus = get_analysis_focus(fund_type_code)
        print(f"  - 主要: {analysis_focus.get('primary')}")
        print(f"  - 次要: {analysis_focus.get('secondary')}")
        print(f"  - 指标: {analysis_focus.get('metrics')}")
        
        print("\nPrompt上下文:")
        prompt_context = get_fund_type_prompt_context(fund_type_code)
        print(prompt_context)
    
    print("\n" + "=" * 80)
    print("基金类型对比分析")
    print("=" * 80)
    print(FUND_TYPE_COMPARISON)
