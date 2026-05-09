"""
自动研报爬虫模块
自动爬取公开的AI/自动驾驶研报和洞察文章
"""
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()


@dataclass
class ReportItem:
    """研报数据结构"""
    title: str
    source: str
    date: str
    url: str
    summary: str  # 摘要/关键观点
    category: str  # 研报/洞察/论文


class AutoReportScraper:
    """自动研报爬虫"""
    
    # 公开可访问的研报/洞察来源
    SOURCES = {
        # 国外咨询公司（公开洞察文章）
        '麦肯锡': {
            'url': 'https://www.mckinsey.com/industries/technology-media-and-telecommunications/our-insights',
            'type': 'insight',
            'keywords': ['AI', 'artificial intelligence', 'autonomous', 'automotive', 'technology']
        },
        '波士顿咨询': {
            'url': 'https://www.bcg.com/industries/technology-digital',
            'type': 'insight',
            'keywords': ['AI', 'artificial intelligence', 'autonomous', 'digital']
        },
        '贝恩咨询': {
            'url': 'https://www.bain.com/insights/',
            'type': 'insight',
            'keywords': ['AI', 'artificial intelligence', 'technology', 'automotive']
        },
        
        # 投资机构博客
        'a16z': {
            'url': 'https://a16z.com/ai/',
            'type': 'blog',
            'keywords': ['AI', 'artificial intelligence', 'LLM', 'autonomous']
        },
        '红杉资本': {
            'url': 'https://www.sequoiacap.com/article/',
            'type': 'blog',
            'keywords': ['AI', 'artificial intelligence', 'autonomous', 'startup']
        },
        
        # AI公司博客
        'OpenAI Blog': {
            'url': 'https://openai.com/blog/',
            'type': 'blog',
            'keywords': ['AI', 'GPT', 'LLM', 'AGI']
        },
        'Anthropic Blog': {
            'url': 'https://www.anthropic.com/news',
            'type': 'blog',
            'keywords': ['AI', 'Claude', 'LLM', 'safety']
        },
        'Google AI Blog': {
            'url': 'https://blog.google/technology/ai/',
            'type': 'blog',
            'keywords': ['AI', 'machine learning', 'Gemini']
        },
        'DeepMind Blog': {
            'url': 'https://deepmind.google/',
            'type': 'blog',
            'keywords': ['AI', 'research', 'deep learning']
        },
        'Meta AI Blog': {
            'url': 'https://ai.meta.com/blog/',
            'type': 'blog',
            'keywords': ['AI', 'LLaMA', 'open source']
        },
        
        # 自动驾驶公司
        'Waymo Blog': {
            'url': 'https://waymo.com/blog/',
            'type': 'blog',
            'keywords': ['autonomous', 'self-driving', 'robotaxi', 'Waymo']
        },
        'Tesla AI': {
            'url': 'https://www.tesla.com/AI',
            'type': 'blog',
            'keywords': ['FSD', 'Autopilot', 'autonomous', 'Tesla']
        },
        
        # 学术论文
        'arXiv AI': {
            'url': 'https://arxiv.org/list/cs.AI/recent',
            'type': 'paper',
            'keywords': ['AI', 'machine learning', 'deep learning']
        },
        'arXiv Robotics': {
            'url': 'https://arxiv.org/list/cs.RO/recent',
            'type': 'paper',
            'keywords': ['robotics', 'autonomous', 'control']
        },
        
        # 国内研究机构
        '艾瑞咨询': {
            'url': 'https://www.iresearch.com.cn/report/',
            'type': 'report',
            'keywords': ['AI', '人工智能', '自动驾驶', '互联网']
        },
        '亿欧智库': {
            'url': 'https://www.iyiou.com/research',
            'type': 'report',
            'keywords': ['AI', '人工智能', '自动驾驶', '科技']
        },
        
        # 科技媒体研究
        'Gartner Insights': {
            'url': 'https://www.gartner.com/en/information-technology/insights',
            'type': 'insight',
            'keywords': ['AI', 'technology', 'trends']
        },
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def scrape_all(self, keywords: List[str] = None, max_per_source: int = 5) -> List[ReportItem]:
        """
        爬取所有研报来源
        
        Args:
            keywords: 过滤关键词，None表示不过滤
            max_per_source: 每个来源最多爬取数量
        """
        if keywords is None:
            keywords = ['AI', 'artificial intelligence', 'autonomous', 'self-driving', 
                       '人工智能', '自动驾驶', '大模型', 'LLM', 'AGI', 'robotaxi']
        
        all_reports = []
        
        for source_name, source_config in self.SOURCES.items():
            console.print(f"[cyan]正在爬取: {source_name}...[/cyan]")
            
            try:
                reports = self._scrape_source(source_name, source_config, keywords, max_per_source)
                all_reports.extend(reports)
                console.print(f"[green]获取 {len(reports)} 条[/green]")
            except Exception as e:
                console.print(f"[yellow]爬取失败: {str(e)[:50]}[/yellow]")
        
        return all_reports
    
    def _scrape_source(self, source_name: str, config: Dict, keywords: List[str], max_items: int) -> List[ReportItem]:
        """爬取单个来源"""
        reports = []
        
        response = self.session.get(config['url'], timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')
        
        # 查找文章链接
        links = soup.find_all('a', href=True)
        
        seen_urls = set()
        for link in links:
            href = link.get('href', '')
            title = link.get_text(strip=True)
            
            # 过滤条件
            if len(title) < 15:
                continue
            
            # 检查关键词
            title_lower = title.lower()
            source_keywords = config.get('keywords', [])
            if not any(kw.lower() in title_lower for kw in keywords + source_keywords):
                continue
            
            # 构建完整URL
            if href.startswith('/'):
                base_url = '/'.join(config['url'].split('/')[:3])
                href = base_url + href
            elif not href.startswith('http'):
                continue
            
            # 去重
            if href in seen_urls:
                continue
            seen_urls.add(href)
            
            # 提取日期
            date = self._extract_date_from_url(href) or datetime.now().strftime('%Y-%m-%d')
            
            report = ReportItem(
                title=title,
                source=source_name,
                date=date,
                url=href,
                summary="",  # 摘要需要单独爬取文章内容
                category=config['type']
            )
            reports.append(report)
            
            if len(reports) >= max_items:
                break
        
        return reports
    
    def _extract_date_from_url(self, url: str) -> str:
        """从URL中提取日期"""
        patterns = [
            r'/(\d{4})/(\d{2})/(\d{2})/',
            r'/(\d{4})(\d{2})(\d{2})',
            r'-(\d{4})-(\d{2})-(\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
        
        return ""
    
    def fetch_report_content(self, report: ReportItem) -> str:
        """
        爬取研报全文内容，提取关键段落
        """
        try:
            response = self.session.get(report.url, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 提取正文
            content_selectors = [
                'article',
                '.article-content',
                '.post-content',
                '.entry-content',
                '.content-body',
                '.rich-text',
                'main article',
            ]
            
            content_text = ""
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    for tag in content_elem.find_all(['script', 'style', 'nav', 'aside']):
                        tag.decompose()
                    content_text = content_elem.get_text(separator='\n')
                    break
            
            if not content_text:
                paragraphs = soup.find_all('p')
                content_text = '\n'.join([p.get_text(strip=True) for p in paragraphs])
            
            # 提取关键段落
            key_paragraphs = self._extract_key_paragraphs(content_text)
            
            return key_paragraphs
            
        except Exception as e:
            return f"[内容获取失败: {str(e)[:30]}]"
    
    def _extract_key_paragraphs(self, text: str, max_paragraphs: int = 3) -> str:
        """提取关键段落"""
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        
        # 关键词权重
        important_keywords = [
            'AI', 'artificial intelligence', 'machine learning', 'deep learning',
            'autonomous', 'self-driving', 'robotaxi', 'LLM', 'GPT', 'AGI',
            '人工智能', '自动驾驶', '大模型', '机器学习',
            'announced', 'released', 'launched', '发布', '推出',
            '$', 'million', 'billion', '亿',
        ]
        
        scored = []
        for para in paragraphs:
            if len(para) < 50 or len(para) > 500:
                continue
            
            score = sum(1 for kw in important_keywords if kw.lower() in para.lower())
            if score > 0:
                scored.append((para, score))
        
        scored.sort(key=lambda x: x[1], reverse=True)
        
        if scored:
            return '\n\n'.join([p[0] for p in scored[:max_paragraphs]])
        
        # 如果没有匹配关键词的，返回前几个段落
        return '\n\n'.join(paragraphs[:max_paragraphs])


def scrape_reports(keywords: List[str] = None, fetch_content: bool = True) -> List[ReportItem]:
    """
    便捷函数：爬取研报
    
    Args:
        keywords: 过滤关键词
        fetch_content: 是否爬取全文内容
    """
    scraper = AutoReportScraper()
    reports = scraper.scrape_all(keywords)
    
    if fetch_content:
        console.print("\n[yellow]正在提取研报内容...[/yellow]")
        for i, report in enumerate(reports):
            console.print(f"[dim]处理 {i+1}/{len(reports)}: {report.title[:30]}...[/dim]")
            report.summary = scraper.fetch_report_content(report)
    
    return reports


if __name__ == '__main__':
    # 测试
    reports = scrape_reports(fetch_content=True)
    
    print(f"\n共爬取 {len(reports)} 条研报/洞察")
    for r in reports[:5]:
        print(f"\n【{r.source}】{r.title}")
        print(f"链接: {r.url}")
        if r.summary:
            print(f"摘要: {r.summary[:100]}...")
