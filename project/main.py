"""
主程序入口
整合数据提取和标签生成两大模块
"""

import os
import sys
import warnings
from datetime import datetime

# 抑制openpyxl的样式警告
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入数据提取模块
from data_extraction import (
    MacroViewExtractor,
    PerformanceExtractor,
    HoldingExtractor,
    DataExporter
)

# 导入标签生成模块
from tag_generation import TagGenerator

# 导入基金类型识别器
from fund_type_identifier import FundTypeIdentifier


class FundAnalysisPipeline:
    """基金分析流程"""
    
    def __init__(self, reports_dir: str, output_dir: str):
        """
        初始化分析流程
        
        Args:
            reports_dir: 报告文件目录
            output_dir: 输出目录
        """
        self.reports_dir = reports_dir
        self.output_dir = output_dir
        
        # 创建输出子目录
        self.extracted_data_dir = os.path.join(output_dir, 'extracted_data')
        self.tags_dir = os.path.join(output_dir, 'tags')
        self.profiles_dir = os.path.join(output_dir, 'profiles')
        
        # 初始化提取器
        self.macro_extractor = MacroViewExtractor()
        self.performance_extractor = PerformanceExtractor()
        self.holding_extractor = HoldingExtractor()
        
        # 初始化导出器
        self.data_exporter = DataExporter(self.extracted_data_dir)
        
        # 初始化标签生成器
        self.tag_generator = TagGenerator()
        
        # 初始化基金类型识别器
        self.fund_type_identifier = FundTypeIdentifier()
    
    def run(self):
        """运行完整分析流程"""
        print("=" * 80)
        print("基金分析流程启动")
        print("=" * 80)
        print(f"报告目录: {self.reports_dir}")
        print(f"输出目录: {self.output_dir}")
        print(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        # 阶段一：数据提取（每个报告单独处理）
        print("\n【阶段一：数据提取】")
        results = self._extract_all_reports()
        
        # 阶段二：标签生成（基于最完整的报告数据）
        print("\n【阶段二：标签生成】")
        all_tags = self._generate_all_tags(results)
        
        # 生成汇总报告
        print("\n生成汇总报告...")
        self._generate_summary_report(results, all_tags)
        
        print("\n" + "=" * 80)
        print("分析流程完成！")
        print("=" * 80)
        print(f"提取数据目录: {self.extracted_data_dir}")
        print(f"标签数据目录: {self.tags_dir}")
        print(f"画像描述目录: {self.profiles_dir}")
        print("=" * 80)
    
    def _extract_all_reports(self) -> list:
        """
        提取所有报告的数据（每个报告单独处理并导出）
        
        Returns:
            所有报告的处理结果列表
        """
        import glob
        import json
        
        results = []
        
        # 查找所有PDF文件
        pdf_pattern = os.path.join(self.reports_dir, "*.pdf")
        pdf_files = glob.glob(pdf_pattern)
        
        if not pdf_files:
            print(f"未找到PDF文件: {pdf_pattern}")
            return []
        
        print(f"找到 {len(pdf_files)} 个PDF文件\n")
        
        # 处理每个文件
        for i, filepath in enumerate(pdf_files, 1):
            filename = os.path.basename(filepath)
            print(f"[{i}/{len(pdf_files)}] 处理文件: {filename}")
            
            result = self._process_single_report(filepath)
            results.append(result)
        
        # 生成提取汇总报告
        self._generate_extraction_summary(results)
        
        return results
    
    def _process_single_report(self, filepath: str) -> dict:
        """
        处理单个报告并导出MD文件
        
        Args:
            filepath: PDF文件路径
            
        Returns:
            处理结果字典
        """
        filename = os.path.basename(filepath)
        
        try:
            # 解析文件名
            report_info = self.macro_extractor.parse_report_info(filename)
            fund_name = report_info.get('fund_name', 'Unknown')
            report_type = report_info.get('report_type', 'Q1')
            
            print(f"  - 基金: {fund_name}")
            print(f"  - 报告类型: {report_info.get('period', '')} {report_info.get('year', '')}")
            
            # 识别基金类型
            fund_type_info = self.fund_type_identifier.identify(fund_name)
            fund_type = fund_type_info['基金类型代码']
            
            print(f"  - 基金类型: {fund_type_info['基金类型']}")
            
            # 设置宏观观点提取器的基金类型
            self.macro_extractor.set_fund_type(fund_type)
            
            # 提取PDF文本
            text = self.macro_extractor.extract_text_from_pdf(filepath)
            
            if not text:
                print(f"  - 警告: 无法提取文本，跳过该文件")
                return {
                    'file': filepath,
                    'success': False,
                    'error': '无法提取文本'
                }
            
            print(f"  - 文本长度: {len(text)} 字符")
            
            # 提取各类数据
            print("  - 提取宏观观点...")
            macro_data = self.macro_extractor.extract(text, report_type)
            
            print("  - 提取业绩数据...")
            performance_data = self.performance_extractor.extract(text, report_type)
            
            print("  - 提取持仓数据...")
            holding_data = self.holding_extractor.extract(text, report_type)
            
            # 计算完整度得分
            score = self._calculate_data_completeness(
                macro_data, performance_data, holding_data
            )
            
            # 评估提取效果
            if score > 1000:
                effect = "优秀"
            elif score > 500:
                effect = "良好"
            else:
                effect = "需改进"
            
            print(f"  - 数据完整度得分: {score} ({effect})")
            
            # 导出MD文件
            base_name = filename.replace('.pdf', '')
            output_file = os.path.join(self.extracted_data_dir, f"{base_name}_提取结果.md")
            os.makedirs(self.extracted_data_dir, exist_ok=True)
            
            self._export_report_md(
                output_file, base_name, filepath, text, report_type, score, effect,
                macro_data, performance_data, holding_data
            )
            
            print(f"  - 结果已导出: {output_file}")
            
            return {
                'file': filepath,
                'fund_name': fund_name,
                'report_type': report_type,
                'report_info': report_info,
                'fund_type_info': fund_type_info,
                'score': score,
                'effect': effect,
                'output_file': output_file,
                'data': {
                    '宏观观点': macro_data,
                    '业绩数据': performance_data,
                    '持仓数据': holding_data
                },
                'success': True
            }
            
        except Exception as e:
            print(f"  - 处理失败: {str(e)}")
            return {
                'file': filepath,
                'success': False,
                'error': str(e)
            }
    
    def _calculate_data_completeness(self, macro_data: dict, 
                                     performance_data: dict, holding_data: dict) -> int:
        """
        计算数据完整度得分
        
        Args:
            macro_data: 宏观观点数据
            performance_data: 业绩数据
            holding_data: 持仓数据
            
        Returns:
            完整度得分
        """
        score = 0
        
        # 宏观观点得分
        if macro_data.get('投资策略和运作分析'):
            score += len(macro_data['投资策略和运作分析'])
        if macro_data.get('宏观经济展望'):
            score += len(macro_data['宏观经济展望'])
        
        # 业绩数据得分（处理A/C类基金）
        if performance_data.get('基金分类') == 'A/C类':
            # A类基金数据
            a_class = performance_data.get('A类基金', {})
            if a_class.get('过去一年收益率'):
                score += 100
            if a_class.get('过去三年收益率'):
                score += 100
            
            # 主要财务指标
            if performance_data.get('主要财务指标', {}).get('A类基金'):
                financial = performance_data['主要财务指标']['A类基金']
                if financial.get('期末资产净值'):
                    score += 100
        else:
            # 非A/C类基金
            if performance_data.get('过去一年收益率'):
                score += 100
            if performance_data.get('过去三年收益率'):
                score += 100
            if performance_data.get('期末资产净值'):
                score += 100
        
        # 持仓数据得分（使用新的字段名）
        if holding_data.get('报告期末基金资产组合情况'):
            allocation = holding_data['报告期末基金资产组合情况']
            if isinstance(allocation, dict) and '原始文本' not in allocation:
                score += len(allocation) * 10
        
        if holding_data.get('前十名股票投资明细'):
            stocks = holding_data['前十名股票投资明细']
            if isinstance(stocks, list) and stocks and '原始文本' not in stocks[0]:
                score += len(stocks) * 10
        
        if holding_data.get('按债券品种分类的债券投资组合'):
            bonds = holding_data['按债券品种分类的债券投资组合']
            if isinstance(bonds, dict) and '原始文本' not in bonds:
                score += len(bonds) * 10
        
        if holding_data.get('前五名债券投资明细'):
            top_bonds = holding_data['前五名债券投资明细']
            if isinstance(top_bonds, list) and top_bonds and '原始文本' not in top_bonds[0]:
                score += len(top_bonds) * 10
        
        return score
    
    def _export_report_md(self, output_file, base_name, filepath, text, report_type, score, effect,
                          macro_data, performance_data, holding_data):
        """
        导出单个报告的MD文件
        
        Args:
            output_file: 输出文件路径
            base_name: 基础文件名
            filepath: 源文件路径
            text: 文本内容
            report_type: 报告类型
            score: 完整度得分
            effect: 提取效果
            macro_data: 宏观观点数据
            performance_data: 业绩数据
            holding_data: 持仓数据
        """
        import json
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# {base_name} - 数据提取结果\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**源文件**: {filepath}\n\n")
            f.write(f"**文本长度**: {len(text)} 字符\n\n")
            f.write(f"**报告类型**: {report_type}\n\n")
            f.write(f"**数据完整度得分**: {score} ({effect})\n\n")
            
            f.write("---\n\n")
            
            # 1. 宏观观点
            f.write("## 1. 宏观观点提取器\n\n")
            f.write(f"- 投资策略和运作分析长度: {len(macro_data.get('投资策略和运作分析', ''))} 字符\n")
            f.write(f"- 宏观经济展望长度: {len(macro_data.get('宏观经济展望', ''))} 字符\n\n")
            
            if macro_data.get('投资策略和运作分析'):
                f.write("### 投资策略和运作分析（完整内容）\n\n")
                f.write(macro_data['投资策略和运作分析'])
                f.write("\n\n")
            
            if macro_data.get('宏观经济展望'):
                f.write("### 宏观经济展望（完整内容）\n\n")
                f.write(macro_data['宏观经济展望'])
                f.write("\n\n")
            
            # 2. 业绩数据（简化版，完整版参考test_extractors.py）
            f.write("## 2. 业绩数据提取器\n\n")
            f.write("```json\n")
            f.write(json.dumps(performance_data, ensure_ascii=False, indent=2))
            f.write("\n```\n\n")
            
            # 3. 持仓数据（简化版）
            f.write("## 3. 投资组合数据提取器\n\n")
            f.write("```json\n")
            f.write(json.dumps(holding_data, ensure_ascii=False, indent=2))
            f.write("\n```\n")
    
    def _generate_extraction_summary(self, results: list):
        """
        生成提取汇总报告
        
        Args:
            results: 所有报告的处理结果
        """
        summary_file = os.path.join(self.output_dir, "数据提取汇总报告.md")
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("# 数据提取汇总报告\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**处理文件总数**: {len(results)}\n\n")
            
            # 统计信息
            success_count = sum(1 for r in results if r.get('success'))
            fail_count = len(results) - success_count
            
            f.write(f"**成功处理**: {success_count} 个\n\n")
            f.write(f"**处理失败**: {fail_count} 个\n\n")
            
            f.write("---\n\n")
            
            # 按效果分类
            excellent = [r for r in results if r.get('success') and r.get('effect') == '优秀']
            good = [r for r in results if r.get('success') and r.get('effect') == '良好']
            need_improve = [r for r in results if r.get('success') and r.get('effect') == '需改进']
            
            f.write("## 提取效果统计\n\n")
            f.write(f"- 优秀: {len(excellent)} 个\n")
            f.write(f"- 良好: {len(good)} 个\n")
            f.write(f"- 需改进: {len(need_improve)} 个\n\n")
            
            # 详细结果表格
            f.write("## 详细结果\n\n")
            f.write("| 序号 | 文件名 | 基金名称 | 得分 | 效果 | 状态 |\n")
            f.write("|------|--------|----------|------|------|------|\n")
            
            for i, result in enumerate(results, 1):
                file_name = os.path.basename(result['file'])
                fund_name = result.get('fund_name', 'N/A')
                if result.get('success'):
                    f.write(f"| {i} | {file_name} | {fund_name} | {result['score']} | {result['effect']} | 成功 |\n")
                else:
                    f.write(f"| {i} | {file_name} | {fund_name} | - | - | 失败 |\n")
            
            f.write("\n")
            
            # 失败文件列表
            if fail_count > 0:
                f.write("## 失败文件详情\n\n")
                for result in results:
                    if not result.get('success'):
                        f.write(f"- **{os.path.basename(result['file'])}**: {result.get('error', '未知错误')}\n")
                f.write("\n")
            
            # 平均得分
            if success_count > 0:
                avg_score = sum(r['score'] for r in results if r.get('success')) / success_count
                f.write(f"## 平均得分\n\n")
                f.write(f"**{avg_score:.2f}**\n")
        
        print(f"提取汇总报告已保存: {summary_file}")
    
    def _generate_all_tags(self, results: list) -> dict:
        """
        生成所有基金的标签
        
        逻辑说明：
        - 收益风险标签：基于得分最高的报告生成（保持原逻辑）
        - 操作风格标签：每个报告都分析生成短期标签，然后聚合为长期标签
        - 个性特征标签：基于得分最高的报告生成（保持原逻辑）
        
        Args:
            results: 所有报告的处理结果
            
        Returns:
            所有基金标签字典
        """
        # 按基金名称分组所有报告
        fund_reports = {}
        
        for result in results:
            if not result.get('success'):
                continue
            
            fund_name = result.get('fund_name')
            if not fund_name:
                continue
            
            if fund_name not in fund_reports:
                fund_reports[fund_name] = []
            fund_reports[fund_name].append(result)
        
        all_tags = {}
        
        for fund_name, reports in fund_reports.items():
            print(f"\n生成标签: {fund_name}")
            print(f"  - 报告数量: {len(reports)}")
            
            # 收益风险标签：不需要报告数据，直接生成
            print("  - 生成收益风险标签...")
            risk_return_tags = self.tag_generator.risk_return_tagger.generate(fund_name)
            
            # 操作风格标签：每个报告都分析，生成短期标签，然后聚合为长期标签
            print("  - 分析操作风格标签（短期→长期）...")
            short_term_operation_tags = []
            
            # 先构建报告映射：按年份和报告类型分组
            report_map = {}  # {year: {'Q1': report, 'Q2': report, 'Q3': report, 'Q4': report, 'annual': report, 'semi': report}}
            for report in reports:
                report_filename = os.path.basename(report.get('file', ''))
                report_name = report_filename.replace('.pdf', '')
                
                # 解析年份
                import re
                year_match = re.search(r'(\d{4})', report_name)
                if not year_match:
                    continue
                year = year_match.group(1)
                
                if year not in report_map:
                    report_map[year] = {}
                
                # 判断报告类型
                if '年度报告' in report_name or '年报' in report_name:
                    report_map[year]['annual'] = report
                elif '中期报告' in report_name or '半年报' in report_name:
                    report_map[year]['semi'] = report
                elif '第1季度' in report_name or '一季报' in report_name or 'Q1' in report_name:
                    report_map[year]['Q1'] = report
                elif '第2季度' in report_name or '二季报' in report_name or 'Q2' in report_name:
                    report_map[year]['Q2'] = report
                elif '第3季度' in report_name or '三季报' in report_name or 'Q3' in report_name:
                    report_map[year]['Q3'] = report
                elif '第4季度' in report_name or '四季报' in report_name or 'Q4' in report_name:
                    report_map[year]['Q4'] = report
            
            # 按年份处理，选择最佳报告
            # 策略：Q1和Q3使用季报，Q2优先使用半年报，Q4优先使用年报
            for year, year_reports in sorted(report_map.items()):
                # Q1: 使用一季报
                if 'Q1' in year_reports:
                    report = year_reports['Q1']
                    report_name = os.path.basename(report.get('file', '')).replace('.pdf', '')
                    print(f"    - Q1使用季报: {report_name}")
                    self._process_report_for_operation_tags(fund_name, report, report_name, short_term_operation_tags)

                # Q2: 优先使用半年报，如果质量低则使用二季报
                q2_processed = False
                if 'semi' in year_reports:
                    semi_report = year_reports['semi']
                    semi_score = semi_report.get('score', 0)
                    if semi_score > 500:
                        report_name = os.path.basename(semi_report.get('file', '')).replace('.pdf', '')
                        print(f"    - Q2使用半年报（得分{semi_score}）: {report_name}")
                        self._process_report_for_operation_tags(fund_name, semi_report, report_name, short_term_operation_tags)
                        q2_processed = True
                
                if not q2_processed and 'Q2' in year_reports:
                    report = year_reports['Q2']
                    report_name = os.path.basename(report.get('file', '')).replace('.pdf', '')
                    print(f"    - Q2使用季报: {report_name}")
                    self._process_report_for_operation_tags(fund_name, report, report_name, short_term_operation_tags)

                # Q3: 使用三季报
                if 'Q3' in year_reports:
                    report = year_reports['Q3']
                    report_name = os.path.basename(report.get('file', '')).replace('.pdf', '')
                    print(f"    - Q3使用季报: {report_name}")
                    self._process_report_for_operation_tags(fund_name, report, report_name, short_term_operation_tags)

                # Q4: 优先使用年报，如果质量低则使用四季报
                q4_processed = False
                if 'annual' in year_reports:
                    annual_report = year_reports['annual']
                    annual_score = annual_report.get('score', 0)
                    if annual_score > 500:
                        report_name = os.path.basename(annual_report.get('file', '')).replace('.pdf', '')
                        print(f"    - Q4使用年报（得分{annual_score}）: {report_name}")
                        self._process_report_for_operation_tags(fund_name, annual_report, report_name, short_term_operation_tags)
                        q4_processed = True
                
                if not q4_processed and 'Q4' in year_reports:
                    report = year_reports['Q4']
                    report_name = os.path.basename(report.get('file', '')).replace('.pdf', '')
                    print(f"    - Q4使用季报: {report_name}")
                    self._process_report_for_operation_tags(fund_name, report, report_name, short_term_operation_tags)
            
            # 聚合为长期操作风格标签
            long_term_operation_tags = self._aggregate_operation_style_tags(short_term_operation_tags)
            
            # 个性特征标签：每个报告都分析，生成短期标签，然后聚合为长期标签
            print("  - 分析个性特征标签（短期→长期）...")
            short_term_personality_tags = []
            
            # 使用相同的报告映射逻辑（优先使用年报/中报）
            for year, year_reports in sorted(report_map.items()):
                # Q1: 使用一季报
                if 'Q1' in year_reports:
                    report = year_reports['Q1']
                    report_name = os.path.basename(report.get('file', '')).replace('.pdf', '')
                    self._process_report_for_personality_tags(fund_name, report, report_name, short_term_personality_tags)

                # Q2: 优先使用半年报，如果质量低则使用二季报
                q2_processed = False
                if 'semi' in year_reports:
                    semi_report = year_reports['semi']
                    semi_score = semi_report.get('score', 0)
                    if semi_score > 500:
                        report_name = os.path.basename(semi_report.get('file', '')).replace('.pdf', '')
                        self._process_report_for_personality_tags(fund_name, semi_report, report_name, short_term_personality_tags)
                        q2_processed = True
                
                if not q2_processed and 'Q2' in year_reports:
                    report = year_reports['Q2']
                    report_name = os.path.basename(report.get('file', '')).replace('.pdf', '')
                    self._process_report_for_personality_tags(fund_name, report, report_name, short_term_personality_tags)

                # Q3: 使用三季报
                if 'Q3' in year_reports:
                    report = year_reports['Q3']
                    report_name = os.path.basename(report.get('file', '')).replace('.pdf', '')
                    self._process_report_for_personality_tags(fund_name, report, report_name, short_term_personality_tags)

                # Q4: 优先使用年报，如果质量低则使用四季报
                q4_processed = False
                if 'annual' in year_reports:
                    annual_report = year_reports['annual']
                    annual_score = annual_report.get('score', 0)
                    if annual_score > 500:
                        report_name = os.path.basename(annual_report.get('file', '')).replace('.pdf', '')
                        self._process_report_for_personality_tags(fund_name, annual_report, report_name, short_term_personality_tags)
                        q4_processed = True
                
                if not q4_processed and 'Q4' in year_reports:
                    report = year_reports['Q4']
                    report_name = os.path.basename(report.get('file', '')).replace('.pdf', '')
                    self._process_report_for_personality_tags(fund_name, report, report_name, short_term_personality_tags)
            
            # 聚合为长期个性特征标签
            long_term_personality_tags = self._aggregate_personality_tags(short_term_personality_tags)
            
            # 组合最终标签
            tags = {
                "基金名称": fund_name,
                "收益风险标签": risk_return_tags,
                "操作风格标签": long_term_operation_tags,
                "个性特征标签": long_term_personality_tags
            }
            
            # 生成画像
            profile = self.tag_generator.generate_profile(fund_name, tags)
            
            # 保存标签和画像
            self.tag_generator.save_tags(fund_name, tags, self.tags_dir)
            self.tag_generator.save_profile(fund_name, profile, self.profiles_dir)
            
            # 保存短期操作风格标签到单独文件
            self._save_short_term_operation_tags(fund_name, short_term_operation_tags)
            
            # 保存短期个性特征标签到单独文件
            self._save_short_term_personality_tags(fund_name, short_term_personality_tags)
            
            all_tags[fund_name] = {
                'tags': tags,
                'profile': profile,
                'short_term_operation_tags': short_term_operation_tags,
                'short_term_personality_tags': short_term_personality_tags
            }
        
        return all_tags
    
    def _process_report_for_operation_tags(self, fund_name: str, report: dict, report_name: str, tags_list: list):
        """
        处理单个报告，生成操作风格标签
        
        Args:
            fund_name: 基金名称
            report: 报告数据
            report_name: 报告名称
            tags_list: 标签列表（用于追加结果）
        """
        report_fund_data = {
            '基金名称': fund_name,
            '基金类型信息': report.get('fund_type_info', {}),
            '宏观观点': report['data']['宏观观点'],
            '业绩数据': report['data']['业绩数据'],
            '持仓数据': report['data']['持仓数据']
        }
        
        # 生成操作风格标签
        operation_tags = self.tag_generator.operation_style_tagger.generate(report_fund_data, report_name)
        operation_tags['报告期'] = report_name
        tags_list.append(operation_tags)
    
    def _process_report_for_personality_tags(self, fund_name: str, report: dict, report_name: str, tags_list: list):
        """
        处理单个报告，生成个性特征标签
        
        Args:
            fund_name: 基金名称
            report: 报告数据
            report_name: 报告名称
            tags_list: 标签列表（用于追加结果）
        """
        report_fund_data = {
            '基金名称': fund_name,
            '基金类型信息': report.get('fund_type_info', {}),
            '宏观观点': report['data']['宏观观点'],
            '业绩数据': report['data']['业绩数据'],
            '持仓数据': report['data']['持仓数据']
        }
        
        # 生成个性特征标签
        personality_tags = self.tag_generator.personality_tagger.generate(report_fund_data)
        personality_tags['报告期'] = report_name
        tags_list.append(personality_tags)
    
    def _aggregate_operation_style_tags(self, tags_list: list) -> dict:
        """
        聚合操作风格标签（短期→长期）
        
        Args:
            tags_list: 操作风格标签列表
            
        Returns:
            聚合后的操作风格标签
        """
        if not tags_list:
            return {}
        
        from collections import Counter
        
        aggregated = {}
        # 修复：使用 OperationStyleTagger.generate() 实际返回的字段
        keys = ['投资风格', '长期风格', '短期风格', '风格稳定性', '风格演变趋势', '风格一致性', '风格波动率']
        
        for key in keys:
            values = [tags.get(key) for tags in tags_list if tags.get(key)]
            if values:
                # 取出现频率最高的值
                counter = Counter(values)
                aggregated[key] = counter.most_common(1)[0][0]
        
        # 分析期数取最大值
        period_counts = [tags.get('分析期数', 0) for tags in tags_list if tags.get('分析期数')]
        if period_counts:
            aggregated['分析期数'] = max(period_counts)
        
        return aggregated
    
    def _aggregate_personality_tags(self, tags_list: list) -> dict:
        """
        聚合个性特征标签（短期→长期）
        
        Args:
            tags_list: 个性特征标签列表
            
        Returns:
            聚合后的个性特征标签
        """
        if not tags_list:
            return {}
        
        from collections import Counter
        
        aggregated = {}
        # 个性特征标签的字段
        keys = ['信用下沉', '权益风格', '回撤控制', '利率波段']
        
        for key in keys:
            values = [tags.get(key) for tags in tags_list if tags.get(key)]
            if values:
                # 取出现频率最高的值
                counter = Counter(values)
                aggregated[key] = counter.most_common(1)[0][0]
        
        return aggregated
    
    def _save_short_term_operation_tags(self, fund_name: str, tags_list: list):
        """
        保存短期操作风格标签到单独文件
        
        Args:
            fund_name: 基金名称
            tags_list: 各期操作风格标签列表
        """
        import json
        
        # 创建短期标签目录
        short_term_dir = os.path.join(self.output_dir, "short_term_operation_tags")
        os.makedirs(short_term_dir, exist_ok=True)
        
        # 保存为JSON文件
        output_file = os.path.join(short_term_dir, f"{fund_name}_各期操作风格.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "基金名称": fund_name,
                "分析期数": len(tags_list),
                "各期操作风格标签": tags_list
            }, f, ensure_ascii=False, indent=2)
        
        print(f"  - 短期操作风格标签已保存: {output_file}")
    
    def _save_short_term_personality_tags(self, fund_name: str, tags_list: list):
        """
        保存短期个性特征标签到单独文件
        
        Args:
            fund_name: 基金名称
            tags_list: 各期个性特征标签列表
        """
        import json
        
        # 创建短期标签目录
        short_term_dir = os.path.join(self.output_dir, "short_term_personality_tags")
        os.makedirs(short_term_dir, exist_ok=True)
        
        # 保存为JSON文件
        output_file = os.path.join(short_term_dir, f"{fund_name}_各期个性特征.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "基金名称": fund_name,
                "分析期数": len(tags_list),
                "各期个性特征标签": tags_list
            }, f, ensure_ascii=False, indent=2)
        
        print(f"  - 短期个性特征标签已保存: {output_file}")
    
    def _generate_summary_report(self, results: list, all_tags: dict):
        """
        生成汇总报告
        
        Args:
            results: 所有报告的处理结果
            all_tags: 所有基金标签
        """
        import json
        
        summary_file = os.path.join(self.output_dir, "基金分析汇总报告.md")
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("# 基金经理风格画像分析汇总报告\n\n")
            f.write(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"分析基金数量: {len(all_tags)}\n\n")
            f.write("---\n\n")
            
            f.write("## 目录\n\n")
            f.write("1. [数据提取汇总](#数据提取汇总)\n")
            f.write("2. [基金经理画像](#基金经理画像)\n")
            f.write("3. [标签体系汇总](#标签体系汇总)\n\n")
            
            f.write("---\n\n")
            
            # 数据提取汇总
            f.write("## 数据提取汇总\n\n")
            f.write("| 基金名称 | 报告数量 | 波动水平 | 过去一年收益率 | 基金规模(亿元) |\n")
            f.write("|---------|---------|---------|--------------|---------------|\n")
            
            # 统计每个基金的报告数量
            fund_report_count = {}
            for result in results:
                if result.get('success'):
                    fund_name = result.get('fund_name', 'Unknown')
                    fund_report_count[fund_name] = fund_report_count.get(fund_name, 0) + 1
            
            for fund_name, tag_data in all_tags.items():
                # 从标签数据中获取业绩信息
                tags = tag_data['tags']
                risk_return = tags.get('收益风险标签', {})
                
                f.write(f"| {fund_name} ")
                f.write(f"| {fund_report_count.get(fund_name, 0)} ")
                f.write(f"| {risk_return.get('波动水平', 'N/A')} ")
                f.write(f"| {risk_return.get('过去一年收益率', 'N/A')} ")
                f.write(f"| {risk_return.get('基金规模(亿元)', 'N/A')} |\n")
            
            f.write("\n---\n\n")
            
            # 基金经理画像
            f.write("## 基金经理画像\n\n")
            
            for fund_name, tag_data in all_tags.items():
                f.write(f"### {fund_name}\n\n")
                f.write(tag_data['profile'])
                f.write("\n\n")
            
            f.write("---\n\n")
            
            # 标签体系汇总
            f.write("## 标签体系汇总\n\n")
            
            for fund_name, tag_data in all_tags.items():
                f.write(f"### {fund_name}\n\n")
                
                tags = tag_data['tags']
                for category, values in tags.items():
                    if category == '基金名称':
                        continue
                    
                    f.write(f"**{category}:**\n\n")
                    
                    if isinstance(values, dict):
                        for key, value in values.items():
                            f.write(f"- {key}: {value}\n")
                    else:
                        f.write(f"- {values}\n")
                    
                    f.write("\n")
                
                f.write("---\n\n")
        
        print(f"汇总报告已保存: {summary_file}")


def main():
    """主函数"""
    # 配置路径
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reports_dir = os.path.join(project_root, 'data', 'fund_reports')
    output_dir = os.path.join(project_root, 'output', 'fund_analysis')
    
    # 创建分析流程
    pipeline = FundAnalysisPipeline(reports_dir, output_dir)
    
    # 运行分析
    pipeline.run()


if __name__ == '__main__':
    main()
