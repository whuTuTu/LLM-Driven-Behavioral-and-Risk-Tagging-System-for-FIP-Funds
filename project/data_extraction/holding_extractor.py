"""
基金持仓信息提取器（改进版）
正确提取表格数据
"""

import re
from typing import Dict, List
from .base_extractor import BaseExtractor


class HoldingExtractor(BaseExtractor):
    """基金持仓信息提取器"""
    
    def __init__(self):
        """初始化提取器"""
        super().__init__()
    
    def extract(self, text: str, report_type: str = 'Q1') -> Dict:
        """
        提取基金持仓信息

        Args:
            text: 报告文本
            report_type: 报告类型

        Returns:
            提取的持仓数据
        """
        # 1. 提取投资组合报告章节
        portfolio_text = self._extract_portfolio_section(text, report_type)

        # 2. 提取各个部分
        # 2.1 报告期末基金资产组合情况
        asset_allocation = self._extract_asset_allocation(portfolio_text, report_type)

        # 2.2 报告期末按行业分类的境内股票投资组合
        stock_by_industry = self._extract_stock_by_industry(portfolio_text, report_type)

        # 2.3 报告期末按公允价值占基金资产净值比例大小排序的前十名股票投资明细
        top_stocks = self._extract_stock_holdings(portfolio_text, report_type)

        # 2.4 报告期末按债券品种分类的债券投资组合
        bond_by_type = self._extract_bond_by_type(portfolio_text, report_type)

        # 2.5 报告期末按公允价值占基金资产净值比例大小排序的前五名债券投资明细
        top_bonds = self._extract_top_bonds(portfolio_text, report_type)

        # 3. 汇总结果
        holding_data = {
            "报告期末基金资产组合情况": asset_allocation,
            "按行业分类的境内股票投资组合": stock_by_industry,
            "前十名股票投资明细": top_stocks,
            "按债券品种分类的债券投资组合": bond_by_type,
            "前五名债券投资明细": top_bonds
        }

        return holding_data
    
    def _extract_portfolio_section(self, text: str, report_type: str) -> str:
        """
        提取投资组合报告章节

        Args:
            text: 报告全文
            report_type: 报告类型

        Returns:
            投资组合报告章节文本
        """
        # 根据报告类型确定章节编号
        if report_type in ['Q1', 'Q2', 'Q3', 'Q4']:
            section_num = '§5'
            next_section = '§6'
        elif report_type == 'Semi-Annual':
            section_num = '§7'
            next_section = '§8'
        else:
            section_num = '§8'
            next_section = '§9'
        
        # 提取章节
        # 改进：使用更精确的匹配，确保匹配到的是章节标题而不是目录
        # 查找所有可能的章节起始位置
        # 注意：有些基金的章节编号后没有空格（如方正基金），有些有空格（如华夏基金）
        # 【修复】支持两种格式：
        # 1. 旧格式: §5 投资组合报告
        # 2. 新格式(2025年起): 投资组合报告 (无§符号)
        pattern = rf'{re.escape(section_num)}\s*投资组合报告'
        matches = list(re.finditer(pattern, text))
        
        # 如果旧格式未匹配，尝试新格式
        if not matches:
            pattern_new = r'投资组合报告'
            matches = list(re.finditer(pattern_new, text))
        
        if not matches:
            return ""
        
        # 使用最后一个匹配（通常是正文部分，而不是目录）
        if len(matches) > 1:
            # 如果有多个匹配，选择包含实际数据的那个
            # 通常正文部分会有"金额单位"或"序号"等关键词
            for match in reversed(matches):
                start_idx = match.start()
                # 检查后续5000字符是否包含数据关键词
                check_text = text[start_idx:start_idx+5000]
                if '金额单位' in check_text or '序号' in check_text:
                    # 找到下一个章节的位置
                    next_match = re.search(rf'{re.escape(next_section)}\s', text[start_idx:])
                    if next_match:
                        return text[start_idx:start_idx+next_match.start()].strip()
                    else:
                        return text[start_idx:].strip()
            # 如果都没找到，使用最后一个匹配
            start_idx = matches[-1].start()
        else:
            start_idx = matches[0].start()
        
        # 找到下一个章节的位置
        next_match = re.search(rf'{re.escape(next_section)}\s', text[start_idx:])
        if next_match:
            return text[start_idx:start_idx+next_match.start()].strip()
        else:
            return text[start_idx:].strip()
    
    def _extract_asset_allocation(self, text: str, report_type: str) -> Dict:
        """
        提取大类资产配置（改进版，正确提取表格）

        Args:
            text: 投资组合报告文本
            report_type: 报告类型

        Returns:
            大类资产配置数据
        """
        # 根据报告类型确定子章节编号
        if report_type in ['Q1', 'Q2', 'Q3', 'Q4']:
            subsection_num = '5.1'
            next_subsection = '5.2'
        elif report_type == 'Semi-Annual':
            subsection_num = '7.1'
            next_subsection = '7.2'
        else:
            subsection_num = '8.1'
            next_subsection = '8.2'
        
        # 提取子章节
        pattern = rf'{re.escape(subsection_num)}\s*[^\n]+(.*?)(?={re.escape(next_subsection)}\s|§\d+\s|$)'
        match = re.search(pattern, text, re.DOTALL)
        
        if not match:
            return {}
        
        allocation_text = match.group(1).strip()
        
        # 解析表格数据
        allocation = {}
        
        # 清理文本
        clean_text = re.sub(r'\n+', ' ', allocation_text)
        clean_text = re.sub(r' {2,}', ' ', clean_text)
        
        # 提取各类资产
        # 格式：序号 项目 金额 占比
        # 例如：1权益投资 7,931,336.20 1.62
        
        # 提取权益投资
        match = re.search(r'1\s*权益投资\s+([\d,]+\.?\d*)\s+(-?\d+\.?\d+)', clean_text)
        if match:
            allocation['权益投资'] = f"{match.group(2)}%"
        
        # 提取固定收益投资
        match = re.search(r'3\s*固定收益投资\s+([\d,]+\.?\d*)\s+(-?\d+\.?\d+)', clean_text)
        if match:
            allocation['固定收益投资'] = f"{match.group(2)}%"
        
        # 提取银行存款和结算备付金合计
        # 支持多种格式："银行存款和结算备付金合计" 或 "银行存款和结算备付金 合计"
        match = re.search(r'7\s*银行存款和结算备付金\s*合计\s+([\d,]+\.?\d*)\s+(-?\d+\.?\d+)', clean_text)
        if match:
            allocation['银行存款和结算备付金'] = f"{match.group(2)}%"
        
        # 提取其他资产
        # 支持多种格式："其他资产" 或 "其他各项资产"
        match = re.search(r'8\s*其他(?:各项)?资产\s+([\d,]+\.?\d*)\s+(-?\d+\.?\d+)', clean_text)
        if match:
            allocation['其他资产'] = f"{match.group(2)}%"
        
        # 如果没有提取到数据，保存原始文本
        if not allocation:
            allocation = {"原始文本": allocation_text[:1000]}
        
        return allocation
    
    def _extract_stock_holdings(self, text: str, report_type: str) -> List[Dict]:
        """
        提取股票持仓明细（改进版，正确提取表格）

        Args:
            text: 投资组合报告文本
            report_type: 报告类型

        Returns:
            股票持仓列表
        """
        # 根据报告类型确定子章节编号
        # 使用5.3.1章节（前十名股票投资明细）而不是5.2（按行业分类）
        if report_type in ['Q1', 'Q2', 'Q3', 'Q4']:
            subsection_num = '5.3.1'
        elif report_type == 'Semi-Annual':
            subsection_num = '7.3.1'
        else:
            subsection_num = '8.3.1'
        
        # 提取子章节
        # 改进停止条件：使用具体的章节编号
        # 对于5.3.1，下一个章节是5.4
        parts = subsection_num.split('.')
        if len(parts) == 3:
            # 格式如 5.3.1，下一个是 5.4
            next_subsection = f"{parts[0]}.{int(parts[1]) + 1}"
        else:
            next_subsection = str(int(subsection_num) + 1)
        
        pattern = rf'{re.escape(subsection_num)}\s*[^\n]+(.*?)(?={re.escape(next_subsection)}\s|§\d+\s|$)'
        match = re.search(pattern, text, re.DOTALL)
        
        if not match:
            return []
        
        stock_text = match.group(1).strip()
        
        # 解析表格数据
        stocks = []
        
        # 按行分割
        lines = stock_text.split('\n')
        
        for line in lines:
            # 提取股票数据
            # 格式：序号 股票代码股票名称数量(股)公允价值(元)占基金资产净值比例(%)
            # 例如：1 600900长江电力 35,000973,350.00 0.25
            
            # 先匹配序号、股票代码、股票名称
            match = re.search(r'(\d+)\s+(\d{6})([^\d]+)\s*', line)
            if not match:
                continue
            
            seq = int(match.group(1))
            code = match.group(2)
            name = match.group(3).strip()
            
            # 获取剩余文本
            remaining = line[match.end():]
            
            # 提取数量、公允价值、占比
            # 格式：数量公允价值 占比
            # 例如：35,000973,350.00 0.25
            # 关键：找到小数点，然后向前分割
            
            # 找到小数点
            decimal_match = re.search(r'([\d,]+)\.(\d+)\s+(\d+\.\d+)', remaining)
            if not decimal_match:
                continue
            
            before_decimal = decimal_match.group(1)
            after_decimal = decimal_match.group(2)
            ratio = decimal_match.group(3)
            
            # 从before_decimal中分离数量和公允价值
            # 方法：根据实际数据特点分割
            # 例如：35,000973,350 → 数量=35,000，公允价值=973,350
            # 规律：数量的千位分隔符后面有3位数字，然后是公允价值（可能有千位分隔符）
            
            commas = [i for i, c in enumerate(before_decimal) if c == ',']
            
            if len(commas) >= 2:
                # 有多个逗号
                # 检查第一个逗号后面是否有6位数字+逗号的格式
                # 如果有，则第一个逗号是数量的千位分隔符
                first_comma_pos = commas[0]
                after_first_comma = before_decimal[first_comma_pos+1:]
                
                # 检查是否有6位数字+逗号的格式
                if len(after_first_comma) >= 7 and after_first_comma[6] == ',':
                    # 第一个逗号是数量的千位分隔符
                    # 分割点：第一个逗号后面3位数字之后
                    split_pos = first_comma_pos + 4  # 逗号(1) + 3位数字(3)
                    quantity_str = before_decimal[:split_pos]
                    value_str = before_decimal[split_pos:] + '.' + after_decimal
                else:
                    # 使用倒数第二个逗号作为分割点
                    split_pos = commas[-2]
                    quantity_str = before_decimal[:split_pos]
                    value_str = before_decimal[split_pos+1:] + '.' + after_decimal
            elif len(commas) == 1:
                # 只有一个逗号，需要判断
                # 如果逗号后面有3位数字，则是公允价值的千位分隔符
                after_comma = before_decimal[commas[0]+1:]
                if len(after_comma) == 3:
                    # 逗号后面有3位数字，这是公允价值的千位分隔符
                    # 数量在逗号前面
                    quantity_str = before_decimal[:commas[0]]
                    value_str = before_decimal[commas[0]+1:] + '.' + after_decimal
                else:
                    # 逗号是数量的千位分隔符
                    quantity_str = before_decimal
                    value_str = after_decimal
            else:
                # 没有逗号，无法分割
                continue
            
            try:
                stock = {
                    "序号": seq,
                    "股票代码": code,
                    "股票名称": name,
                    "占净值比例": f"{ratio}%"
                }
                stocks.append(stock)
            except:
                continue
        
        # 如果没有提取到，保存原始文本
        if not stocks:
            stocks = [{"原始文本": stock_text[:1000]}]
        
        return stocks
    
    def _extract_bond_holdings(self, text: str, report_type: str) -> Dict:
        """
        提取债券持仓明细（改进版，正确提取表格）

        Args:
            text: 投资组合报告文本
            report_type: 报告类型

        Returns:
            债券持仓数据
        """
        # 根据报告类型确定子章节编号
        if report_type in ['Q1', 'Q2', 'Q3', 'Q4']:
            subsection_num = '5.4'
        elif report_type == 'Semi-Annual':
            subsection_num = '7.4'
        else:
            subsection_num = '8.4'
        
        # 提取子章节
        # 改进停止条件：使用具体的章节编号，避免匹配到数字中的小数点
        next_subsection = str(int(subsection_num.split('.')[0]) + 0.1) if '.' in subsection_num else str(int(subsection_num) + 1)
        pattern = rf'{re.escape(subsection_num)}\s*[^\n]+(.*?)(?={re.escape(next_subsection)}\s|§\d+\s|$)'
        match = re.search(pattern, text, re.DOTALL)
        
        if not match:
            return {}
        
        bond_text = match.group(1).strip()
        
        # 解析表格数据
        bonds = {}
        
        # 按行分割
        lines = bond_text.split('\n')
        
        for line in lines:
            # 提取债券数据
            # 格式：序号 债券品种 公允价值(元) 占基金资产净值比例(%)
            match = re.search(
                r'(\d+)\s+([^\d]+?)\s+([\d,]+\.?\d*)\s+(\d+\.\d+)%', 
                line
            )
            
            if match:
                bond_type = match.group(2).strip()
                bonds[bond_type] = match.group(4) + '%'
        
        # 如果没有提取到，保存原始文本
        if not bonds:
            bonds = {"原始文本": bond_text[:1000]}
        
        return bonds
    
    def _extract_top_bonds(self, text: str, report_type: str) -> List[Dict]:
        """
        提取前五大重仓债券（改进版，正确提取表格）

        Args:
            text: 投资组合报告文本
            report_type: 报告类型

        Returns:
            前五大重仓债券列表
        """
        # 根据报告类型确定子章节编号
        if report_type in ['Q1', 'Q2', 'Q3', 'Q4']:
            subsection_num = '5.5'
            next_subsection = '5.6'
        elif report_type == 'Semi-Annual':
            subsection_num = '7.5'
            next_subsection = '7.6'
        else:
            subsection_num = '8.5'
            next_subsection = '8.6'
        
        # 提取子章节
        pattern = rf'{re.escape(subsection_num)}\s*[^\n]+(.*?)(?={re.escape(next_subsection)}\s|§\d+\s|$)'
        match = re.search(pattern, text, re.DOTALL)
        
        if not match:
            return []
        
        top_bond_text = match.group(1).strip()
        
        # 解析表格数据
        top_bonds = []
        
        # 按行分割，处理跨行数据
        lines = top_bond_text.split('\n')
        
        # 合并跨行的债券名称
        merged_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # 跳过表头和页眉页脚
            if '序号' in line or '报告' in line or '第' in line or '页' in line:
                i += 1
                continue
            
            # 检查是否是债券数据行（以数字开头）
            if re.match(r'^\d', line):
                # 检查下一行是否是债券名称的续行
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    # 如果下一行不是以数字开头，且不是章节标题，则是债券名称的续行
                    if not re.match(r'^\d+\.\d+', next_line) and not re.match(r'^\d', next_line) and '报告' not in next_line:
                        line = line + next_line
                        i += 1
                
                merged_lines.append(line)
            
            i += 1
        
        # 提取债券数据
        for line in merged_lines:
            # 格式：序号(1位) + 债券代码(6位) + 债券名称 + 数量 + 公允价值 + 占比
            # 例如：123240001424民生银行二级300,00030,748,972.60 7.92
            # 或者：324021024国开10 200,00021,144,931.51 5.44
            
            # 提取序号
            match = re.match(r'^(\d)', line)
            if not match:
                continue
            
            seq_num = int(match.group(1))
            remaining = line[1:].strip()  # 去除前导空格
            
            # 提取债券代码（6位数字）
            code_match = re.match(r'^(\d{6})', remaining)
            if not code_match:
                continue
            
            bond_code = code_match.group(1)
            remaining = remaining[code_match.end():].strip()  # 去除前导空格
            
            # 提取债券名称、数量、公允价值、占比
            # 格式：债券名称 + 数量 + 公允价值 + 占比
            # 例如：民生银行二级300,00030,748,972.60 7.92
            # 或者：国开10 200,00021,144,931.51 5.44
            
            # 先找到小数点，确定公允价值的位置
            decimal_match = re.search(r'([\d,]+)\.(\d+)\s+(\d+\.\d+)', remaining)
            if not decimal_match:
                continue
            
            before_decimal = decimal_match.group(1)
            after_decimal = decimal_match.group(2)
            ratio = decimal_match.group(3)
            
            # 从before_decimal中分离数量和公允价值
            # 关键：找到数量的千位分隔符
            # 例如：300,00030,748,972 → 数量=300,000，公允价值=30,748,972
            # 规律：数量的千位分隔符后面有3位数字，然后是公允价值
            
            commas = [i for i, c in enumerate(before_decimal) if c == ',']
            
            if len(commas) >= 2:
                # 有多个逗号
                # 从前往后找，找到第一个逗号后面有3位数字的位置
                found = False
                for pos in commas:
                    after_comma = before_decimal[pos+1:]
                    # 检查后面是否有3位数字
                    if len(after_comma) >= 3:
                        # 检查这3位数字后面是否是数字（公允价值的开始）
                        if len(after_comma) > 3 and after_comma[3].isdigit():
                            # 这是数量的千位分隔符
                            quantity_str = before_decimal[:pos+4]  # 包含逗号和后面3位数字
                            value_str = before_decimal[pos+4:] + '.' + after_decimal
                            found = True
                            break
                
                if not found:
                    # 使用倒数第二个逗号作为分割点
                    split_pos = commas[-2]
                    quantity_str = before_decimal[:split_pos]
                    value_str = before_decimal[split_pos+1:] + '.' + after_decimal
            elif len(commas) == 1:
                # 只有一个逗号，需要判断
                # 如果逗号后面有3位数字，则是公允价值的千位分隔符
                after_comma = before_decimal[commas[0]+1:]
                if len(after_comma) == 3:
                    # 逗号后面有3位数字，这是公允价值的千位分隔符
                    # 数量在逗号前面
                    quantity_str = before_decimal[:commas[0]]
                    value_str = before_decimal[commas[0]+1:] + '.' + after_decimal
                else:
                    # 逗号是数量的千位分隔符
                    quantity_str = before_decimal
                    value_str = after_decimal
            else:
                # 没有逗号，无法分割
                continue
            
            # 提取债券名称（在数量之前）
            name_match = re.match(r'([^\d]+)', remaining)
            if not name_match:
                continue
            
            bond_name = name_match.group(1).strip()
            
            try:
                bond = {
                    "序号": seq_num,
                    "债券代码": bond_code,
                    "债券名称": bond_name,
                    "占净值比例": f"{ratio}%"
                }
                top_bonds.append(bond)
            except:
                continue
        
        # 如果没有提取到，保存原始文本
        if not top_bonds:
            top_bonds = [{"原始文本": top_bond_text[:1000]}]
        
        return top_bonds

    def _extract_stock_by_industry(self, text: str, report_type: str) -> List[Dict]:
        """
        提取按行业分类的境内股票投资组合

        Args:
            text: 投资组合报告文本
            report_type: 报告类型

        Returns:
            按行业分类的股票投资组合
        """
        # 根据报告类型确定子章节编号
        if report_type in ['Q1', 'Q2', 'Q3', 'Q4']:
            subsection_num = '5.2.1'
        elif report_type == 'Semi-Annual':
            subsection_num = '7.2.1'
        else:
            subsection_num = '8.2.1'

        # 提取子章节
        parts = subsection_num.split('.')
        next_subsection = f"{parts[0]}.{int(parts[1]) + 1}"
        pattern = rf'{re.escape(subsection_num)}\s*[^\n]+(.*?)(?={re.escape(next_subsection)}\s|§\d+\s|$)'
        match = re.search(pattern, text, re.DOTALL)

        if not match:
            return []

        industry_text = match.group(1).strip()

        # 解析表格数据
        industries = []

        # 按行分割，处理跨行数据
        lines = industry_text.split('\n')

        # 合并跨行的行业名称
        merged_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]

            # 跳过表头和页眉页脚
            if '代码' in line or '报告' in line or '第' in line or '页' in line:
                i += 1
                continue

            # 检查是否是行业数据行（以字母A-S开头）
            if re.match(r'^[A-S]', line):
                # 检查下一行是否是行业名称的续行
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    # 如果下一行不是以字母开头，且不是章节标题，则是行业名称的续行
                    if not re.match(r'^[A-S]', next_line) and not re.match(r'^\d+\.\d+', next_line) and '报告' not in next_line:
                        line = line + next_line
                        i += 1

                merged_lines.append(line)

            i += 1

        # 提取行业数据
        for line in merged_lines:
            # 格式：代码 + 行业名称 + 公允价值 + 占比
            # 例如：A农、林、牧、渔业 116,190.00 0.03
            # 或者：D电力、热力、燃气及水生产和供应业 1,133,750.00 0.29

            # 提取代码
            match = re.match(r'^([A-S])', line)
            if not match:
                continue

            code = match.group(1)
            remaining = line[1:]

            # 提取行业名称、公允价值、占比
            # 使用正则表达式提取
            data_match = re.search(r'([^\d]+?)\s+([\d,]+\.?\d*)\s+(\d+\.\d+)', remaining)
            if data_match:
                industry = {
                    "行业代码": code,
                    "行业名称": data_match.group(1).strip(),
                    "占净值比例": f"{data_match.group(3)}%"
                }
                industries.append(industry)

        # 如果没有提取到，保存原始文本
        if not industries:
            industries = [{"原始文本": industry_text[:1000]}]

        return industries

    def _extract_top_stocks(self, text: str, report_type: str) -> List[Dict]:
        """
        提取前十名股票投资明细（使用已有的_extract_stock_holdings方法）

        Args:
            text: 投资组合报告文本
            report_type: 报告类型

        Returns:
            前十名股票投资明细
        """
        # 复用已有的股票持仓提取方法
        return self._extract_stock_holdings(text, report_type)

    def _extract_bond_by_type(self, text: str, report_type: str) -> Dict:
        """
        提取按债券品种分类的债券投资组合

        Args:
            text: 投资组合报告文本
            report_type: 报告类型

        Returns:
            按债券品种分类的债券投资组合
        """
        # 根据报告类型确定子章节编号
        if report_type in ['Q1', 'Q2', 'Q3', 'Q4']:
            subsection_num = '5.4'
        elif report_type == 'Semi-Annual':
            subsection_num = '7.4'
        else:
            subsection_num = '8.4'

        # 提取子章节
        parts = subsection_num.split('.')
        next_subsection = f"{parts[0]}.{int(parts[1]) + 1}"
        pattern = rf'{re.escape(subsection_num)}\s*[^\n]+(.*?)(?={re.escape(next_subsection)}\s|§\d+\s|$)'
        match = re.search(pattern, text, re.DOTALL)

        if not match:
            return {}

        bond_text = match.group(1).strip()

        # 解析表格数据
        bonds = {}

        # 清理文本
        clean_text = re.sub(r'\n+', ' ', bond_text)
        clean_text = re.sub(r' {2,}', ' ', clean_text)

        # 提取债券品种数据
        # 格式：序号 债券品种 公允价值 占比
        pattern = r'(\d+)\s*([^\d]+?)\s+([\d,]+\.?\d*)\s+(\d+\.\d+)'
        matches = re.finditer(pattern, clean_text)

        for match in matches:
            bond_type = match.group(2).strip()
            bonds[bond_type] = f"{match.group(4)}%"

        # 如果没有提取到，保存原始文本
        if not bonds:
            bonds = {"原始文本": bond_text[:1000]}

        return bonds
