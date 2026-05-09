"""
自动研报爬虫模块
自动爬取AI/自动驾驶相关的研报和洞察文章
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
    source_url: str
    date: str
    content: str  # 关键内容摘要
    category: str  # 研报/专家观点/洞察


class AutoResearchScraper:
    """自动研报爬虫"""
    
    # 研报/洞察来源配置
    SOURCES = {
        # 国际咨询机构
        'mckinsey': {
            'name': '麦肯锡',
            'url': 'https://www.mckinsey.com/industries/technology-media-and-telecommunications/our-insights',
            'type': 'insights',
            'keywords': ['AI', 'artificial intelligence', 'autonomous', 'automotive', 'technology']
        },
        'bcg': {
            'name': '波士顿咨询',
            'url': 'https://www.bcg.com/industries/technology-industry',
            'type': 'insights',
            'keywords': ['AI', 'artificial intelligence', 'autonomous']
        },
        'bain': {
            'name': '贝恩咨询',
            'url': 'https://www.bain.com/insights/',
            'type': 'insights',
            'keywords': ['AI', 'artificial intelligence', 'technology']
        },
        
        # 投资机构博客
        'a16z': {
            'name': 'a16z',
            'url': 'https://a16z.com/ai/',
            'type': 'vc_blog',
            'keywords': ['AI', 'artificial intelligence', 'LLM', 'autonomous']
        },
        'sequoia': {
            'name': '红杉资本',
            'url': 'https://www.sequoiacap.com/article/',
            'type': 'vc_blog',
            'keywords': ['AI', 'artificial intelligence']
        },
        
        # AI公司博客
        'openai_blog': {
            'name': 'OpenAI',
            'url': 'https://openai.com/blog/',
            'type': 'company_blog',
            'keywords': ['GPT', 'AI', 'LLM', 'AGI']
        },
        'anthropic_blog': {
            'name': 'Anthropic',
            'url': 'https://www.anthropic.com/news',
            'type': 'company_blog',
            'keywords': ['Claude', 'AI', 'LLM', 'safety']
        },
        'google_ai': {
            'name': 'Google AI',
            'url': 'https://blog.google/technology/ai/',
            'type': 'company_blog',
            'keywords': ['AI', 'Gemini', 'machine learning']
        },
        'deepmind': {
            'name': 'DeepMind',
            'url': 'https://deepmind.google/',
            'type': 'company_blog',
            'keywords': ['AI', 'research', 'deep learning']
        },
        
        # 自动驾驶公司
        'waymo': {
            'name': 'Waymo',
            'url': 'https://waymo.com/blog/',
            'type': 'company_blog',
            'keywords': ['autonomous', 'self-driving', 'robotaxi']
        },
        'cruise': {
            'name': 'Cruise',
            'url': 'https://www.getcruise.com/news/',
            'type': 'company_blog',
            'keywords': ['autonomous', 'self-driving']
        },
        
        # 学术论文
        'arxiv_cs_ai': {
            'name': 'arXiv AI',
            'url': 'https://arxiv.org/list/cs.AI/recent',
            'type': 'academic',
            'keywords': ['AI', 'machine learning', 'deep learning']
        },
        'arxiv_cs_ro': {
            'name': 'arXiv Robotics',
            'url': 'https://arxiv.org/list/cs.RO/recent',
            'type': 'academic',
            'keywords': ['robotics', 'autonomous']
        },
        
        # 国内研究机构
        'iresearch': {
            'name': '艾瑞咨询',
            'url': 'https://www.iresearch.com.cn/report/',
            'type': 'research_cn',
            'keywords': ['人工智能', 'AI', '自动驾驶', '大模型']
        },
        'analysys': {
            'name': '易观分析',
            'url': 'https://www.analysys.cn/article/list/',
            'type': 'research_cn',
            'keywords': ['人工智能', 'AI', '数字经济']
        },
        
        # 科技媒体深度文章
        'mit_tr': {
            'name': 'MIT Technology Review',
            'url': 'https://www.technologyreview.com/topic/artificial-intelligence/',
            'type': 'tech_media',
            'keywords': ['AI', 'artificial intelligence']
        },
        'wired_ai': {
            'name': 'Wired AI',
            'url': 'https://www.wired.com/tag/artificial-intelligence/',
            'type': 'tech_media',
            'keywords': ['AI', 'artificial intelligence']
        },
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
    
    def scrape_all(self, keywords: List[str] = None, max_per_source: int = 3) -> List[ResearchArticle]:
        """
        爬取所有研报来源
        
        Args:
            keywords: 过滤关键词
            max_per_source: 每个来源最多爬取数量
        """
        if keywords is None:
            keywords = ['AI', 'artificial intelligence', 'autonomous', 'self-driving', 
                       'LLM', 'GPT', 'machine learning', '人工智能', '自动驾驶', '大模型']
        
        all_articles = []
        
        console.print("\n[yellow]正在爬取研报和洞察文章...[/yellow]")
        
        for source_id, source_config in self.SOURCES.items():
            try:
                console.print(f"[cyan]爬取: {source_config['name']}...[/cyan]")
                articles = self._scrape_source(source_id, source_config, keywords, max_per_source)
                all_articles.extend(articles)
                console.print(f"[green]获取 {len(articles)} 条[/green]")
            except Exception as e:
                console.print(f"[red]爬取 {source_config['name']} 失败: {str(e)[:50]}[/red]")
        
        return all_articles
    
    def _scrape_source(self, source_id: str, config: Dict, keywords: List[str], max_count: int) -> List[ResearchArticle]:
        """爬取单个来源"""
        articles = []
        
        try:
            response = self.session.get(config['url'], timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 根据不同类型使用不同的解析方法
            source_type = config.get('type', 'insights')
            
            if source_type == 'academic':
                articles = self._parse_arxiv(soup, config, keywords, max_count)
            elif source_type == 'research_cn':
                articles = self._parse_chinese_research(soup, config, keywords, max_count)
            elif source_type == 'company_blog':
                articles = self._parse_company_blog(soup, config, keywords, max_count)
            else:
                articles = self._parse_generic(soup, config, keywords, max_count)
        
        except Exception as e:
            pass
        
        return articles
    
    def _parse_arxiv(self, soup, config: Dict, keywords: List[str], max_count: int) -> List[ResearchArticle]:
        """解析 arXiv 论文列表"""
        articles = []
        
        # arXiv 论文链接
        links = soup.select('a[href*="/abs/"]')
        
        for link in links[:max_count * 2]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 10:
                continue
            
            # 检查关键词
            title_lower = title.lower()
            if not any(kw.lower() in title_lower for kw in keywords):
                continue
            
            if href.startswith('/'):
                href = f"https://arxiv.org{href}"
            
            article = ResearchArticle(
                title=title,
                source=config['name'],
                source_url=href,
                date=datetime.now().strftime('%Y-%m-%d'),
                content="",  # 论文需要单独提取摘要
                category='学术论文'
            )
            articles.append(article)
            
            if len(articles) >= max_count:
                break
        
        return articles
    
    def _parse_chinese_research(self, soup, config: Dict, keywords: List[str], max_count: int) -> List[ResearchArticle]:
        """解析国内研究机构"""
        articles = []
        
        links = soup.select('a[href*=".pdf"], a[href*="report"], .article-title a, h3 a, h2 a')
        
        for link in links[:max_count * 3]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5:
                continue
            
            # 检查关键词
            title_lower = title.lower()
            if not any(kw.lower() in title_lower for kw in keywords):
                continue
            
            # 构建完整URL
            base_url = '/'.join(config['url'].split('/')[:3])
            if href.startswith('/'):
                href = base_url + href
            elif not href.startswith('http'):
                continue
            
            article = ResearchArticle(
                title=title,
                source=config['name'],
                source_url=href,
                date=datetime.now().strftime('%Y-%m-%d'),
                content="",
                category='研报'
            )
            articles.append(article)
            
            if len(articles) >= max_count:
                break
        
        return articles
    
    def _parse_company_blog(self, soup, config: Dict, keywords: List[str], max_count: int) -> List[ResearchArticle]:
        """解析公司博客"""
        articles = []
        
        # 常见的博客文章选择器
        links = soup.select('article a, .post a, .blog-post a, a[href*="/blog/"], a[href*="/news/"], h2 a, h3 a')
        
        seen_urls = set()
        for link in links[:max_count * 3]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5:
                continue
            
            # 去重
            if href in seen_urls:
                continue
            seen_urls.add(href)
            
            # 构建完整URL
            base_url = '/'.join(config['url'].split('/')[:3])
            if href.startswith('/'):
                href = base_url + href
            elif not href.startswith('http'):
                continue
            
            article = ResearchArticle(
                title=title,
                source=config['name'],
                source_url=href,
                date=datetime.now().strftime('%Y-%m-%d'),
                content="",
                category='公司动态'
            )
            articles.append(article)
            
            if len(articles) >= max_count:
                break
        
        return articles
    
    def _parse_generic(self, soup, config: Dict, keywords: List[str], max_count: int) -> List[ResearchArticle]:
        """通用解析方法"""
        articles = []
        
        links = soup.select('a')
        
        seen_urls = set()
        for link in links[:max_count * 5]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 10:
                continue
            
            # 检查关键词
            title_lower = title.lower()
            if not any(kw.lower() in title_lower for kw in keywords):
                continue
            
            # 去重
            if href in seen_urls:
                continue
            seen_urls.add(href)
            
            # 构建完整URL
            base_url = '/'.join(config['url'].split('/')[:3])
            if href.startswith('/'):
                href = base_url + href
            elif not href.startswith('http'):
                continue
            
            article = ResearchArticle(
                title=title,
                source=config['name'],
                source_url=href,
                date=datetime.now().strftime('%Y-%m-%d'),
                content="",
                category='洞察'
            )
            articles.append(article)
            
            if len(articles) >= max_count:
                break
        
        return articles
    
    def extract_article_content(self, url: str) -> str:
        """提取文章正文内容"""
        try:
            response = self.session.get(url, timeout=15)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 尝试多种内容选择器
            content_selectors = [
                'article',
                '.article-content',
                '.post-content',
                '.entry-content',
                '.content-body',
                'main article',
                '.rich_media_content',
                '.article-body',
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # 清理
                    for tag in content_elem.find_all(['script', 'style', 'nav', 'aside', 'footer']):
                        tag.decompose()
                    
                    # 获取段落
                    paragraphs = content_elem.find_all('p')
                    if paragraphs:
                        texts = []
                        for p in paragraphs[:10]:
                            text = p.get_text(strip=True)
                            if len(text) > 30:
                                texts.append(text)
                        return '\n\n'.join(texts[:5])
            
            return ""
            
        except Exception as e:
            return ""


# 便捷函数
def scrape_research_reports(keywords: List[str] = None, max_per_source: int = 3) -> List[ResearchArticle]:
    """爬取研报的便捷函数"""
    scraper = AutoResearchScraper()
    return scraper.scrape_all(keywords, max_per_source)
