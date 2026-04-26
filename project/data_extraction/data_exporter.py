"""
数据导出器
将提取的数据导出为结构化格式（JSON、Excel、CSV）
"""

import os
import json
import pandas as pd
from typing import Dict, List
from datetime import datetime


class DataExporter:
    """数据导出器"""
    
    def __init__(self, output_dir: str):
        """
        初始化导出器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def export_fund_data(self, fund_name: str, fund_data: Dict, formats: List[str] = ['json', 'excel']):
        """
        导出单只基金的数据
        
        Args:
            fund_name: 基金名称
            fund_data: 基金数据字典
            formats: 导出格式列表
        """
        for format_type in formats:
            if format_type == 'json':
                self._export_to_json(fund_name, fund_data)
            elif format_type == 'excel':
                self._export_to_excel(fund_name, fund_data)
            elif format_type == 'csv':
                self._export_to_csv(fund_name, fund_data)
    
    def export_all_funds(self, all_funds_data: Dict, formats: List[str] = ['json', 'excel']):
        """
        导出所有基金的数据
        
        Args:
            all_funds_data: 所有基金数据字典
            formats: 导出格式列表
        """
        # 导出汇总数据
        summary_data = self._create_summary(all_funds_data)
        
        for format_type in formats:
            if format_type == 'json':
                self._export_summary_to_json(summary_data)
            elif format_type == 'excel':
                self._export_summary_to_excel(summary_data)
        
        # 导出每只基金的详细数据
        for fund_name, fund_data in all_funds_data.items():
            self.export_fund_data(fund_name, fund_data, formats)
    
    def _export_to_json(self, fund_name: str, fund_data: Dict):
        """
        导出为JSON格式
        
        Args:
            fund_name: 基金名称
            fund_data: 基金数据
        """
        filename = os.path.join(self.output_dir, f"{fund_name}_提取数据.json")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(fund_data, f, ensure_ascii=False, indent=2)
        
        print(f"  - JSON数据已导出: {filename}")
    
    def _export_to_excel(self, fund_name: str, fund_data: Dict):
        """
        导出为Excel格式
        
        Args:
            fund_name: 基金名称
            fund_data: 基金数据
        """
        filename = os.path.join(self.output_dir, f"{fund_name}_提取数据.xlsx")
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # 导出宏观观点
            if '宏观观点' in fund_data:
                self._write_dict_to_sheet(writer, fund_data['宏观观点'], '宏观观点')
            
            # 导出基金经理信息
            if '基金经理信息' in fund_data:
                self._write_dict_to_sheet(writer, fund_data['基金经理信息'], '基金经理信息')
            
            # 导出业绩数据
            if '业绩数据' in fund_data:
                self._write_dict_to_sheet(writer, fund_data['业绩数据'], '业绩数据')
            
            # 导出持仓数据
            if '持仓数据' in fund_data:
                holding_data = fund_data['持仓数据']
                
                # 大类资产配置
                if '大类资产配置' in holding_data:
                    self._write_dict_to_sheet(writer, holding_data['大类资产配置'], '资产配置')
                
                # 股票持仓
                if '股票持仓' in holding_data and holding_data['股票持仓']:
                    df = pd.DataFrame(holding_data['股票持仓'])
                    df.to_excel(writer, sheet_name='股票持仓', index=False)
                
                # 债券持仓
                if '债券持仓' in holding_data and holding_data['债券持仓']:
                    self._write_dict_to_sheet(writer, holding_data['债券持仓'], '债券持仓')
                
                # 前五大重仓债券
                if '前五大重仓债券' in holding_data and holding_data['前五大重仓债券']:
                    df = pd.DataFrame(holding_data['前五大重仓债券'])
                    df.to_excel(writer, sheet_name='重仓债券', index=False)
        
        print(f"  - Excel数据已导出: {filename}")
    
    def _export_to_csv(self, fund_name: str, fund_data: Dict):
        """
        导出为CSV格式
        
        Args:
            fund_name: 基金名称
            fund_data: 基金数据
        """
        # 为每种数据类型创建单独的CSV文件
        for data_type, data in fund_data.items():
            if isinstance(data, dict):
                df = pd.DataFrame([data])
            elif isinstance(data, list):
                df = pd.DataFrame(data)
            else:
                continue
            
            filename = os.path.join(self.output_dir, f"{fund_name}_{data_type}.csv")
            df.to_csv(filename, index=False, encoding='utf-8-sig')
        
        print(f"  - CSV数据已导出到: {self.output_dir}")
    
    def _export_summary_to_json(self, summary_data: Dict):
        """
        导出汇总数据为JSON
        
        Args:
            summary_data: 汇总数据
        """
        filename = os.path.join(self.output_dir, "所有基金提取数据汇总.json")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        
        print(f"  - 汇总JSON已导出: {filename}")
    
    def _export_summary_to_excel(self, summary_data: Dict):
        """
        导出汇总数据为Excel
        
        Args:
            summary_data: 汇总数据
        """
        filename = os.path.join(self.output_dir, "所有基金提取数据汇总.xlsx")
        
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            # 导出基金列表
            if '基金列表' in summary_data:
                df = pd.DataFrame(summary_data['基金列表'])
                df.to_excel(writer, sheet_name='基金列表', index=False)
            
            # 导出业绩汇总
            if '业绩汇总' in summary_data:
                df = pd.DataFrame(summary_data['业绩汇总'])
                df.to_excel(writer, sheet_name='业绩汇总', index=False)
        
        print(f"  - 汇总Excel已导出: {filename}")
    
    def _create_summary(self, all_funds_data: Dict) -> Dict:
        """
        创建汇总数据
        
        Args:
            all_funds_data: 所有基金数据
            
        Returns:
            汇总数据字典
        """
        summary = {
            "导出时间": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "基金数量": len(all_funds_data),
            "基金列表": [],
            "业绩汇总": []
        }
        
        for fund_name, fund_data in all_funds_data.items():
            # 基金列表
            fund_info = {
                "基金名称": fund_name,
                "报告数量": len(fund_data.get('报告列表', []))
            }
            summary['基金列表'].append(fund_info)
            
            # 业绩汇总
            if '业绩数据' in fund_data:
                performance = fund_data['业绩数据']
                performance_info = {
                    "基金名称": fund_name,
                    "过去一年收益率": performance.get('过去一年收益率', 'N/A'),
                    "过去一年标准差": performance.get('过去一年标准差', 'N/A'),
                    "波动水平": performance.get('波动水平', 'N/A'),
                    "基金规模(亿元)": performance.get('基金规模(亿元)', 'N/A')
                }
                summary['业绩汇总'].append(performance_info)
        
        return summary
    
    def _write_dict_to_sheet(self, writer, data: Dict, sheet_name: str):
        """
        将字典写入Excel工作表
        
        Args:
            writer: Excel写入器
            data: 数据字典
            sheet_name: 工作表名称
        """
        # 将嵌套字典展平为一维字典
        flat_data = self._flatten_dict(data)
        
        # 转换为DataFrame
        df = pd.DataFrame(list(flat_data.items()), columns=['指标', '值'])
        
        # 写入工作表
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    
    def _flatten_dict(self, d: Dict, parent_key: str = '', sep: str = '_') -> Dict:
        """
        展平嵌套字典
        
        Args:
            d: 嵌套字典
            parent_key: 父键名
            sep: 分隔符
            
        Returns:
            展平后的字典
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # 列表转换为字符串
                items.append((new_key, str(v)))
            else:
                items.append((new_key, v))
        return dict(items)
