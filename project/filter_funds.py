"""
第一步：基金筛选脚本
根据以下条件筛选基金:
1. 成立时间早于2023年
2. 最新规模不低于2亿且近三年平均规模不低于2亿
"""
import pandas as pd
import numpy as np
from datetime import datetime
import sys
import os

# 设置pandas显示选项
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)

def load_and_process_data(file_path):
    """
    加载并预处理基金数据
    """
    print(f"正在加载数据: {file_path}")
    df = pd.read_excel(file_path)

    # 重命名列名，简化处理
    df.columns = ['代码', '名称', '投资类型', '基金成立日',
                  '最新规模', '2025规模', '2024规模', '2023规模']

    print(f"原始数据总行数: {len(df)}")
    return df

def clean_scale_data(value):
    """
    清理规模数据，将字符串转换为数值
    """
    if pd.isna(value) or value == '--' or value == '':
        return np.nan
    try:
        return float(value)
    except:
        return np.nan

def filter_by_establishment_date(df, cutoff_date='2023-01-01'):
    """
    筛选条件1: 成立时间早于2023年
    """
    print(f"\n筛选条件1: 成立时间早于 {cutoff_date}")

    # 转換成立日期
    df['成立日期'] = pd.to_datetime(df['基金成立日'], errors='coerce')
    cutoff = pd.to_datetime(cutoff_date)

    # 筛选
    mask = df['成立日期'] < cutoff
    filtered_df = df[mask].copy()

    removed_count = len(df) - len(filtered_df)
    print(f"  - 移除 {removed_count} 只基金 (成立时间晚于或等于 {cutoff_date})")
    print(f"  - 保留 {len(filtered_df)} 只基金")

    return filtered_df

def filter_by_scale(df, min_scale=200000000):
    """
    筛选条件2: 最新规模不低于2亿且近三年平均规模不低于2亿
    min_scale: 最小规模，默认2亿元 (200,000,000元)
    """
    print(f"\n筛选条件2: 最新规模 >= {min_scale/100000000:.0f}亿 且 近三年平均规模 >= {min_scale/100000000:.0f}亿")

    # 清理规模数据
    df['最新规模_数值'] = df['最新规模'].apply(clean_scale_data)
    df['2024规模_数值'] = df['2024规模'].apply(clean_scale_data)
    df['2023规模_数值'] = df['2023规模'].apply(clean_scale_data)

    # 计算近三年平均规模 (2023, 2024, 最新)
    # 注意: 2025规模列可能数据不全，使用2023、2024和最新规模计算
    scale_columns = ['2023规模_数值', '2024规模_数值', '最新规模_数值']

    # 计算有效数据数量和平均值
    df['有效年份数'] = df[scale_columns].notna().sum(axis=1)
    df['近三年平均规模'] = df[scale_columns].mean(axis=1, skipna=True)

    # 筛选条件
    # 条件2a: 最新规模 >= 2亿
    mask_latest = df['最新规模_数值'] >= min_scale

    # 条件2b: 近三年平均规模 >= 2亿 (至少有1年数据)
    mask_avg = (df['近三年平均规模'] >= min_scale) & (df['有效年份数'] >= 1)

    # 同时满足两个条件
    mask = mask_latest & mask_avg
    filtered_df = df[mask].copy()

    removed_count = len(df) - len(filtered_df)
    print(f"  - 移除 {removed_count} 只基金 (规模不满足条件)")
    print(f"  - 保留 {len(filtered_df)} 只基金")

    # 打印一些统计信息
    print(f"\n  规模统计:")
    print(f"  - 最新规模范围: {filtered_df['最新规模_数值'].min()/100000000:.2f}亿 ~ {filtered_df['最新规模_数值'].max()/100000000:.2f}亿")
    print(f"  - 近三年平均规模范围: {filtered_df['近三年平均规模'].min()/100000000:.2f}亿 ~ {filtered_df['近三年平均规模'].max()/100000000:.2f}亿")

    return filtered_df

def save_results(df, output_path):
    """
    保存筛选结果 - 将两类基金分别保存到不同的工作表
    """
    # 选择要保存的列
    columns_to_save = ['代码', '名称', '投资类型', '基金成立日',
                       '最新规模', '2024规模', '2023规模',
                       '最新规模_数值', '近三年平均规模']

    output_df = df[columns_to_save].copy()

    # 格式化数值列
    output_df['最新规模(亿元)'] = output_df['最新规模_数值'] / 100000000
    output_df['近三年平均规模(亿元)'] = output_df['近三年平均规模'] / 100000000

    # 删除中间计算列
    output_df = output_df.drop(columns=['最新规模_数值', '近三年平均规模'])

    # 按投资类型分组
    type_stats = output_df['投资类型'].value_counts()
    
    # 创建Excel写入器
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for type_name in type_stats.index:
            # 筛选该类型的基金
            type_df = output_df[output_df['投资类型'] == type_name]
            # 写入到对应的工作表
            type_df.to_excel(writer, sheet_name=type_name, index=False)
            print(f"  - {type_name}: {len(type_df)} 只基金已保存到工作表 '{type_name}'")
    
    print(f"\n筛选结果已保存至: {output_path}")

    return output_df

def main():
    """
    主函数
    """
    print("=" * 80)
    print("基金筛选程序")
    print("=" * 80)

    # 文件路径 - 使用绝对路径
    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 项目根目录
    project_root = os.path.dirname(script_dir)

    input_file = os.path.join(project_root, 'data', 'ifind基金数据.xlsx')
    output_file = os.path.join(project_root, 'input', '筛选后的基金列表.xlsx')

    # 检查输入文件是否存在
    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在: {input_file}")
        sys.exit(1)

    # 加载数据
    df = load_and_process_data(input_file)

    # 筛选条件1: 成立时间早于2023年
    df = filter_by_establishment_date(df, cutoff_date='2023-01-01')

    # 筛选条件2: 规模条件
    df = filter_by_scale(df, min_scale=200000000)  # 2亿元

    # 保存结果
    result_df = save_results(df, output_file)

    # 打印部分结果
    print("\n" + "=" * 80)
    print("筛选结果预览 (前10条)")
    print("=" * 80)
    print(result_df.head(10).to_string())

    print("\n" + "=" * 80)
    print(f"筛选完成! 共筛选出 {len(result_df)} 只基金")
    print("=" * 80)

    # 按投资类型统计
    print("\n按投资类型统计:")
    type_stats = result_df['投资类型'].value_counts()
    for type_name, count in type_stats.items():
        print(f"  - {type_name}: {count} 只")
    
    print("\n" + "=" * 80)
    print("各类基金已分别保存到Excel的不同工作表中")
    print("=" * 80)

if __name__ == '__main__':
    main()
