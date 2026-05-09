"""
研报自动爬取模块
自动爬取AI/自动驾驶领域的公开研报和洞察文章
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
class ResearchArticle:
    """研报/洞察文章数据结构"""
    title: str
    source: str
    url: str
    date: str
    summary: str  # 摘要
    key_insights: List[str]  # 关键洞察
    category: str = "research"  # research/insight/report


class AutoReportScraper:
    """自动研报爬虫"""
    
    # 研报/洞察来源（这些网站有公开内容）
    SOURCES = {
        # 国际咨询公司
        'mckinsey': {
            'name': '麦肯锡',
            'url': 'https://www.mckinsey.com/industries/automotive-and-assembly/our-insights',
            'ai_url': 'https://www.mckinsey.com/capabilities/quantumblack/our-insights',
            'type': 'insight',
            'language': 'en'
        },
        'bcg': {
            'name': '波士顿咨询',
            'url': 'https://www.bcg.com/industries/technology-industries',
            'type': 'insight',
            'language': 'en'
        },
        'bain': {
            'name': '贝恩咨询',
            'url': 'https://www.bain.com/insights/',
            'type': 'insight',
            'language': 'en'
        },
        # 国内研究机构
        'iresearch': {
            'name': '艾瑞咨询',
            'url': 'https://www.iresearch.com.cn/List/10.shtml',  # 科技频道
            'type': 'report',
            'language': 'zh'
        },
        'analysys': {
            'name': '易观分析',
            'url': 'https://www.analysys.cn/article/list.html',
            'type': 'report',
            'language': 'zh'
        },
        'questmobile': {
            'name': 'QuestMobile',
            'url': 'https://www.questmobile.com.cn/research',
            'type': 'report',
            'language': 'zh'
        },
        # 投资机构洞察
        'a16z': {
            'name': 'Andreessen Horowitz',
            'url': 'https://a16z.com/ai/',
            'type': 'insight',
            'language': 'en'
        },
        'sequoia': {
            'name': '红杉资本',
            'url': 'https://www.sequoiacap.com/article/',
            'type': 'insight',
            'language': 'en'
        },
        # 学术论文
        'arxiv_ai': {
            'name': 'arXiv AI',
            'url': 'https://arxiv.org/list/cs.AI/recent',
            'type': 'paper',
            'language': 'en'
        },
        'arxiv_cv': {
            'name': 'arXiv 计算机视觉',
            'url': 'https://arxiv.org/list/cs.CV/recent',
            'type': 'paper',
            'language': 'en'
        },
        'arxiv_ro': {
            'name': 'arXiv 机器人',
            'url': 'https://arxiv.org/list/cs.RO/recent',
            'type': 'paper',
            'language': 'en'
        },
        # 科技媒体深度报道
        'mit_tr': {
            'name': 'MIT Technology Review',
            'url': 'https://www.technologyreview.com/topic/artificial-intelligence/',
            'type': 'insight',
            'language': 'en'
        },
        'wired_ai': {
            'name': 'Wired AI',
            'url': 'https://www.wired.com/tag/artificial-intelligence/',
            'type': 'insight',
            'language': 'en'
        },
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        
        # AI/自动驾驶关键词
        self.keywords = [
            'AI', 'artificial intelligence', 'machine learning', 'deep learning',
            'LLM', 'GPT', 'transformer', 'neural network',
            'autonomous', 'self-driving', 'driverless', 'robotaxi',
            '自动驾驶', '人工智能', '大模型', '机器学习',
        ]
    
    def scrape_all(self, max_per_source: int = 5) -> List[ResearchArticle]:
        """
        爬取所有来源的研报/洞察
        """
        all_articles = []
        
        for source_id, source_info in self.SOURCES.items():
            try:
                console.print(f"[cyan]正在爬取: {source_info['name']}...[/cyan]")
                articles = self._scrape_source(source_id, source_info, max_per_source)
                all_articles.extend(articles)
                console.print(f"[green]获取 {len(articles)} 条内容[/green]")
            except Exception as e:
                console.print(f"[yellow]爬取 {source_info['name']} 失败: {str(e)[:50]}[/yellow]")
        
        return all_articles
    
    def _scrape_source(self, source_id: str, source_info: Dict, max_items: int) -> List[ResearchArticle]:
        """爬取单个来源"""
        articles = []
        
        url = source_info['url']
        response = self.session.get(url, timeout=20)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'lxml')
        
        # 根据不同来源使用不同的解析器
        if source_id == 'mckinsey':
            articles = self._parse_mckinsey(soup, source_info, max_items)
        elif source_id == 'bcg':
            articles = self._parse_bcg(soup, source_info, max_items)
        elif source_id == 'bain':
            articles = self._parse_bain(soup, source_info, max_items)
        elif source_id == 'iresearch':
            articles = self._parse_iresearch(soup, source_info, max_items)
        elif source_id == 'analysys':
            articles = self._parse_analysys(soup, source_info, max_items)
        elif source_id in ['arxiv_ai', 'arxiv_cv', 'arxiv_ro']:
            articles = self._parse_arxiv(soup, source_info, max_items)
        elif source_id == 'a16z':
            articles = self._parse_a16z(soup, source_info, max_items)
        elif source_id == 'sequoia':
            articles = self._parse_sequoia(soup, source_info, max_items)
        elif source_id == 'mit_tr':
            articles = self._parse_mit_tr(soup, source_info, max_items)
        else:
            # 通用解析
            articles = self._parse_generic(soup, source_info, max_items)
        
        return articles
    
    def _parse_mckinsey(self, soup, source_info: Dict, max_items: int) -> List[ResearchArticle]:
        """解析麦肯锡洞察"""
        articles = []
        links = soup.select('a[href*="/insights/"], a[href*="/our-insights/"]')
        
        seen = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 15 or title in seen:
                continue
            
            # 过滤关键词
            if not any(kw.lower() in title.lower() for kw in self.keywords):
                continue
            
            seen.add(title)
            
            if href.startswith('/'):
                href = f"https://www.mckinsey.com{href}"
            
            articles.append(ResearchArticle(
                title=title,
                source=source_info['name'],
                url=href,
                date=datetime.now().strftime('%Y-%m-%d'),
                summary="",
                key_insights=[],
                category="insight"
            ))
            
            if len(articles) >= max_items:
                break
        
        return articles
    
    def _parse_bcg(self, soup, source_info: Dict, max_items: int) -> List[ResearchArticle]:
        """解析BCG洞察"""
        articles = []
        links = soup.select('a[href*="/insights/"], a[href*="/publications/"]')
        
        seen = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 15 or title in seen:
                continue
            
            if not any(kw.lower() in title.lower() for kw in self.keywords):
                continue
            
            seen.add(title)
            
            if href.startswith('/'):
                href = f"https://www.bcg.com{href}"
            
            articles.append(ResearchArticle(
                title=title,
                source=source_info['name'],
                url=href,
                date=datetime.now().strftime('%Y-%m-%d'),
                summary="",
                key_insights=[],
                category="insight"
            ))
            
            if len(articles) >= max_items:
                break
        
        return articles
    
    def _parse_bain(self, soup, source_info: Dict, max_items: int) -> List[ResearchArticle]:
        """解析贝恩洞察"""
        articles = []
        links = soup.select('a[href*="/insights/"], a[href*="/publications/"]')
        
        seen = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 15 or title in seen:
                continue
            
            if not any(kw.lower() in title.lower() for kw in self.keywords):
                continue
            
            seen.add(title)
            
            if href.startswith('/'):
                href = f"https://www.bain.com{href}"
            
            articles.append(ResearchArticle(
                title=title,
                source=source_info['name'],
                url=href,
                date=datetime.now().strftime('%Y-%m-%d'),
                summary="",
                key_insights=[],
                category="insight"
            ))
            
            if len(articles) >= max_items:
                break
        
        return articles
    
    def _parse_iresearch(self, soup, source_info: Dict, max_items: int) -> List[ResearchArticle]:
        """解析艾瑞咨询"""
        articles = []
        links = soup.select('a[href*="/Article/"], a[href*="/report/"]')
        
        seen = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5 or title in seen:
                continue
            
            # 过滤AI相关
            ai_keywords = ['AI', '人工智能', '智能', '自动驾驶', '大模型', '机器学习', '自动驾驶']
            if not any(kw in title for kw in ai_keywords):
                continue
            
            seen.add(title)
            
            if href.startswith('/'):
                href = f"https://www.iresearch.com.cn{href}"
            
            articles.append(ResearchArticle(
                title=title,
                source=source_info['name'],
                url=href,
                date=datetime.now().strftime('%Y-%m-%d'),
                summary="",
                key_insights=[],
                category="report"
            ))
            
            if len(articles) >= max_items:
                break
        
        return articles
    
    def _parse_analysys(self, soup, source_info: Dict, max_items: int) -> List[ResearchArticle]:
        """解析易观分析"""
        articles = []
        links = soup.select('a[href*="/article/"], a[href*="/report/"]')
        
        seen = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5 or title in seen:
                continue
            
            ai_keywords = ['AI', '人工智能', '智能', '自动驾驶', '大模型']
            if not any(kw in title for kw in ai_keywords):
                continue
            
            seen.add(title)
            
            if href.startswith('/'):
                href = f"https://www.analysys.cn{href}"
            
            articles.append(ResearchArticle(
                title=title,
                source=source_info['name'],
                url=href,
                date=datetime.now().strftime('%Y-%m-%d'),
                summary="",
                key_insights=[],
                category="report"
            ))
            
            if len(articles) >= max_items:
                break
        
        return articles
    
    def _parse_arxiv(self, soup, source_info: Dict, max_items: int) -> List[ResearchArticle]:
        """解析arXiv论文"""
        articles = []
        
        # arXiv 最新论文列表
        links = soup.select('dt a[title="Abstract"], dd.list-title a')
        
        seen = set()
        for i, link in enumerate(links[:30]):
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 10 or title in seen:
                continue
            
            seen.add(title)
            
            if href.startswith('/'):
                href = f"https://arxiv.org{href}"
            
            articles.append(ResearchArticle(
                title=title,
                source=source_info['name'],
                url=href,
                date=datetime.now().strftime('%Y-%m-%d'),
                summary="",
                key_insights=[],
                category="paper"
            ))
            
            if len(articles) >= max_items:
                break
        
        return articles
    
    def _parse_a16z(self, soup, source_info: Dict, max_items: int) -> List[ResearchArticle]:
        """解析a16z"""
        articles = []
        links = soup.select('a[href*="/article/"], a[href*="/podcast/"]')
        
        seen = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 10 or title in seen:
                continue
            
            seen.add(title)
            
            if href.startswith('/'):
                href = f"https://a16z.com{href}"
            
            articles.append(ResearchArticle(
                title=title,
                source=source_info['name'],
                url=href,
                date=datetime.now().strftime('%Y-%m-%d'),
                summary="",
                key_insights=[],
                category="insight"
            ))
            
            if len(articles) >= max_items:
                break
        
        return articles
    
    def _parse_sequoia(self, soup, source_info: Dict, max_items: int) -> List[ResearchArticle]:
        """解析红杉资本"""
        articles = []
        links = soup.select('a[href*="/article/"]')
        
        seen = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 10 or title in seen:
                continue
            
            if not any(kw.lower() in title.lower() for kw in self.keywords):
                continue
            
            seen.add(title)
            
            if href.startswith('/'):
                href = f"https://www.sequoiacap.com{href}"
            
            articles.append(ResearchArticle(
                title=title,
                source=source_info['name'],
                url=href,
                date=datetime.now().strftime('%Y-%m-%d'),
                summary="",
                key_insights=[],
                category="insight"
            ))
            
            if len(articles) >= max_items:
                break
        
        return articles
    
    def _parse_mit_tr(self, soup, source_info: Dict, max_items: int) -> List[ResearchArticle]:
        """解析MIT Technology Review"""
        articles = []
        links = soup.select('a[href*="/technology/"], a[href*="/article/"]')
        
        seen = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 10 or title in seen:
                continue
            
            seen.add(title)
            
            if href.startswith('/'):
                href = f"https://www.technologyreview.com{href}"
            
            articles.append(ResearchArticle(
                title=title,
                source=source_info['name'],
                url=href,
                date=datetime.now().strftime('%Y-%m-%d'),
                summary="",
                key_insights=[],
                category="insight"
            ))
            
            if len(articles) >= max_items:
                break
        
        return articles
    
    def _parse_generic(self, soup, source_info: Dict, max_items: int) -> List[ResearchArticle]:
        """通用解析方法"""
        articles = []
        links = soup.select('a')
        
        seen = set()
        for link in links[:30]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 15 or title in seen:
                continue
            
            if not any(kw.lower() in title.lower() for kw in self.keywords):
                continue
            
            seen.add(title)
            
            base_url = '/'.join(source_info['url'].split('/')[:3])
            if href.startswith('/'):
                href = base_url + href
            elif not href.startswith('http'):
                continue
            
            articles.append(ResearchArticle(
                title=title,
                source=source_info['name'],
                url=href,
                date=datetime.now().strftime('%Y-%m-%d'),
                summary="",
                key_insights=[],
                category=source_info.get('type', 'insight')
            ))
            
            if len(articles) >= max_items:
                break
        
        return articles
    
    def fetch_article_content(self, article: ResearchArticle) -> ResearchArticle:
        """
        爬取文章正文内容
        """
        try:
            response = self.session.get(article.url, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 提取正文
            content_selectors = [
                'article',
                '.article-content',
                '.post-content',
                '.entry-content',
                '.content-body',
                'main article',
                '.rich_text',
            ]
            
            content_text = ""
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    for tag in content_elem.find_all(['script', 'style', 'nav', 'aside']):
                        tag.decompose()
                    content_text = content_elem.get_text(separator='\n')
                    break
            
            # 提取摘要（前500字符）
            if content_text:
                article.summary = content_text[:500].strip()
                
                # 提取关键洞察
                article.key_insights = self._extract_insights(content_text)
            
            return article
            
        except Exception as e:
            console.print(f"[dim]抓取正文失败: {article.url[:30]}... - {str(e)[:30]}[/dim]")
            return article
    
    def _extract_insights(self, text: str) -> List[str]:
        """提取关键洞察"""
        insights = []
        
        # 按段落分割
        paragraphs = [p.strip() for p in text.split('\n') if p.strip() and len(p.strip()) > 30]
        
        # 高价值模式
        patterns = [
            r'.*(?:预计|预测|将达|超过|增长|下降|达到)\s*\d+[\.\d]*[%％亿万美元].*',
            r'.*(?:关键|核心|重要|突破|创新|首次).*',
            r'.*We (?:expect|predict|believe|estimate).*',
            r'.*(?:will|expected to|projected to)\s+(?:reach|grow|increase).*',
        ]
        
        for para in paragraphs[:20]:
            for pattern in patterns:
                if re.match(pattern, para, re.IGNORECASE):
                    if para not in insights:
                        insights.append(para[:200])
                    break
            
            if len(insights) >= 5:
                break
        
        return insights
