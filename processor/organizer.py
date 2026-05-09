"""
日报内容整理和格式化模块
"""
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass
import jieba
import jieba.analyse
from core import NewsItem, console
from processor.enhancer import ContentEnhancer, EnhancedContent


@dataclass
class DailyReport:
    """日报数据结构"""
    date: str
    title: str
    categories: Dict[str, List[EnhancedContent]]
    summary: str
    total_count: int
    
    def to_markdown(self) -> str:
        """转换为 Markdown 格式（知识库风格 - 参照原日报格式）"""
        md = f"# 【日报】{self.date}\n\n"
        
        # 按分类输出
        category_names = {
            'policy': '政策动向',
            'company': '行业动态趋势',
            'news': '行业资讯',
            'wechat': '微信精选',
            'research': '研究观点摘录'
        }
        
        for category, items in self.categories.items():
            if not items:
                continue
            
            cat_name = category_names.get(category, category)
            md += f"# **{cat_name}**\n\n"
            
            # 中文数字编号
            cn_numbers = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
                         '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十']
            
            for i, item in enumerate(items):
                cn_num = cn_numbers[i] if i < len(cn_numbers) else str(i + 1)
                
                # 研究观点摘录用不同格式
                if category == 'research':
                    md += f"## {cn_num}.{item.title}\n\n"
                    
                    # 正文内容
                    if item.key_messages:
                        for msg in item.key_messages:
                            md += f"{msg}\n\n"
                    
                    # 链接
                    md += f"链接：[{item.source_url}]({item.source_url})\n\n"
                else:
                    # 标题（加粗）
                    md += f"## **{cn_num}、{item.title}**\n\n"
                    
                    # 正文内容（直接写原文，不要标签）
                    if item.key_messages:
                        for msg in item.key_messages:
                            md += f"{msg}\n\n"
                    
                    # 链接
                    if item.original_url and item.original_url != item.source_url:
                        md += f"链接：[{item.original_url}]({item.original_url})\n\n"
                        md += f"[{item.source_url}]({item.source_url})\n\n"
                    else:
                        md += f"链接：[{item.source_url}]({item.source_url})\n\n"
        
        return md


class ContentOrganizer:
    """内容整理器"""
    
    def __init__(self, api_key: str = None, api_base: str = None, model: str = None):
        # 初始化jieba分词
        jieba.initialize()
        # 初始化内容增强器（带AI翻译支持）
        self.enhancer = ContentEnhancer(api_key=api_key, api_base=api_base, model=model)
        self.translation_enabled = bool(api_key)
    
    def organize(self, items: List[NewsItem], date: datetime = None, enhance: bool = True) -> DailyReport:
        """
        整理新闻内容，生成日报
        
        Args:
            items: 新闻列表
            date: 日期
            enhance: 是否增强内容（提取Key Message、追溯原文）
        """
        if date is None:
            date = datetime.now()
        
        # 增强内容
        enhanced_items = []
        if enhance and items:
            console.print("[cyan]正在提取关键信息...[/cyan]")
            enhanced_items = self.enhancer.batch_enhance(items)
        
        # 按分类分组
        categories = self._group_by_category(enhanced_items, items)
        
        # 添加研究观点摘录
        research_insights = self._load_research_insights()
        if research_insights:
            categories['research'] = research_insights
        
        # 添加全球研报
        global_research = self.load_global_research()
        if global_research:
            if 'research' not in categories:
                categories['research'] = []
            categories['research'].extend(global_research)
        
        # 生成摘要
        summary = self._generate_summary(items)
        
        # 创建日报
        report = DailyReport(
            date=date.strftime("%Y-%m-%d"),
            title=f"【日报】{date.strftime('%Y年%m月%d日')} 政策与行业动态",
            categories=categories,
            summary=summary,
            total_count=len(enhanced_items)
        )
        
        return report
    
    def _load_research_insights(self) -> List:
        """从文件加载研究观点"""
        import json
        from pathlib import Path
        
        insights_file = Path('data/research_insights.json')
        if not insights_file.exists():
            return []
        
        try:
            with open(insights_file, 'r', encoding='utf-8') as f:
                insights = json.load(f)
            
            # 转换为 EnhancedContent 格式
            from processor.enhancer import EnhancedContent
            result = []
            for item in insights:
                result.append(EnhancedContent(
                    title=item.get('title', ''),
                    key_messages=item.get('insights', []),
                    original_url=item.get('source_url', ''),
                    source_url=item.get('source_url', ''),
                    source=item.get('source', ''),
                    summary=''
                ))
            return result
        except:
            return []
    
    def load_global_research(self) -> List:
        """从文件加载全球研报数据"""
        import json
        from pathlib import Path
        from processor.enhancer import EnhancedContent
        
        research_file = Path('data/global_research_reports.json')
        if not research_file.exists():
            return []
        
        try:
            with open(research_file, 'r', encoding='utf-8') as f:
                reports = json.load(f)
            
            result = []
            for item in reports:
                # 构建摘要作为key message
                summary = item.get('summary', '')
                country = item.get('country', '')
                language = item.get('language', '')
                keywords = item.get('keywords', [])
                
                key_messages = []
                if summary:
                    key_messages.append(summary)
                if country or language:
                    key_messages.append(f"来源：{item.get('source', '')}（{country}）| 语言：{language}")
                if keywords:
                    key_messages.append(f"关键词：{', '.join(keywords)}")
                
                result.append(EnhancedContent(
                    title=item.get('title', ''),
                    key_messages=key_messages,
                    original_url=item.get('url', ''),
                    source_url=item.get('url', ''),
                    source=item.get('source', ''),
                    summary=summary
                ))
            return result
        except Exception as e:
            console.print(f"[yellow]加载全球研报失败: {e}[/yellow]")
            return []
    
    def _group_by_category(self, enhanced_items: List[EnhancedContent], original_items: List[NewsItem]) -> Dict[str, List[EnhancedContent]]:
        """按分类分组"""
        categories = {}
        
        # 建立原始item的分类映射
        category_map = {}
        for item in original_items:
            # 使用标题作为key
            category_map[item.title] = item.category
        
        for item in enhanced_items:
            # 从原始item获取分类
            cat = category_map.get(item.title, 'news')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        return categories
    
    def _generate_summary(self, items: List[NewsItem]) -> str:
        """生成日报摘要"""
        if not items:
            return "今日暂无重要动态。"
        
        # 统计各分类数量
        category_counts = {}
        for item in items:
            cat = item.category
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # 提取关键词
        all_titles = " ".join([item.title for item in items])
        keywords = jieba.analyse.extract_tags(all_titles, topK=10)
        
        # 生成摘要文本
        summary_parts = [f"今日共收录 **{len(items)}** 条信息，"]
        
        category_names = {
            'policy': '政策动向',
            'company': '公司动态',
            'news': '行业资讯',
            'wechat': '微信精选'
        }
        
        count_parts = []
        for cat, count in category_counts.items():
            cat_name = category_names.get(cat, cat)
            count_parts.append(f"{cat_name} {count} 条")
        
        summary_parts.append("、".join(count_parts) + "。")
        
        if keywords:
            summary_parts.append(f"\n\n**热点关键词：** {'、'.join(keywords[:5])}")
        
        return "".join(summary_parts)
    
    def filter_by_keywords(self, items: List[NewsItem], keywords: List[str]) -> List[NewsItem]:
        """按关键词过滤（支持中英文，不区分大小写）"""
        if not keywords:
            return items
        
        # 预处理关键词：转小写
        keywords_lower = [kw.lower() for kw in keywords]
        
        filtered = []
        for item in items:
            # 合并标题和内容进行检测
            text = f"{item.title} {item.content or ''}".lower()
            
            # 检查是否包含任一关键词
            for kw in keywords_lower:
                if kw in text:
                    filtered.append(item)
                    break  # 匹配到一个关键词即可
        
        return filtered
    
    def filter_by_relevance(self, items: List[NewsItem], config: Dict) -> List[NewsItem]:
        """
        按相关性过滤（AI/自动驾驶相关）
        使用配置中的关键词列表
        """
        keywords = config.get('daily_report', {}).get('filter_keywords', [])
        
        if not keywords:
            # 默认关键词列表
            keywords = [
                # AI 相关
                "ai", "人工智能", "chatgpt", "gpt", "大模型", "机器学习", "深度学习",
                "openai", "anthropic", "claude", "gemini", "llm", "agi", "生成式", "aigc",
                # 自动驾驶相关
                "自动驾驶", "无人驾驶", "无人车", "robotaxi", "waymo", "cruise", "zoox",
                "pony", "weride", "文远知行", "小马智行", "特斯拉", "tesla", "fsd", "autopilot",
                "autonomous", "driverless", "self-driving", "l4", "l3", "智能驾驶", "智能网联",
                "车载", "车路协同", "激光雷达", "lidar", "智驾"
            ]
        
        return self.filter_by_keywords(items, keywords)
    
    def filter_by_date_range(self, items: List[NewsItem], start_date: str, end_date: str) -> List[NewsItem]:
        """
        按日期范围过滤
        尽可能保留指定日期范围内的新闻，无法确定日期的也保留（由用户判断）
        
        Args:
            items: 新闻列表
            start_date: 开始日期，格式 "2026-04-30"
            end_date: 结束日期，格式 "2026-05-06"
        """
        from datetime import datetime
        
        filtered = []
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        for item in items:
            item_date = None
            
            # 1. 尝试从 URL 中提取日期
            import re
            url = item.source_url
            
            url_date_patterns = [
                (r'/(\d{4})/(\d{2})/(\d{2})/', lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
                (r'/(\d{4})(\d{2})(\d{2})', lambda m: datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))),
            ]
            
            for pattern, extractor in url_date_patterns:
                match = re.search(pattern, url)
                if match:
                    try:
                        item_date = extractor(match)
                        break
                    except:
                        continue
            
            # 2. 如果URL没有，尝试从 publish_time 获取
            if not item_date and item.publish_time:
                try:
                    for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y年%m月%d日']:
                        try:
                            item_date = datetime.strptime(item.publish_time[:10], fmt)
                            break
                        except:
                            continue
                except:
                    pass
            
            # 3. 如果能确定日期，检查是否在范围内
            if item_date:
                if start <= item_date <= end:
                    filtered.append(item)
            else:
                # 无法确定日期的也保留，让用户自己判断
                filtered.append(item)
        
        return filtered
    
    def deduplicate(self, items: List[NewsItem]) -> List[NewsItem]:
        """去重"""
        seen = set()
        unique = []
        
        for item in items:
            # 使用标题作为去重依据
            key = item.title.strip().lower()
            if key not in seen:
                seen.add(key)
                unique.append(item)
        
        return unique


class AIEnhancer:
    """
    AI 增强器
    使用 AI 模型对内容进行摘要、翻译、分类等增强处理
    """
    
    def __init__(self, api_key: str = None, api_base: str = None, model: str = None):
        self.api_key = api_key
        self.api_base = api_base or "https://api.openai.com/v1"
        self.model = model or "gpt-3.5-turbo"
        self.enabled = bool(api_key)
    
    def enhance_summary(self, items: List[NewsItem]) -> str:
        """使用 AI 生成更智能的摘要"""
        if not self.enabled:
            console.print("[yellow]AI 增强未启用，使用基础摘要[/yellow]")
            return None
        
        try:
            import openai
            
            # 构建提示词
            titles = [f"- {item.title}" for item in items[:20]]
            prompt = f"""请根据以下今日新闻标题，生成一份简洁的日报摘要（100字以内）：

{chr(10).join(titles)}

摘要要求：
1. 提炼最重要的趋势和事件
2. 使用客观、专业的语言
3. 突出关键词和热点
"""
            
            client = openai.OpenAI(api_key=self.api_key, base_url=self.api_base)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的新闻编辑，擅长撰写简洁准确的新闻摘要。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            console.print(f"[red]AI 摘要生成失败: {e}[/red]")
            return None
    
    def categorize_item(self, item: NewsItem) -> str:
        """使用 AI 对新闻进行智能分类"""
        if not self.enabled:
            return item.category
        
        try:
            import openai
            
            categories = ["政策", "公司动态", "行业资讯", "技术", "财经"]
            prompt = f"""请判断以下新闻属于哪个分类？
分类选项：{', '.join(categories)}

新闻标题：{item.title}

只输出分类名称，不要其他内容。"""
            
            client = openai.OpenAI(api_key=self.api_key, base_url=self.api_base)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10,
                temperature=0
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            console.print(f"[yellow]AI 分类失败: {e}[/yellow]")
            return item.category