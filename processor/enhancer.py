"""
内容增强模块
- 抓取文章正文
- 提取 Key Message
- 追溯原始链接
- 翻译英文内容
"""
import re
import os
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()


@dataclass
class EnhancedContent:
    """增强后的内容"""
    title: str
    key_messages: List[str]  # 关键信息点
    original_url: str  # 原始官方链接
    source_url: str  # 抓取来源链接
    source: str
    summary: str  # 摘要


class ContentEnhancer:
    """内容增强器"""
    
    # 官方网站映射（用于追溯原文）
    OFFICIAL_SOURCES = {
        # 自动驾驶公司
        'tesla': 'https://www.tesla.com/press',
        'waymo': 'https://waymo.com/blog/',
        'cruise': 'https://www.getcruise.com/news/',
        'zoox': 'https://zoox.com/press-room',
        'pony.ai': 'https://pony.ai/press',
        'weride': 'https://ir.weride.ai/news-events/news-releases',
        'nuro': 'https://nuro.ai/news/',
        'argo': 'https://www.argo.ai/blog/',
        'motional': 'https://motional.com/news/',
        'aurora': 'https://aurora.com/blog',
        # AI公司
        'openai': 'https://openai.com/blog/',
        'anthropic': 'https://www.anthropic.com/news',
        'google': 'https://blog.google/',
        'deepmind': 'https://deepmind.google/',
        'meta': 'https://about.meta.com/newsroom/',
        'microsoft': 'https://blogs.microsoft.com/',
        'nvidia': 'https://nvidianews.nvidia.com/',
        # 中国科技公司
        'baidu': 'https://www.baidu.com/',
        'alibaba': 'https://www.alibabagroup.com/newsroom',
        'tencent': 'https://www.tencent.com/zh-cn/articles',
        'bytedance': 'https://www.bytedance.com/en/newsroom',
        'huawei': 'https://www.huawei.com/cn/news',
        'xiaomi': 'https://www.mi.com/global/about/new',
    }
    
    def __init__(self, api_key: str = None, api_base: str = None, model: str = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # 翻译API配置
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.api_base = api_base or "https://api.openai.com/v1"
        self.model = model or "gpt-4"
        self.translation_enabled = bool(self.api_key)
    
    def enhance(self, item, fetch_content: bool = True) -> EnhancedContent:
        """
        增强单条新闻内容
        
        Args:
            item: NewsItem 对象
            fetch_content: 是否抓取正文内容
        """
        title = item.title
        source_url = item.source_url
        source = item.source
        
        # 抓取正文内容
        article_content = ""
        if fetch_content:
            article_content = self._fetch_article_content(source_url)
        
        # 提取 Key Messages（保留原文，不翻译）
        key_messages = self._extract_key_messages(title, article_content)
        
        # 追溯原始官方链接
        original_url = self._find_original_url(title, source_url, article_content)
        
        # 生成摘要
        summary = self._generate_summary(key_messages)
        
        return EnhancedContent(
            title=title,
            key_messages=key_messages,
            original_url=original_url,
            source_url=source_url,
            source=source,
            summary=summary
        )
    
    def _fetch_article_content(self, url: str) -> str:
        """抓取文章正文内容"""
        try:
            response = self.session.get(url, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 尝试多种正文选择器
            content_selectors = [
                'article',
                '.article-content',
                '.post-content',
                '.entry-content',
                '.content-body',
                '#article-content',
                '.article-body',
                '.news-content',
                '.rich_media_content',  # 微信公众号
                'main article',
                '.post-article',
                '.article-text',
                '.story-body',
                '[data-component="text-block"]',  # BBC style
                '.prose',  # Common blog style
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # 清理脚本和样式
                    for tag in content_elem.find_all(['script', 'style', 'iframe', 'nav', 'aside', 'header', 'footer']):
                        tag.decompose()
                    
                    # 获取所有段落文本
                    paragraphs = content_elem.find_all('p')
                    if paragraphs:
                        texts = []
                        for p in paragraphs:
                            text = p.get_text(strip=True)
                            # 过滤太短的段落（可能是广告或导航）
                            if len(text) > 30:
                                texts.append(text)
                        return '\n\n'.join(texts[:15])[:5000]  # 保留更多内容
                    
                    # 如果没有段落标签，获取全部文本
                    return content_elem.get_text(strip=True, separator='\n')[:5000]
            
            # 如果没有找到，尝试获取所有段落
            paragraphs = soup.find_all('p')
            if paragraphs:
                texts = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if len(text) > 30:
                        texts.append(text)
                return '\n\n'.join(texts[:15])[:5000]
            
            return ""
            
        except Exception as e:
            console.print(f"[yellow]抓取正文失败: {url[:50]}... - {e}[/yellow]")
            return ""
    
    def _extract_key_messages(self, title: str, content: str) -> List[str]:
        """
        提取关键信息点
        从文章中提取完整段落作为关键信息
        重要：返回中文内容，英文需要翻译
        """
        key_messages = []
        
        # 规则1：如果有抓取到正文内容，提取重要段落
        if content and len(content) > 100:
            # 按段落分割
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            
            # 关键词权重（用于判断段落重要性）
            important_keywords = [
                # AI 相关
                'ai', 'artificial intelligence', 'chatgpt', 'gpt', 'llm', 'agi', 'openai', 'anthropic', 
                '人工智能', '大模型', '机器学习', '深度学习',
                # 自动驾驶相关
                'autonomous', 'self-driving', 'driverless', 'robotaxi', 'waymo', 'tesla', 'cruise', 'fsd',
                '自动驾驶', '无人驾驶', '智能驾驶',
                # 动作词
                'announced', 'launched', 'released', 'raised', 'acquired', 'partnered',
                '发布', '推出', '宣布', '融资', '收购', '合作',
                # 数字相关
                '$', 'million', 'billion', '%', '亿', '万',
            ]
            
            scored_paragraphs = []
            for para in paragraphs:
                para_lower = para.lower()
                score = 0
                
                # 计算段落重要性得分
                for kw in important_keywords:
                    if kw in para_lower:
                        score += 1
                
                # 长度适中（太短可能不是正文，太长可能包含废话）
                if 50 < len(para) < 500:
                    score += 1
                
                if score > 0:
                    scored_paragraphs.append((para, score))
            
            # 按得分排序，取前3个段落
            scored_paragraphs.sort(key=lambda x: x[1], reverse=True)
            
            for para, score in scored_paragraphs[:3]:
                # 直接使用原文，不翻译
                if para and para not in key_messages:
                    key_messages.append(para)
        
        # 规则2：如果没有提取到段落，从标题生成
        if not key_messages and title:
            key_messages = [title]
        
        # 规则3：如果内容太少，补充标题
        if len(key_messages) < 2 and title:
            if title not in key_messages:
                key_messages.insert(0, title)
        
        return key_messages[:3]  # 最多3个关键信息点
    
    def _translate_to_chinese(self, text: str) -> str:
        """
        将英文翻译成中文
        使用术语替换 + 句子模式匹配
        后续可接入翻译API获得更好的效果
        """
        if not text:
            return text
        
        result = text
        
        # 常见术语翻译映射（按优先级排序）
        translations = {
            # 公司名
            'Waymo': 'Waymo',
            'Tesla': '特斯拉',
            'OpenAI': 'OpenAI',
            'Anthropic': 'Anthropic',
            'Google': '谷歌',
            'Meta': 'Meta',
            'Microsoft': '微软',
            'Apple': '苹果',
            'Amazon': '亚马逊',
            'NVIDIA': '英伟达',
            'Nvidia': '英伟达',
            'Uber': 'Uber',
            'Zoox': 'Zoox',
            'Cruise': 'Cruise',
            'Pony.ai': '小马智行',
            'WeRide': '文远知行',
            'Nuro': 'Nuro',
            'Aurora': 'Aurora',
            'Motional': 'Motional',
            'xAI': 'xAI',
            'xAI\'s': 'xAI的',
            'Sam Altman': 'Sam Altman',
            'Elon Musk': '埃隆·马斯克',
            'Musk': '马斯克',
            'Barry Diller': 'Barry Diller',
            'Mark Zuckerberg': '扎克伯格',
            
            # 技术术语
            'autonomous vehicle': '自动驾驶汽车',
            'autonomous vehicles': '自动驾驶汽车',
            'autonomous driving': '自动驾驶',
            'self-driving': '自动驾驶',
            'self-driving car': '自动驾驶汽车',
            'driverless': '无人驾驶',
            'driverless car': '无人驾驶汽车',
            'robotaxi': '无人驾驶出租车',
            'robotaxis': '无人驾驶出租车',
            'AI': 'AI',
            'A.I.': 'AI',
            'artificial intelligence': '人工智能',
            'machine learning': '机器学习',
            'deep learning': '深度学习',
            'neural network': '神经网络',
            'neural networks': '神经网络',
            'LLM': '大语言模型',
            'large language model': '大语言模型',
            'large language models': '大语言模型',
            'AGI': '通用人工智能',
            'artificial general intelligence': '通用人工智能',
            'FSD': '全自动驾驶',
            'Full Self-Driving': '全自动驾驶',
            'L4': 'L4级',
            'L3': 'L3级',
            'L2': 'L2级',
            'lidar': '激光雷达',
            'LiDAR': '激光雷达',
            'lidars': '激光雷达',
            'data center': '数据中心',
            'data centers': '数据中心',
            'neocloud': '新型云服务',
            'compute': '算力',
            'startup': '初创公司',
            'startups': '初创公司',
            'venture fund': '风险基金',
            'expert network': '专家网络',
            
            # 常见词组
            'said': '表示',
            'announced': '宣布',
            'launched': '推出',
            'released': '发布',
            'invested': '投资',
            'acquired': '收购',
            'partnered': '合作',
            'raised': '融资',
            'according to': '根据',
            'reported': '报道',
            'told': '告诉',
            'confirmed': '确认',
            'will': '将',
            'has': '已经',
            'have': '已经',
            'new': '新',
            'first': '首次',
            
            # 单位和数字
            'million': '百万',
            'billion': '十亿',
            'trillion': '万亿',
            'dollars': '美元',
            'percent': '百分之',
            'per cent': '百分之',
        }
        
        # 按长度降序排序，先替换长的词组
        sorted_translations = sorted(translations.items(), key=lambda x: len(x[0]), reverse=True)
        
        for en, zh in sorted_translations:
            # 使用正则匹配单词边界，忽略大小写
            pattern = r'\b' + re.escape(en) + r'\b'
            result = re.sub(pattern, zh, result, flags=re.IGNORECASE)
        
        # 句子模式翻译
        sentence_patterns = [
            (r'(\w+) announced that', r'\1宣布'),
            (r'(\w+) has (announced|launched|released)', r'\1已经\2'),
            (r'according to (\w+)', r'根据\1'),
            (r'raised \$([\d.]+) (million|billion)', r'融资\1\2美元'),
            (r'\$([\d.]+) (million|billion)', r'\1\2美元'),
            (r'(\d+) percent', r'\1%'),
            (r'the company', r'该公司'),
            (r'The company', r'该公司'),
            (r'this year', r'今年'),
            (r'last year', r'去年'),
            (r'next year', r'明年'),
        ]
        
        for pattern, replacement in sentence_patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result
    
    def _find_original_url(self, title: str, source_url: str, content: str) -> str:
        """
        追溯原始官方链接
        从标题和内容中识别公司名，返回官方新闻页面
        """
        text = f"{title} {content}".lower()
        
        # 如果来源已经是官方网站，直接返回
        for company, url in self.OFFICIAL_SOURCES.items():
            if company in source_url.lower():
                return source_url
        
        # 检查标题中明确提到的公司（优先级更高）
        title_lower = title.lower()
        
        # 按优先级匹配（标题 > 内容）
        company_matches = []
        for company, url in self.OFFICIAL_SOURCES.items():
            company_clean = company.replace('.', '')  # pony.ai -> ponyai
            
            # 标题中匹配，权重更高
            if company in title_lower or company_clean in title_lower.replace('.', '').replace(' ', ''):
                company_matches.append((company, url, 2))  # 权重2
            # 内容中匹配
            elif company in text or company_clean in text.replace('.', '').replace(' ', ''):
                company_matches.append((company, url, 1))  # 权重1
        
        # 如果只有一个公司匹配，直接返回
        if len(company_matches) == 1:
            return company_matches[0][1]
        
        # 如果有多个匹配，按权重排序返回最高的
        if company_matches:
            company_matches.sort(key=lambda x: x[2], reverse=True)
            return company_matches[0][1]
        
        # 检查内容中是否有原始链接
        if content:
            # 查找内容中的链接
            link_patterns = [
                r'https?://[^\s<>"]+?(?:tesla|waymo|openai|anthropic|google|meta|nvidia|pony|weride|cruise)[^\s<>"]*',
                r'原文链接[：:]\s*(https?://[^\s<>"]+)',
                r'来源[：:]\s*(https?://[^\s<>"]+)',
            ]
            
            for pattern in link_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    return matches[0]
        
        # 没有找到原始链接，返回当前来源
        return source_url
    
    def _generate_summary(self, key_messages: List[str]) -> str:
        """生成简短摘要"""
        if not key_messages:
            return ""
        
        if len(key_messages) == 1:
            return key_messages[0]
        
        return " | ".join(key_messages[:3])
    
    def translate_text(self, text: str) -> str:
        """
        使用AI翻译英文到中文
        如果API不可用，则使用词典翻译
        """
        if not text:
            return text
        
        # 检查是否包含中文，如果大部分是中文则不翻译
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        if chinese_chars > len(text) * 0.3:
            return text
        
        # 尝试使用AI翻译
        if self.translation_enabled:
            try:
                import openai
                client = openai.OpenAI(api_key=self.api_key, base_url=self.api_base)
                
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "你是一个专业的科技新闻翻译助手。请将以下英文内容翻译成流畅的中文，保持专业术语的准确性。只输出翻译结果，不要添加任何解释。"},
                        {"role": "user", "content": text}
                    ],
                    max_tokens=2000,
                    temperature=0.3
                )
                
                return response.choices[0].message.content.strip()
            except Exception as e:
                console.print(f"[yellow]AI翻译失败，使用词典翻译: {str(e)[:50]}[/yellow]")
        
        # 词典翻译作为后备
        return self._translate_to_chinese(text)
    
    def batch_enhance(self, items: list, show_progress: bool = True) -> List[EnhancedContent]:
        """批量增强内容"""
        results = []
        
        for i, item in enumerate(items):
            if show_progress:
                # 过滤特殊字符，避免 Windows GBK 编码问题
                safe_title = item.title[:30].encode('gbk', errors='replace').decode('gbk')
                console.print(f"[cyan]处理 {i+1}/{len(items)}: {safe_title}...[/cyan]")
            
            try:
                enhanced = self.enhance(item)
                results.append(enhanced)
            except Exception as e:
                console.print(f"[red]处理失败: {e}[/red]")
                # 保留原始信息
                results.append(EnhancedContent(
                    title=item.title,
                    key_messages=[item.title],
                    original_url=item.source_url,
                    source_url=item.source_url,
                    source=item.source,
                    summary=item.title
                ))
        
        return results