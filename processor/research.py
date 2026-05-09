"""
研究观点摘录模块
- 搜索研报和专家访谈
- 提取原文观点
- 支持PDF和网页内容提取
"""
import os
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class ResearchInsight:
    """研究观点数据结构"""
    title: str  # 标题
    source: str  # 来源（机构/专家名）
    source_type: str  # report / interview
    source_url: str  # 原文链接
    insights: List[str] = field(default_factory=list)  # 原文观点
    images: List[str] = field(default_factory=list)  # 图片链接
    date: str = ""  # 发布日期
    author: str = ""  # 作者/专家
    summary: str = ""  # 简短说明（用于候选列表）


class ResearchFinder:
    """研究内容发现器 - 生成候选列表供用户选择"""
    
    # 研报来源网站
    REPORT_SOURCES = {
        "麦肯锡": "https://www.mckinsey.com/industries/automotive-and-assembly/our-insights",
        "波士顿咨询": "https://www.bcg.com/industries/automotive",
        "贝恩资本": "https://www.bain.com/insights/",
        "德勤": "https://www2.deloitte.com/cn/zh/pages/technology-media-telecommunications/articles/",
        "普华永道": "https://www.pwc.com/us/en/tech-effect/automotive.html",
        "埃森哲": "https://www.accenture.com/us-en/industries/automotive-index",
    }
    
    # 专家访谈来源
    INTERVIEW_SOURCES = {
        "a16z Podcast": "https://a16z.com/podcasts/",
        "Lex Fridman Podcast": "https://lexfridman.com/podcast/",
        "Stanford HAI": "https://hai.stanford.edu/news",
        "MIT Tech Review": "https://www.technologyreview.com/topic/artificial-intelligence/",
        "IEEE Spectrum AI": "https://spectrum.ieee.org/topic/artificial-intelligence",
        "VentureBeat AI": "https://venturebeat.com/category/ai/",
        "Wired AI": "https://www.wired.com/tag/artificial-intelligence/",
        # 中文
        "机器之心": "https://www.jiqizhixin.com/",
        "量子位": "https://www.qbitai.com/",
        "新智元": "https://www.jiqie.com/",
    }
    
    # 知名专家博客
    EXPERT_BLOGS = {
        "Andrej Karpathy": "https://karpathy.ai/",
        "Andrew Ng": "https://www.deeplearning.ai/the-batch/",
        "Yann LeCun": "https://twitter.com/ylecun",
        "Geoffrey Hinton": "https://www.cs.toronto.edu/~hinton/",
        "Sam Altman": "https://blog.samaltman.com/",
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def find_reports(self, keywords: List[str] = None) -> List[Dict]:
        """
        搜索相关研报
        
        Args:
            keywords: 搜索关键词，如 ['自动驾驶', 'AI', 'robotaxi']
        
        Returns:
            研报候选列表
        """
        if keywords is None:
            keywords = ['autonomous vehicle', 'self-driving', 'robotaxi', 'AI', 'artificial intelligence']
        
        candidates = []
        
        console.print("[cyan]正在搜索相关研报...[/cyan]")
        
        for name, url in self.REPORT_SOURCES.items():
            try:
                results = self._search_source(name, url, keywords, 'report')
                candidates.extend(results)
            except Exception as e:
                console.print(f"[yellow]搜索 {name} 失败: {e}[/yellow]")
        
        return candidates
    
    def find_interviews(self, keywords: List[str] = None) -> List[Dict]:
        """
        搜索专家访谈
        
        Args:
            keywords: 搜索关键词
        
        Returns:
            访谈候选列表
        """
        if keywords is None:
            keywords = ['AI', 'autonomous', 'self-driving', 'OpenAI', 'Tesla', 'Waymo']
        
        candidates = []
        
        console.print("[cyan]正在搜索专家访谈和观点...[/cyan]")
        
        for name, url in self.INTERVIEW_SOURCES.items():
            try:
                results = self._search_source(name, url, keywords, 'interview')
                candidates.extend(results)
            except Exception as e:
                console.print(f"[yellow]搜索 {name} 失败: {e}[/yellow]")
        
        return candidates
    
    def _search_source(self, source_name: str, url: str, keywords: List[str], source_type: str) -> List[Dict]:
        """搜索单个来源"""
        results = []
        
        try:
            response = self.session.get(url, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 查找文章链接
            links = soup.find_all('a', href=True)
            
            for link in links[:30]:
                title = link.get_text(strip=True)
                href = link['href']
                
                # 过滤相关内容
                if not title or len(title) < 15:
                    continue
                
                # 检查是否包含关键词
                title_lower = title.lower()
                if not any(kw.lower() in title_lower for kw in keywords):
                    continue
                
                # 补全URL
                if href.startswith('/'):
                    base_url = '/'.join(url.split('/')[:3])
                    href = base_url + href
                elif not href.startswith('http'):
                    continue
                
                # 过滤导航链接
                skip_words = ['login', 'signup', 'subscribe', 'contact', 'about', 'privacy']
                if any(w in href.lower() for w in skip_words):
                    continue
                
                results.append({
                    'title': title,
                    'source': source_name,
                    'type': source_type,
                    'url': href
                })
        
        except Exception as e:
            pass
        
        return results[:5]  # 每个来源最多5条
    
    def display_candidates(self, candidates: List[Dict], title: str = "候选列表"):
        """显示候选列表供用户选择"""
        if not candidates:
            console.print(f"[yellow]未找到相关{title}[/yellow]")
            return
        
        table = Table(title=title)
        table.add_column("序号", style="cyan", width=6)
        table.add_column("标题", style="green", width=60)
        table.add_column("来源", style="blue", width=15)
        table.add_column("链接", style="white", width=40)
        
        for i, item in enumerate(candidates, 1):
            table.add_row(
                str(i),
                item['title'][:60] + ("..." if len(item['title']) > 60 else ""),
                item['source'],
                item['url'][:40] + "..."
            )
        
        console.print(table)
        console.print(f"\n[bold]共 {len(candidates)} 条候选内容[/bold]")


class ResearchExtractor:
    """研究内容提取器 - 从PDF或网页提取原文观点"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract_from_url(self, url: str, source_name: str = "") -> ResearchInsight:
        """
        从网页URL提取原文观点
        
        Args:
            url: 文章URL
            source_name: 来源名称
        
        Returns:
            ResearchInsight 对象
        """
        console.print(f"[cyan]正在提取: {url[:50]}...[/cyan]")
        
        try:
            response = self.session.get(url, timeout=20)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 提取标题
            title = self._extract_title(soup)
            
            # 提取原文段落（关键观点）
            insights = self._extract_key_paragraphs(soup)
            
            # 提取图片
            images = self._extract_images(soup, url)
            
            # 提取日期和作者
            date = self._extract_date(soup)
            author = self._extract_author(soup)
            
            return ResearchInsight(
                title=title,
                source=source_name or self._extract_source(soup, url),
                source_type="interview",
                source_url=url,
                insights=insights,
                images=images,
                date=date,
                author=author
            )
            
        except Exception as e:
            console.print(f"[red]提取失败: {e}[/red]")
            return ResearchInsight(
                title="提取失败",
                source=source_name,
                source_type="interview",
                source_url=url,
                insights=[f"提取失败: {e}"]
            )
    
    def extract_from_pdf(self, pdf_path: str, source_name: str = "") -> ResearchInsight:
        """
        从PDF文件提取原文观点
        
        Args:
            pdf_path: PDF文件路径
            source_name: 来源名称（如"麦肯锡"）
        
        Returns:
            ResearchInsight 对象
        """
        console.print(f"[cyan]正在解析PDF: {pdf_path}[/cyan]")
        
        try:
            # 尝试使用 PyPDF2 或 pdfplumber
            text_content = self._read_pdf(pdf_path)
            
            if not text_content:
                return ResearchInsight(
                    title="PDF解析失败",
                    source=source_name,
                    source_type="report",
                    source_url=pdf_path,
                    insights=["无法解析PDF内容，请检查文件格式"]
                )
            
            # 提取原文观点
            insights = self._extract_key_insights_from_text(text_content)
            
            # 从文件名提取标题
            title = os.path.basename(pdf_path).replace('.pdf', '').replace('_', ' ')
            
            return ResearchInsight(
                title=title,
                source=source_name,
                source_type="report",
                source_url=pdf_path,
                insights=insights,
                images=[],  # PDF图片提取较复杂，暂时返回空
                date="",
                author=""
            )
            
        except Exception as e:
            console.print(f"[red]PDF解析失败: {e}[/red]")
            return ResearchInsight(
                title="PDF解析失败",
                source=source_name,
                source_type="report",
                source_url=pdf_path,
                insights=[f"解析失败: {e}"]
            )
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """提取标题"""
        # 尝试多种标题标签
        for tag in ['h1', 'title', '.article-title', '.post-title', 'header h1']:
            elem = soup.select_one(tag)
            if elem:
                return elem.get_text(strip=True)
        return "未知标题"
    
    def _extract_key_paragraphs(self, soup: BeautifulSoup) -> List[str]:
        """
        提取关键段落（原文观点）
        重要：只提取原文，不总结
        """
        paragraphs = []
        
        # 查找正文区域
        content_selectors = [
            'article',
            '.article-content',
            '.post-content',
            '.entry-content',
            '.content-body',
            'main article',
            '.rich_media_content',  # 微信
        ]
        
        content_elem = None
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                break
        
        if not content_elem:
            content_elem = soup.find('body')
        
        if not content_elem:
            return paragraphs
        
        # 提取所有段落
        for p in content_elem.find_all(['p', 'blockquote']):
            text = p.get_text(strip=True)
            
            # 过滤太短或无意义的内容
            if len(text) < 30:
                continue
            
            # 过滤导航、广告等
            skip_keywords = ['subscribe', 'sign up', 'login', 'cookie', 'advertisement', 
                           '关注', '订阅', '登录', '广告']
            if any(kw in text.lower() for kw in skip_keywords):
                continue
            
            # 只保留包含关键信息的段落
            keywords = ['AI', '自动驾驶', 'autonomous', 'robotaxi', 'Tesla', 'Waymo', 
                       'OpenAI', 'Anthropic', '融资', '投资', '市场', '预测', '趋势',
                       '技术', '发展', '未来', '突破', '创新', 'L4', 'L3']
            
            if any(kw in text for kw in keywords):
                paragraphs.append(text)
        
        return paragraphs[:10]  # 最多10个关键段落
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """提取图片"""
        images = []
        
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src')
            if not src:
                continue
            
            # 补全URL
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = '/'.join(base_url.split('/')[:3]) + src
            elif not src.startswith('http'):
                continue
            
            # 过滤小图片和图标
            if any(x in src.lower() for x in ['icon', 'logo', 'avatar', 'button']):
                continue
            
            images.append(src)
        
        return images[:5]  # 最多5张图片
    
    def _extract_date(self, soup: BeautifulSoup) -> str:
        """提取日期"""
        # 尝试多种日期格式
        date_selectors = [
            'time',
            '.date',
            '.publish-date',
            '.post-date',
            'meta[property="article:published_time"]',
        ]
        
        for selector in date_selectors:
            elem = soup.select_one(selector)
            if elem:
                date = elem.get('datetime') or elem.get('content') or elem.get_text(strip=True)
                if date:
                    return date[:10]  # 只保留日期部分
        
        return ""
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """提取作者"""
        author_selectors = [
            '.author',
            '.byline',
            'meta[name="author"]',
        ]
        
        for selector in author_selectors:
            elem = soup.select_one(selector)
            if elem:
                return elem.get('content') or elem.get_text(strip=True)
        
        return ""
    
    def _extract_source(self, soup: BeautifulSoup, url: str) -> str:
        """从URL提取来源"""
        domain = url.split('/')[2]
        
        # 常见域名映射
        domain_map = {
            'techcrunch.com': 'TechCrunch',
            'theinformation.com': 'The Information',
            'businessinsider.com': 'Business Insider',
            'mckinsey.com': 'McKinsey',
            'bcg.com': 'BCG',
            'a16z.com': 'a16z',
            'stanford.edu': 'Stanford',
            'mit.edu': 'MIT',
        }
        
        for key, value in domain_map.items():
            if key in domain:
                return value
        
        return domain
    
    def _read_pdf(self, pdf_path: str) -> str:
        """读取PDF内容"""
        text = ""
        
        # 尝试使用 pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages[:20]:  # 只读前20页
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
            return text
        except ImportError:
            pass
        
        # 尝试使用 PyPDF2
        try:
            import PyPDF2
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages[:20]:
                    text += page.extract_text() + "\n\n"
            return text
        except ImportError:
            pass
        
        # 如果都没安装，提示安装
        console.print("[yellow]请安装 PDF 解析库: pip install pdfplumber 或 pip install PyPDF2[/yellow]")
        return ""
    
    def _extract_key_insights_from_text(self, text: str) -> List[str]:
        """
        从文本中提取关键观点
        重要：只提取原文句子，不总结
        """
        insights = []
        
        # 按句子分割
        sentences = re.split(r'[。！？\n]', text)
        
        # 关键词过滤
        keywords = ['AI', '自动驾驶', 'autonomous', 'robotaxi', 'Tesla', 'Waymo',
                   'OpenAI', 'Anthropic', '市场', '预测', '趋势', '技术', '发展',
                   '未来', '突破', '创新', '增长', '投资', '融资', '亿', '%']
        
        for sentence in sentences:
            sentence = sentence.strip()
            
            # 长度过滤
            if len(sentence) < 20 or len(sentence) > 500:
                continue
            
            # 包含关键词
            if any(kw in sentence for kw in keywords):
                insights.append(sentence)
        
        return insights[:10]


class ResearchInsightFormatter:
    """研究观点格式化器 - 生成Markdown格式"""
    
    def format_insight(self, insight: ResearchInsight) -> str:
        """格式化单个研究观点"""
        if insight.source_type == "report":
            return self._format_report(insight)
        else:
            return self._format_interview(insight)
    
    def _format_report(self, insight: ResearchInsight) -> str:
        """格式化研报观点"""
        md = f"### {insight.title}\n\n"
        md += f"> 来源：{insight.source}"
        if insight.date:
            md += f" | 时间：{insight.date}"
        md += "\n\n"
        
        if insight.insights:
            md += "**核心观点（原文摘录）：**\n\n"
            for i, point in enumerate(insight.insights, 1):
                md += f"{i}. {point}\n\n"
        
        if insight.images:
            md += "**关键图表：**\n\n"
            for img in insight.images:
                md += f"![图表]({img})\n\n"
        
        md += f"**原文链接：** {insight.source_url}\n\n"
        md += "---\n\n"
        
        return md
    
    def _format_interview(self, insight: ResearchInsight) -> str:
        """格式化专家访谈"""
        md = f"### {insight.title}\n\n"
        md += f"> 来源：{insight.source}"
        if insight.author:
            md += f" | 人物：{insight.author}"
        if insight.date:
            md += f" | 时间：{insight.date}"
        md += "\n\n"
        
        if insight.insights:
            md += "**核心观点（原文摘录）：**\n\n"
            for i, point in enumerate(insight.insights, 1):
                md += f"{i}. {point}\n\n"
        
        md += f"**原文链接：** {insight.source_url}\n\n"
        md += "---\n\n"
        
        return md
    
    def format_section(self, insights: List[ResearchInsight]) -> str:
        """格式化整个研究观点板块"""
        md = "## 研究观点摘录\n\n"
        
        if not insights:
            md += "*暂无研究观点内容*\n\n"
            return md
        
        for insight in insights:
            md += self.format_insight(insight)
        
        return md
