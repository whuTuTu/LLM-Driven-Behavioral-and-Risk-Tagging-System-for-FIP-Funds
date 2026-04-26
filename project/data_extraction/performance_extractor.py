"""
业绩数据提取器（改进版）
支持A/C类基金分类，分别提取业绩数据
"""

import re
from typing import Dict
from .base_extractor import BaseExtractor


class PerformanceExtractor(BaseExtractor):
    """历史业绩数据提取器"""
    
    def __init__(self):
        """初始化提取器"""
        super().__init__()
    
    def extract(self, text: str, report_type: str = 'Q1') -> Dict:
        """
        提取历史业绩数据

        Args:
            text: 报告文本
            report_type: 报告类型

        Returns:
            提取的业绩数据
        """
        # 1. 提取业绩指标章节
        performance_text = self._extract_performance_section(text, report_type)

        # 2. 检查是否有A/C类基金分类
        has_classification = self._check_fund_classification(performance_text)

        # 3. 解析业绩指标
        if has_classification:
            performance_data = self._parse_performance_with_classification(performance_text)
        else:
            performance_data = self._parse_performance_metrics(performance_text)

        # 4. 提取章节4.5报告期内基金的业绩表现
        report_period_performance = self._extract_report_period_performance(text)
        if report_period_performance:
            performance_data['报告期内业绩表现'] = report_period_performance

        return performance_data
    
    def _extract_performance_section(self, text: str, report_type: str) -> str:
        """
        提取业绩指标章节
        
        Args:
            text: 报告全文
            report_type: 报告类型
            
        Returns:
            业绩指标章节文本
        """
        # 使用finditer处理多个匹配（跳过目录页）
        section3_matches = list(re.finditer(r'§3\s*[^\n]+(.*?)(?=§4\s|§5\s|$)', text, re.DOTALL))
        
        if section3_matches:
            # 选择内容最长的匹配（跳过目录页）
            content = max([m.group(1) for m in section3_matches], key=len)
            if len(content) > 100:
                return content
        
        return text
    
    def _check_fund_classification(self, text: str) -> bool:
        """
        检查是否有A/C类基金分类
        
        Args:
            text: 业绩指标章节文本
            
        Returns:
            是否有分类
        """
        # 查找A类和C类基金标识
        # 注意：PDF文本中可能是"债券 A"或"债券A"格式
        has_a_class = bool(re.search(r'[AＡ]类|债券\s*A|份额\s*A', text))
        has_c_class = bool(re.search(r'[CＣ]类|债券\s*C|份额\s*C', text))

        return has_a_class and has_c_class
    
    def _parse_performance_with_classification(self, text: str) -> Dict:
        """
        解析有A/C类分类的业绩指标

        Args:
            text: 业绩指标章节文本

        Returns:
            解析后的业绩数据
        """
        performance_data = {
            "基金分类": "A/C类",
            "A类基金": {},
            "C类基金": {}
        }

        # 提取主要财务指标（§3.1）
        financial_metrics = self._extract_financial_metrics(text)
        if financial_metrics:
            performance_data['主要财务指标'] = financial_metrics

        # 提取A类基金数据
        a_class_data = self._extract_class_data(text, 'A')
        if a_class_data:
            performance_data["A类基金"] = a_class_data

        # 提取C类基金数据
        c_class_data = self._extract_class_data(text, 'C')
        if c_class_data:
            performance_data["C类基金"] = c_class_data

        return performance_data
    
    def _extract_class_data(self, text: str, class_type: str) -> Dict:
        """
        提取指定类型基金的数据

        Args:
            text: 业绩指标章节文本
            class_type: 基金类型（A或C）

        Returns:
            该类型基金的业绩数据
        """
        data = {}

        # 清理文本
        clean_text = re.sub(r'\n+', ' ', text)
        clean_text = re.sub(r' {2,}', ' ', clean_text)

        # 先查找§3.2.1基金份额净值增长率章节
        # 支持多种格式：
        # 1. "3.2.1 基金份额净值增长率"（方正富邦格式）
        # 2. "净值增长率及其与同期业绩比较基准收益率的比较"（华夏格式）
        section_321_match = re.search(
            r'(?:3\.2\.1\s*)?基金份额净值增长率.*?(?=3\.2\.2|§4|$)',
            clean_text, re.DOTALL
        )

        if not section_321_match:
            # 尝试华夏格式
            section_321_match = re.search(
                r'净值增长率及其与同期业绩比较基准收益率的比较.*?(?=3\.2\.2|§4|$)',
                clean_text, re.DOTALL
            )

        if not section_321_match:
            return data

        section_321_text = section_321_match.group(0)

        # 查找该类型基金的章节
        # 支持多种格式：
        # 1. "方正富邦丰利债券 A"（方正富邦格式）
        # 2. "华夏可转债增强债券 A："（华夏格式，带冒号）
        # 尝试多种模式
        patterns = [
            rf'方正富邦[^C\n]*债券\s*{class_type}\s+(.*?)(?=方正富邦[^C\n]*债券\s*[AC]\s|华夏可转债增强债券\s*[AC]\s*：|3\.2\.2|§4\s|§5\s|$)',
            rf'华夏可转债增强债券\s*{class_type}\s*：\s*(.*?)(?=华夏可转债增强债券\s*[AC]\s*：|方正富邦[^C\n]*债券\s*[AC]\s|3\.2\.2|§4\s|§5\s|$)',
            rf'债券\s*{class_type}\s*：?\s*(.*?)(?=债券\s*[AC]\s*：?|3\.2\.2|§4\s|§5\s|$)',
            rf'{class_type}类\s+(.*?)(?=[AC]类\s|3\.2\.2|§4\s|§5\s|$)',
        ]

        class_match = None
        for pattern in patterns:
            class_match = re.search(pattern, section_321_text, re.DOTALL | re.IGNORECASE)
            if class_match:
                break

        if class_match:
            class_text = class_match.group(1)

            # 合并百分号前的空格（如 "1.48 %" -> "1.48%"）
            class_text = re.sub(r'(\d+\.\d+)\s*%', r'\1%', class_text)

            # 合并被分割的时间段名称（如 "过去三个 月" -> "过去三个月"）
            # 处理多种分割情况
            class_text = re.sub(r'过去三个\s*月', '过去三个月', class_text)
            class_text = re.sub(r'过去三个(?!\s*月)', '过去三个月', class_text)  # 处理"过去三个"后面没有"月"的情况
            class_text = re.sub(r'过去六个\s*月', '过去六个月', class_text)
            class_text = re.sub(r'过去六个(?!\s*月)', '过去六个月', class_text)
            class_text = re.sub(r'过去一\s*年', '过去一年', class_text)
            class_text = re.sub(r'过去一年(?!\s)', '过去一年', class_text)  # 处理"过去一年"后面没有空格的情况
            class_text = re.sub(r'过去三\s*年', '过去三年', class_text)
            class_text = re.sub(r'过去三年(?!\s)', '过去三年', class_text)
            class_text = re.sub(r'过去五\s*年', '过去五年', class_text)
            class_text = re.sub(r'过去五年(?!\s)', '过去五年', class_text)
            class_text = re.sub(r'自基金合\s*同生效起\s*至今', '自基金合同生效起至今', class_text)
            class_text = re.sub(r'自新增份\s*额类别以\s*来至今', '自新增份额类别以来至今', class_text)

            # 提取过去三个月
            # 格式：过去三个月 1.48% 0.05% 0.73% 0.08% 0.75% -0.03%
            # ①净值增长率 ②标准差 ③业绩比较基准收益率 ④业绩比较基准标准差 ⑤①－③ ⑥②－④
            match = re.search(
                r'过去三个月\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%',
                class_text
            )
            if match:
                data['过去三个月收益率'] = float(match.group(1))
                data['过去三个月标准差'] = float(match.group(2))
                data['过去三个月业绩比较基准收益率'] = float(match.group(3))
                data['过去三个月业绩比较基准标准差'] = float(match.group(4))

            # 提取过去六个月
            match = re.search(
                r'过去六个月\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%',
                class_text
            )
            if match:
                data['过去六个月收益率'] = float(match.group(1))
                data['过去六个月标准差'] = float(match.group(2))
                data['过去六个月业绩比较基准收益率'] = float(match.group(3))
                data['过去六个月业绩比较基准标准差'] = float(match.group(4))

            # 提取过去一年
            match = re.search(
                r'过去一年\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%',
                class_text
            )
            if match:
                data['过去一年收益率'] = float(match.group(1))
                data['过去一年标准差'] = float(match.group(2))
                data['过去一年业绩比较基准收益率'] = float(match.group(3))
                data['过去一年业绩比较基准标准差'] = float(match.group(4))

            # 提取过去三年
            match = re.search(
                r'过去三年\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%',
                class_text
            )
            if match:
                data['过去三年收益率'] = float(match.group(1))
                data['过去三年标准差'] = float(match.group(2))
                data['过去三年业绩比较基准收益率'] = float(match.group(3))
                data['过去三年业绩比较基准标准差'] = float(match.group(4))

            # 提取过去五年
            match = re.search(
                r'过去五年\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%',
                class_text
            )
            if match:
                data['过去五年收益率'] = float(match.group(1))
                data['过去五年标准差'] = float(match.group(2))
                data['过去五年业绩比较基准收益率'] = float(match.group(3))
                data['过去五年业绩比较基准标准差'] = float(match.group(4))

        return data
    
    def _parse_performance_metrics(self, text: str) -> Dict:
        """
        解析无分类的业绩指标
        
        Args:
            text: 业绩指标章节文本
            
        Returns:
            解析后的业绩数据
        """
        metrics = {}
        
        # 清理文本：合并被换行分割的关键词
        clean_text = re.sub(r'\n+', ' ', text)
        clean_text = re.sub(r' {2,}', ' ', clean_text)
        # 合并被分割的关键词
        clean_text = re.sub(r'过去三个\s*月', '过去三个月', clean_text)
        clean_text = re.sub(r'过去六个\s*月', '过去六个月', clean_text)
        clean_text = re.sub(r'自基金合\s*同生效起\s*至今', '自基金合同生效起至今', clean_text)
        # 合并百分号前的空格（如 "1.16 %" -> "1.16%"）
        clean_text = re.sub(r'(\d+\.\d+)\s*%', r'\1%', clean_text)
        
        # 提取过去三个月净值增长率和标准差
        # 格式：过去三个月 1.06% 0.07% 0.03% 0.09% 1.03% -0.02%
        # 第一个%是净值增长率，第二个%是标准差
        pattern = r'过去三个月\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%'
        match = re.search(pattern, clean_text)
        if match:
            metrics['过去三个月收益率'] = float(match.group(1))
            metrics['过去三个月标准差'] = float(match.group(2))
        
        # 提取过去六个月数据
        pattern = r'过去六个月\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%'
        match = re.search(pattern, clean_text)
        if match:
            metrics['过去六个月收益率'] = float(match.group(1))
            metrics['过去六个月标准差'] = float(match.group(2))
        
        # 提取过去一年数据
        pattern = r'过去一年\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%'
        match = re.search(pattern, clean_text)
        if match:
            metrics['过去一年收益率'] = float(match.group(1))
            metrics['过去一年标准差'] = float(match.group(2))
        
        # 提取过去三年数据
        pattern = r'过去三年\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%'
        match = re.search(pattern, clean_text)
        if match:
            metrics['过去三年收益率'] = float(match.group(1))
            metrics['过去三年标准差'] = float(match.group(2))
        
        # 提取过去五年数据
        pattern = r'过去五年\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%'
        match = re.search(pattern, clean_text)
        if match:
            metrics['过去五年收益率'] = float(match.group(1))
            metrics['过去五年标准差'] = float(match.group(2))
        
        # 提取成立以来数据
        pattern = r'自基金合同\s*生效起至今\s+(-?\d+\.\d+)%\s+(-?\d+\.\d+)%'
        match = re.search(pattern, clean_text)
        if match:
            metrics['成立以来收益率'] = float(match.group(1))
            metrics['成立以来标准差'] = float(match.group(2))
        
        # 提取本期已实现收益
        pattern = r'本期已实现收益\s+([\d,]+\.?\d*)'
        match = re.search(pattern, clean_text)
        if match:
            value = match.group(1).replace(',', '')
            metrics['本期已实现收益'] = float(value)
        
        # 提取本期利润
        pattern = r'本期利润\s+([\d,]+\.?\d*)'
        match = re.search(pattern, clean_text)
        if match:
            value = match.group(1).replace(',', '')
            metrics['本期利润'] = float(value)
        
        # 提取期末基金资产净值
        pattern = r'期末基金资产净值\s+([\d,]+\.?\d*)'
        match = re.search(pattern, clean_text)
        if match:
            value = match.group(1).replace(',', '')
            metrics['期末资产净值'] = float(value)
        
        # 提取期末基金份额净值
        pattern = r'期末基金份额净值\s+(\d+\.\d+)'
        match = re.search(pattern, clean_text)
        if match:
            metrics['期末份额净值'] = float(match.group(1))
        
        # 计算基金规模（亿元）
        if metrics.get('期末资产净值'):
            metrics['基金规模(亿元)'] = round(metrics['期末资产净值'] / 100000000, 2)
        
        return metrics
    
    def _extract_financial_metrics(self, text: str) -> Dict:
        """
        提取主要财务指标（§3.1）

        Args:
            text: 业绩指标章节文本

        Returns:
            主要财务指标数据
        """
        metrics = {}

        # 清理文本
        clean_text = re.sub(r'\n+', ' ', text)
        clean_text = re.sub(r' {2,}', ' ', clean_text)

        # 查找主要财务指标章节
        match = re.search(r'3\.1\s*主要财务指标(.*?)(?=3\.2|§4|$)', clean_text, re.DOTALL)
        if not match:
            return metrics

        financial_text = match.group(1)

        # 提取A类基金数据
        a_metrics = {}

        # 提取本期已实现收益
        match = re.search(r'本期已实现收益\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)', financial_text)
        if match:
            a_metrics['本期已实现收益'] = float(match.group(1).replace(',', ''))
            c_value = match.group(2).replace(',', '')
            if c_value and c_value != '-':
                metrics['C类基金'] = {'本期已实现收益': float(c_value)}

        # 提取本期利润
        match = re.search(r'本期利润\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)', financial_text)
        if match:
            a_metrics['本期利润'] = float(match.group(1).replace(',', ''))
            c_value = match.group(2).replace(',', '')
            if c_value and c_value != '-':
                if 'C类基金' not in metrics:
                    metrics['C类基金'] = {}
                metrics['C类基金']['本期利润'] = float(c_value)

        # 提取期末基金资产净值
        match = re.search(r'期末基金资产净值\s+([\d,]+\.?\d*)\s+([\d,]+\.?\d*)', financial_text)
        if match:
            a_metrics['期末资产净值'] = float(match.group(1).replace(',', ''))
            a_metrics['基金规模(亿元)'] = round(a_metrics['期末资产净值'] / 100000000, 2)
            c_value = match.group(2).replace(',', '')
            if c_value and c_value != '-':
                if 'C类基金' not in metrics:
                    metrics['C类基金'] = {}
                metrics['C类基金']['期末资产净值'] = float(c_value)
                metrics['C类基金']['基金规模(亿元)'] = round(metrics['C类基金']['期末资产净值'] / 100000000, 2)

        # 提取期末基金份额净值
        match = re.search(r'期末基金份额净值\s+(\d+\.?\d*)\s+(\d+\.?\d*)', financial_text)
        if match:
            a_metrics['期末份额净值'] = float(match.group(1))
            c_value = match.group(2)
            if c_value and c_value != '-':
                if 'C类基金' not in metrics:
                    metrics['C类基金'] = {}
                metrics['C类基金']['期末份额净值'] = float(c_value)

        if a_metrics:
            metrics['A类基金'] = a_metrics

        return metrics

    def _extract_report_period_performance(self, text: str) -> Dict:
        """
        提取章节4.5报告期内基金的业绩表现

        Args:
            text: 报告全文

        Returns:
            报告期内业绩表现数据
        """
        performance = {}

        # 查找章节4.5
        match = re.search(r'4\.5\s*报告期内基金的业绩表现(.*?)(?=4\.6|5\.|§5|$)', text, re.DOTALL)
        if not match:
            return performance

        section_text = match.group(1)

        # 清理文本
        clean_text = re.sub(r'\n+', ' ', section_text)
        clean_text = re.sub(r' {2,}', ' ', clean_text)

        # 提取A类基金数据
        # 格式：截至本报告期末方正富邦丰利债券 A基金份额净值为 1.0401元，本报告期基金份额净值增长率为1.48%
        a_match = re.search(
            r'债券\s*A.*?份额净值为\s*(\d+\.?\d*)元.*?净值增长率为\s*(-?\d+\.?\d*)%',
            clean_text
        )
        if a_match:
            performance['A类基金'] = {
                '期末份额净值': float(a_match.group(1)),
                '报告期净值增长率': float(a_match.group(2))
            }

        # 提取C类基金数据
        c_match = re.search(
            r'债券\s*C.*?份额净值为\s*(\d+\.?\d*)元.*?净值增长率为\s*(-?\d+\.?\d*)%',
            clean_text
        )
        if c_match:
            performance['C类基金'] = {
                '期末份额净值': float(c_match.group(1)),
                '报告期净值增长率': float(c_match.group(2))
            }

        # 提取业绩比较基准收益率
        benchmark_match = re.search(r'业绩比较基准收益率为\s*(-?\d+\.?\d*)%', clean_text)
        if benchmark_match:
            performance['业绩比较基准收益率'] = float(benchmark_match.group(1))

        return performance
