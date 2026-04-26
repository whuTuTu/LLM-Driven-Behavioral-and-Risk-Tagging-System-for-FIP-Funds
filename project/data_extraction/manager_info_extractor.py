"""
基金经理履历信息提取器（改进版）
正确提取表格数据，支持多种报告格式
"""

import re
from typing import Dict, List
from .base_extractor import BaseExtractor


class ManagerInfoExtractor(BaseExtractor):
    """基金经理履历信息提取器"""
    
    def __init__(self):
        """初始化提取器"""
        super().__init__()
    
    def extract(self, text: str, report_type: str = 'Q1') -> Dict:
        """
        提取基金经理履历信息
        
        Args:
            text: 报告文本
            report_type: 报告类型
            
        Returns:
            提取的基金经理履历数据
        """
        # 1. 提取基金经理简介章节
        manager_info_text = self._extract_manager_info_section(text, report_type)
        
        # 2. 解析基金经理信息
        manager_data = self._parse_manager_info(manager_info_text)
        
        return manager_data
    
    def _extract_manager_info_section(self, text: str, report_type: str) -> str:
        """
        提取基金经理简介章节
        
        Args:
            text: 报告全文
            report_type: 报告类型
            
        Returns:
            基金经理简介章节文本
        """
        # 提取§4 管理人报告章节
        # 使用finditer处理多个匹配（跳过目录页）
        section4_matches = list(re.finditer(r'§4\s*管理人报告[^\n]*\s*(.*?)(?=§5|$)', text, re.DOTALL))
        
        if not section4_matches:
            return ""
        
        # 选择内容最长的匹配（跳过目录页）
        section4_text = max([m.group(1) for m in section4_matches], key=len)
        
        # 基金经理简介章节匹配模式
        # 模式1：季度报告格式 4.1 基金经理（或基金经理简介）
        quarterly_pattern = r'4\.1\s*基金经理[^\n]*\s*(.*?)(?=4\.2\s|4\.3\s|4\.4\s|$)'
        # 模式2：年度报告格式 4.1.2 基金经理（注意：年度报告是4.1.2，不是4.1.1）
        annual_pattern = r'4\.1\.2\s*基金经理[^\n]*\s*(.*?)(?=4\.1\.3\s|4\.2\s|$)'
        
        manager_match = None
        
        if report_type in ['Q1', 'Q2', 'Q3', 'Q4']:
            # 先尝试季度报告模式
            manager_match = re.search(quarterly_pattern, section4_text, re.DOTALL)
            # 如果失败，尝试年度报告模式
            if not manager_match:
                manager_match = re.search(annual_pattern, section4_text, re.DOTALL)
        elif report_type in ['Semi-Annual', 'Annual']:
            # 先尝试年度报告模式
            manager_match = re.search(annual_pattern, section4_text, re.DOTALL)
            # 如果失败，尝试季度报告模式
            if not manager_match:
                manager_match = re.search(quarterly_pattern, section4_text, re.DOTALL)
        
        if manager_match:
            return manager_match.group(1).strip()
        
        return ""
    
    def _parse_manager_info(self, text: str) -> Dict:
        """
        解析基金经理信息（改进版，正确处理表格）
        
        Args:
            text: 基金经理简介文本
            
        Returns:
            解析后的基金经理信息
        """
        result = {
            "基金经理列表": [],
            "原始文本": text[:2000] if text else ""
        }
        
        if not text:
            return result
        
        # 方法1：通过"本基金的基金经理"关键词定位
        managers = self._extract_managers_by_keyword(text)
        if managers:
            result["基金经理列表"] = managers
        else:
            # 方法2：按行分割，查找包含姓名的行
            lines = text.split('\n')
            
            for i, line in enumerate(lines):
                # 查找包含姓名特征的行
                # 姓名通常是2-4个汉字
                name_match = re.search(r'^([^\s]{2,4})\s+', line)
                
                if name_match:
                    potential_name = name_match.group(1)
                    
                    # 验证是否是姓名（不包含特殊字符，且不是表头）
                    chinese_pattern = r'^[\u4e00-\u9fa5]+$'
                    if re.match(chinese_pattern, potential_name) and potential_name not in ['姓名', '职务', '任职', '离任']:
                        # 尝试提取该基金经理的完整信息
                        manager = self._extract_manager_from_lines(lines, i)
                        if manager and manager.get("姓名"):
                            result["基金经理列表"].append(manager)
        
        # 添加兼容字段（取第一个基金经理的信息）
        if result["基金经理列表"]:
            first_manager = result["基金经理列表"][0]
            result["姓名"] = first_manager.get("姓名", "")
            result["任职日期"] = first_manager.get("任职日期", "")
            result["证券从业年限"] = first_manager.get("证券从业年限", "")
            result["学历"] = first_manager.get("学历", "")
            result["履历"] = first_manager.get("履历", "")
        
        return result
    
    def _extract_managers_by_keyword(self, text: str) -> List[Dict]:
        """
        通过"本基金的基金经理"关键词提取所有基金经理信息
        
        Args:
            text: 基金经理简介文本
            
        Returns:
            基金经理信息列表
        """
        managers = []
        
        # 先清理文本
        # 1. 将换行符替换为空格
        clean_text = re.sub(r'\n+', ' ', text)
        # 2. 合并被分割的关键词：
        #    "本基金 的基金 经理" -> "本基金的基金经理"
        #    "本基金的 基金经理" -> "本基金的基金经理"
        clean_text = re.sub(r'本基金\s*的基金\s*经理', '本基金的基金经理', clean_text)
        clean_text = re.sub(r'本基金的\s*基金经理', '本基金的基金经理', clean_text)
        # 3. 合并被分割的姓名（如"牛伟 松" -> "牛伟松"）
        #    查找"姓名 本基金的基金经理"模式，合并姓名中的空格
        clean_text = re.sub(r'([^\s]{2,3})\s+([^\s]{1,2})\s*本基金的基金经理', r'\1\2本基金的基金经理', clean_text)
        # 4. 替换多个空格为单个空格
        clean_text = re.sub(r' {2,}', ' ', clean_text)
        
        # 查找所有"本基金的基金经理"出现的位置
        # 格式通常是：姓名 本基金的基金经理 任职日期 - 从业年限 学历。履历
        pattern = r'([^\s]{2,4})\s*本基金的基金经理'
        
        valid_matches = []
        for match in re.finditer(pattern, clean_text):
            start_pos = match.start()
            name = match.group(1)
            
            # 验证是否是姓名
            chinese_pattern = r'^[\u4e00-\u9fa5]+$'
            if not re.match(chinese_pattern, name):
                continue
            
            # 过滤掉表头中的错误匹配（如"职务任"）
            # 真正的基金经理信息格式：姓名 本基金的基金经理 日期 - 从业年限 学历
            # 表头格式：职务任本基金的基金经理 （助理）期限...
            # 检查姓名后面是否紧跟"本基金的基金经理 日期"格式
            end_pos_check = min(start_pos + 50, len(clean_text))
            check_segment = clean_text[start_pos:end_pos_check]
            # 必须包含"本基金的基金经理"后面紧跟日期（YYYY年或YYYY-）
            if not re.search(r'本基金的基金经理\s*\d{4}', check_segment):
                continue
            
            valid_matches.append((start_pos, name))
        
        # 只取第一个有效匹配（避免重复匹配）
        if not valid_matches:
            return managers
        
        start_pos, name = valid_matches[0]
        
        # 从该位置向后提取信息（取后面1500字符，确保包含完整简介）
        end_pos = min(start_pos + 1500, len(clean_text))
        segment = clean_text[start_pos:end_pos]
        
        manager = {
            "姓名": name,
            "职务": "基金经理",
            "任职日期": "",
            "离任日期": "",
            "证券从业年限": "",
            "学历": "",
            "履历": ""
        }
        
        # 提取任职日期（格式：YYYY年MM月DD日 或 YYYY-MM-DD）
        # 注意：日期可能被换行分割，如"2022年10月 10日"
        # 注意：也可能是"2016 -11-18"这种格式
        date_match = re.search(r'(\d{4})\s*[-年]\s*(\d{1,2})\s*[-月]\s*(\d{1,2})\s*日?', segment)
        if date_match:
            year = date_match.group(1)
            month = date_match.group(2)
            day = date_match.group(3)
            manager["任职日期"] = f"{year}年{month}月{day}日"
        else:
            # 备选方案：查找"YYYY -MM-DD"格式
            date_match2 = re.search(r'(\d{4})\s*-\s*(\d{1,2})\s*-\s*(\d{1,2})', segment)
            if date_match2:
                year = date_match2.group(1)
                month = date_match2.group(2)
                day = date_match2.group(3)
                manager["任职日期"] = f"{year}年{month}月{day}日"
        
        # 提取从业年限（格式：X年，通常在学历之前）
        # 注意：可能是"10年 中央财经大学硕士"这样的格式
        # 注意：要排除日期中的年份，通常从业年限是1-50之间的数字
        exp_match = re.search(r'(\d{1,2})\s*年\s*(?:硕士|博士|本科|研究生|中央|清华|北大|复旦|上海)', segment)
        if exp_match:
            manager["证券从业年限"] = exp_match.group(1) + "年"
        else:
            # 备选方案：查找" - X年"格式（表格中常见）
            exp_match2 = re.search(r'-\s*(\d{1,2})\s*年', segment)
            if exp_match2:
                manager["证券从业年限"] = exp_match2.group(1) + "年"
        
        # 提取学历
        edu_match = re.search(r'(博士|硕士|本科|研究生)', segment)
        if edu_match:
            manager["学历"] = edu_match.group(1)
        
        # 提取履历/简介
        # 格式通常是：学历。加入公司。历任...。现任...
        # 查找从学历开始到"等。"或"注："之前的内容
        intro_match = re.search(r'((?:硕士|博士|本科|研究生)[^。]*。\s*.*?)(?=注：|等。)', segment, re.DOTALL)
        if intro_match:
            intro_text = intro_match.group(1).strip()
            # 清理换行和多余空格
            intro_text = re.sub(r'\s+', ' ', intro_text)
            # 如果以"等。"结尾，加上"等。"
            if segment.find('等。', intro_match.end()) != -1:
                intro_text += '等。'
            manager["履历"] = intro_text
        else:
            # 备选方案：只提取"历任"开头的句子
            exp_text_match = re.search(r'(历任[^。]+。)', segment)
            if exp_text_match:
                manager["履历"] = exp_text_match.group(1)
        
        managers.append(manager)
        
        return managers
    
    def _extract_manager_from_lines(self, lines: List[str], start_idx: int) -> Dict:
        """
        从行列表中提取基金经理信息
        
        Args:
            lines: 文本行列表
            start_idx: 起始行索引
            
        Returns:
            基金经理信息
        """
        manager = {
            "姓名": "",
            "职务": "",
            "任职日期": "",
            "离任日期": "",
            "证券从业年限": "",
            "学历": "",
            "履历": ""
        }
        
        # 合并连续的几行
        combined_text = ""
        for i in range(start_idx, min(start_idx + 10, len(lines))):
            combined_text += lines[i] + " "
        
        # 提取姓名
        name_match = re.search(r'^([^\s]{2,4})\s+', combined_text)
        if name_match:
            manager["姓名"] = name_match.group(1)
        
        # 提取任职日期
        date_match = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日)', combined_text)
        if date_match:
            manager["任职日期"] = date_match.group(1)
        
        # 提取从业年限
        exp_match = re.search(r'(\d+)\s*年', combined_text)
        if exp_match:
            manager["证券从业年限"] = exp_match.group(1) + "年"
        
        # 提取学历
        edu_match = re.search(r'(博士|硕士|本科|研究生)', combined_text)
        if edu_match:
            manager["学历"] = edu_match.group(1)
        
        # 提取履历（查找"历任"或"曾任"）
        exp_text_match = re.search(r'(历任[^。]+。|曾任[^。]+。)', combined_text)
        if exp_text_match:
            manager["履历"] = exp_text_match.group(1)
        
        return manager if manager["姓名"] else {}
