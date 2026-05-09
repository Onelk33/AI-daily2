"""
研究观点摘录模块
- 研报发现与提取
- 专家访谈发现与提取
- 自动爬取公开研报
"""
import os
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class ResearchReport:
    """研报数据结构"""
    title: str
    source: str  # 券商/机构
    date: str
    keywords: List[str]
    pdf_url: str = ""
    local_path: str = ""
    summary: str = ""  # 摘要
    key_insights: List[str] = None  # 关键观点


@dataclass
class ExpertOpinion:
    """专家观点数据结构"""
    title: str
    expert: str  # 专家姓名
    position: str  # 职位
    source: str  # 来源
    url: str
    date: str
    key_quotes: List[str]  # 原文引用


class AutoReportScraper:
    """自动研报爬虫 - 爬取公开可访问的研究报告"""
    
    # 公开研报来源（可直接爬取内容）
    PUBLIC_SOURCES = {
        # 国际咨询公司
        '麦肯锡': {
            'url': 'https://www.mckinsey.com/industries/technology-media-and-telecommunications/our-insights',
            'type': 'consulting',
            'keywords': ['AI', 'artificial intelligence', 'autonomous', 'technology']
        },
        '麦肯锡汽车': {
            'url': 'https://www.mckinsey.com/industries/automotive-and-assembly/our-insights',
            'type': 'consulting',
            'keywords': ['autonomous', 'mobility', 'electric vehicle']
        },
        'BCG科技': {
            'url': 'https://www.bcg.com/industries/technology-industries',
            'type': 'consulting',
            'keywords': ['AI', 'artificial intelligence', 'technology']
        },
        'BCG汽车': {
            'url': 'https://www.bcg.com/industries/automotive',
            'type': 'consulting',
            'keywords': ['autonomous', 'mobility', 'automotive']
        },
        '贝恩资本': {
            'url': 'https://www.bain.com/insights/',
            'type': 'consulting',
            'keywords': ['AI', 'technology', 'automotive']
        },
        
        # 国内研究机构
        '艾瑞咨询': {
            'url': 'https://www.iresearch.com.cn/report/',
            'type': 'research_cn',
            'keywords': ['人工智能', 'AI', '自动驾驶', '新能源']
        },
        '易观分析': {
            'url': 'https://www.analysys.cn/article/analysis/list',
            'type': 'research_cn',
            'keywords': ['人工智能', 'AI', '自动驾驶']
        },
        '亿欧智库': {
            'url': 'https://www.iyiou.com/research',
            'type': 'research_cn',
            'keywords': ['人工智能', 'AI', '自动驾驶', '智能汽车']
        },
        
        # 投资机构
        'a16z AI': {
            'url': 'https://a16z.com/ai/',
            'type': 'vc',
            'keywords': ['AI', 'artificial intelligence']
        },
        '红杉资本': {
            'url': 'https://www.sequoiacap.com/article/',
            'type': 'vc',
            'keywords': ['AI', 'technology', 'artificial intelligence']
        },
        
        # 学术论文
        'arXiv AI': {
            'url': 'https://arxiv.org/list/cs.AI/recent',
            'type': 'academic',
            'keywords': ['artificial intelligence', 'machine learning', 'deep learning']
        },
        'arXiv Robotics': {
            'url': 'https://arxiv.org/list/cs.RO/recent',
            'type': 'academic',
            'keywords': ['robotics', 'autonomous', 'autonomous vehicles']
        },
        
        # 行业媒体
        'Gartner': {
            'url': 'https://www.gartner.com/en/information-technology/insights',
            'type': 'analyst',
            'keywords': ['AI', 'artificial intelligence', 'technology']
        },
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
    
    def scrape_reports(self, max_per_source: int = 3, date_range: tuple = None) -> List[ResearchReport]:
        """
        自动爬取公开研报
        
        Args:
            max_per_source: 每个来源最多爬取数量
            date_range: 日期范围元组 (start_date, end_date)
        """
        all_reports = []
        
        for source_name, config in self.PUBLIC_SOURCES.items():
            try:
                console.print(f"[cyan]正在爬取: {source_name}...[/cyan]")
                reports = self._scrape_source(source_name, config, max_per_source, date_range)
                all_reports.extend(reports)
                console.print(f"[green]获取 {len(reports)} 条[/green]")
            except Exception as e:
                console.print(f"[dim]爬取 {source_name} 失败: {str(e)[:50]}[/dim]")
        
        return all_reports
    
    def _scrape_source(self, source_name: str, config: dict, max_items: int, date_range: tuple) -> List[ResearchReport]:
        """爬取单个来源"""
        reports = []
        
        try:
            response = self.session.get(config['url'], timeout=20)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 根据类型选择不同的解析方法
            source_type = config.get('type', 'generic')
            
            if source_type == 'consulting':
                items = self._parse_consulting_site(soup, source_name, config['url'])
            elif source_type == 'research_cn':
                items = self._parse_cn_research_site(soup, source_name, config['url'])
            elif source_type == 'vc':
                items = self._parse_vc_site(soup, source_name, config['url'])
            elif source_type == 'academic':
                items = self._parse_academic_site(soup, source_name, config['url'])
            else:
                items = self._parse_generic_site(soup, source_name, config['url'])
            
            # 过滤关键词
            keywords = config.get('keywords', [])
            for item in items[:max_items * 2]:
                # 检查标题是否包含关键词
                title_lower = item['title'].lower()
                if any(kw.lower() in title_lower for kw in keywords):
                    # 尝试提取内容
                    if item['url'].startswith('http'):
                        item['key_insights'] = self._extract_insights_from_url(item['url'])
                    
                    report = ResearchReport(
                        title=item['title'],
                        source=source_name,
                        date=item.get('date', datetime.now().strftime('%Y-%m-%d')),
                        keywords=[kw for kw in keywords if kw.lower() in title_lower],
                        pdf_url=item['url'],
                        summary=item.get('summary', ''),
                        key_insights=item.get('key_insights', [])
                    )
                    reports.append(report)
                    
                    if len(reports) >= max_items:
                        break
        
        except Exception as e:
            pass
        
        return reports
    
    def _parse_consulting_site(self, soup, source_name: str, base_url: str) -> List[Dict]:
        """解析咨询公司网站"""
        items = []
        
        # 常见的文章链接选择器
        selectors = [
            'a[href*="/insights/"]',
            'a[href*="/our-insights/"]',
            'a[href*="/article/"]',
            '.insight-item a',
            '.article-link',
            'h3 a', 'h2 a'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            if links:
                break
        
        seen = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 10 or title in seen:
                continue
            
            seen.add(title)
            
            if href.startswith('/'):
                href = '/'.join(base_url.split('/')[:3]) + href
            elif not href.startswith('http'):
                continue
            
            items.append({
                'title': title,
                'url': href,
                'date': datetime.now().strftime('%Y-%m-%d')
            })
        
        return items
    
    def _parse_cn_research_site(self, soup, source_name: str, base_url: str) -> List[Dict]:
        """解析国内研究机构网站"""
        items = []
        
        selectors = [
            'a[href*="/report/"]',
            'a[href*="/article/"]',
            '.report-item a',
            '.article-item a',
            'h3 a', 'h2 a'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            if links:
                break
        
        seen = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5 or title in seen:
                continue
            
            # 过滤导航链接
            if any(x in title for x in ['登录', '注册', '首页', '更多', '下载']):
                continue
            
            seen.add(title)
            
            if href.startswith('/'):
                href = '/'.join(base_url.split('/')[:3]) + href
            elif not href.startswith('http'):
                continue
            
            items.append({
                'title': title,
                'url': href,
                'date': datetime.now().strftime('%Y-%m-%d')
            })
        
        return items
    
    def _parse_vc_site(self, soup, source_name: str, base_url: str) -> List[Dict]:
        """解析投资机构网站"""
        items = []
        
        selectors = [
            'a[href*="/article/"]',
            'a[href*="/post/"]',
            '.article-card a',
            'h3 a', 'h2 a'
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            if links:
                break
        
        seen = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 10 or title in seen:
                continue
            
            seen.add(title)
            
            if href.startswith('/'):
                href = '/'.join(base_url.split('/')[:3]) + href
            elif not href.startswith('http'):
                continue
            
            items.append({
                'title': title,
                'url': href,
                'date': datetime.now().strftime('%Y-%m-%d')
            })
        
        return items
    
    def _parse_academic_site(self, soup, source_name: str, base_url: str) -> List[Dict]:
        """解析学术网站（arXiv）"""
        items = []
        
        # arXiv 特定选择器
        links = soup.select('dt a[title="Abstract"], a[href*="/abs/"]')
        
        seen = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 10 or title in seen:
                continue
            
            seen.add(title)
            
            if href.startswith('/'):
                href = 'https://arxiv.org' + href
            
            items.append({
                'title': title,
                'url': href,
                'date': datetime.now().strftime('%Y-%m-%d')
            })
        
        return items
    
    def _parse_generic_site(self, soup, source_name: str, base_url: str) -> List[Dict]:
        """通用解析方法"""
        items = []
        links = soup.select('a')
        
        seen = set()
        for link in links[:30]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 10 or title in seen:
                continue
            
            seen.add(title)
            
            if href.startswith('/'):
                href = '/'.join(base_url.split('/')[:3]) + href
            elif not href.startswith('http'):
                continue
            
            items.append({
                'title': title,
                'url': href,
                'date': datetime.now().strftime('%Y-%m-%d')
            })
        
        return items
    
    def _extract_insights_from_url(self, url: str) -> List[str]:
        """从文章URL提取关键观点"""
        try:
            response = self.session.get(url, timeout=15)
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
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    for tag in content_elem.find_all(['script', 'style', 'nav', 'aside']):
                        tag.decompose()
                    
                    text = content_elem.get_text(separator='\n')
                    
                    # 提取关键段落
                    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
                    
                    insights = []
                    for para in paragraphs:
                        # 选择有价值的段落
                        if 50 < len(para) < 500:
                            # 包含数字、百分比、预测等
                            if re.search(r'[%$¥]|\d+[\.\d]*[亿万千百]|预计|预测|增长|下降|将达到', para):
                                insights.append(para)
                                if len(insights) >= 3:
                                    break
                    
                    return insights
            
        except Exception as e:
            pass
        
        return []


class ResearchDiscovery:
    """研究内容发现器"""
    
    # 研报来源网站
    REPORT_SOURCES = {
        '券商研报': {
            '东吴证券': 'https://www.dwzq.com.cn/report/',
            '华泰证券': 'https://www.htsc.com.cn/research/',
            '中信证券': 'http://researchreport.citics.com/',
            '国泰君安': 'https://www.gtja.com/research/',
        },
        '咨询机构': {
            '麦肯锡': 'https://www.mckinsey.com/industries/automotive-and-assembly/our-insights',
            '波士顿咨询': 'https://www.bcg.com/industries/automotive',
            '贝恩资本': 'https://www.bain.com/insights/',
            '普华永道': 'https://www.pwc.com/us/en/industries/technology.html',
        },
        '投资机构': {
            'a16z': 'https://a16z.com/ai/',
            '红杉资本': 'https://www.sequoiacap.com/article/',
            '光速资本': 'https://lightspeedvp.com/perspectives/',
        }
    }
    
    # 专家访谈来源
    EXPERT_SOURCES = {
        '技术博客': {
            'Andrej Karpathy': 'https://karpathy.github.io/',
            'Andrew Ng': 'https://www.deeplearning.ai/blog/',
            'OpenAI Blog': 'https://openai.com/blog/',
            'Anthropic Blog': 'https://www.anthropic.com/news',
            'Google AI Blog': 'https://blog.google/technology/ai/',
            'Meta AI Blog': 'https://ai.meta.com/blog/',
        },
        '媒体访谈': {
            'The Information': 'https://www.theinformation.com/',
            'Wired': 'https://www.wired.com/tag/artificial-intelligence/',
            'MIT Tech Review': 'https://www.technologyreview.com/topic/artificial-intelligence/',
        },
        '播客访谈': {
            'Lex Fridman': 'https://lexfridman.com/podcast/',
            'a16z Podcast': 'https://a16z.com/podcasts/',
        }
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def discover_reports(self, keywords: List[str] = None) -> List[ResearchReport]:
        """
        发现相关研报
        返回研报列表供用户选择
        """
        if keywords is None:
            keywords = ['自动驾驶', 'AI', '人工智能', '大模型', 'robotaxi', 'autonomous']
        
        reports = []
        
        console.print("\n[yellow]正在搜索相关研报...[/yellow]")
        
        # 搜索咨询机构报告
        for category, sources in self.REPORT_SOURCES.items():
            for name, url in sources.items():
                try:
                    found = self._search_site_for_reports(name, url, keywords)
                    reports.extend(found)
                except Exception as e:
                    console.print(f"[dim]搜索 {name} 失败: {e}[/dim]")
        
        return reports
    
    def discover_expert_opinions(self, keywords: List[str] = None) -> List[Dict]:
        """
        发现相关专家访谈
        返回访谈列表供用户选择
        """
        if keywords is None:
            keywords = ['AI', '自动驾驶', 'LLM', 'AGI', 'autonomous', 'interview']
        
        opinions = []
        
        console.print("\n[yellow]正在搜索专家访谈...[/yellow]")
        
        for category, sources in self.EXPERT_SOURCES.items():
            for name, url in sources.items():
                try:
                    found = self._search_site_for_expert_content(name, url, keywords)
                    opinions.extend(found)
                except Exception as e:
                    console.print(f"[dim]搜索 {name} 失败: {e}[/dim]")
        
        return opinions
    
    def _search_site_for_reports(self, source_name: str, base_url: str, keywords: List[str]) -> List[ResearchReport]:
        """搜索单个站点的研报"""
        reports = []
        
        try:
            response = self.session.get(base_url, timeout=15)
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 查找包含关键词的链接
            links = soup.find_all('a', href=True)
            
            for link in links[:30]:
                title = link.get_text(strip=True)
                href = link.get('href', '')
                
                # 检查是否包含关键词
                title_lower = title.lower()
                if not any(kw.lower() in title_lower for kw in keywords):
                    continue
                
                if len(title) < 10:
                    continue
                
                # 构建完整URL
                if href.startswith('/'):
                    href = base_url.rstrip('/') + href
                elif not href.startswith('http'):
                    continue
                
                report = ResearchReport(
                    title=title,
                    source=source_name,
                    date=datetime.now().strftime('%Y-%m-%d'),
                    keywords=[kw for kw in keywords if kw.lower() in title_lower],
                    pdf_url=href
                )
                reports.append(report)
        
        except Exception as e:
            pass
        
        return reports[:5]  # 每个来源最多5个
    
    def _search_site_for_expert_content(self, source_name: str, base_url: str, keywords: List[str]) -> List[Dict]:
        """搜索专家内容"""
        contents = []
        
        try:
            response = self.session.get(base_url, timeout=15)
            soup = BeautifulSoup(response.text, 'lxml')
            
            links = soup.find_all('a', href=True)
            
            for link in links[:30]:
                title = link.get_text(strip=True)
                href = link.get('href', '')
                
                title_lower = title.lower()
                if not any(kw.lower() in title_lower for kw in keywords):
                    continue
                
                if len(title) < 15:
                    continue
                
                if href.startswith('/'):
                    href = base_url.rstrip('/') + href
                elif not href.startswith('http'):
                    continue
                
                contents.append({
                    'title': title,
                    'source': source_name,
                    'url': href,
                    'date': datetime.now().strftime('%Y-%m-%d')
                })
        
        except Exception as e:
            pass
        
        return contents[:5]
    
    def display_reports(self, reports: List[ResearchReport]):
        """显示研报列表"""
        if not reports:
            console.print("[yellow]未找到相关研报[/yellow]")
            return
        
        table = Table(title="相关研报列表")
        table.add_column("序号", style="cyan", width=5)
        table.add_column("标题", style="white", width=50)
        table.add_column("来源", style="green", width=15)
        table.add_column("关键词", style="yellow", width=20)
        
        for i, report in enumerate(reports, 1):
            table.add_row(
                str(i),
                report.title[:50] + ("..." if len(report.title) > 50 else ""),
                report.source,
                ", ".join(report.keywords[:3])
            )
        
        console.print(table)
        console.print(f"\n[cyan]共找到 {len(reports)} 份研报[/cyan]")
        console.print("[dim]请根据上述列表，找到PDF文件并输入路径[/dim]")
    
    def display_expert_opinions(self, opinions: List[Dict]):
        """显示专家访谈列表"""
        if not opinions:
            console.print("[yellow]未找到相关专家访谈[/yellow]")
            return
        
        table = Table(title="专家访谈/文章列表")
        table.add_column("序号", style="cyan", width=5)
        table.add_column("标题", style="white", width=50)
        table.add_column("来源", style="green", width=15)
        table.add_column("链接", style="blue", width=40)
        
        for i, op in enumerate(opinions, 1):
            table.add_row(
                str(i),
                op['title'][:50] + ("..." if len(op['title']) > 50 else ""),
                op['source'],
                op['url'][:40] + "..."
            )
        
        console.print(table)
        console.print(f"\n[cyan]共找到 {len(opinions)} 篇专家内容[/cyan]")
        console.print("[dim]请选择感兴趣的链接，输入完整URL[/dim]")


class ContentExtractor:
    """内容提取器 - 提取原文观点"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract_from_pdf(self, pdf_path: str) -> Dict:
        """
        从PDF提取原文观点和图片
        """
        console.print(f"[cyan]正在提取PDF内容: {pdf_path}[/cyan]")
        
        result = {
            'title': '',
            'source': '',
            'key_quotes': [],  # 原文引用
            'images': [],  # 图片路径
            'success': False
        }
        
        try:
            # 尝试使用 PyMuPDF 提取
            try:
                import fitz  # PyMuPDF
                
                doc = fitz.open(pdf_path)
                text_content = []
                
                for page_num, page in enumerate(doc):
                    # 提取文本
                    text = page.get_text()
                    text_content.append(text)
                    
                    # 提取图片
                    images = page.get_images()
                    for img_index, img in enumerate(images):
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # 保存图片
                        img_dir = os.path.join(os.path.dirname(pdf_path), 'images')
                        os.makedirs(img_dir, exist_ok=True)
                        img_path = os.path.join(img_dir, f'page{page_num+1}_img{img_index+1}.png')
                        
                        with open(img_path, 'wb') as f:
                            f.write(image_bytes)
                        
                        result['images'].append(img_path)
                
                full_text = '\n'.join(text_content)
                result['key_quotes'] = self._extract_key_quotes(full_text)
                result['success'] = True
                
                doc.close()
                
            except ImportError:
                # 如果没有 PyMuPDF，提示用户安装
                console.print("[yellow]需要安装 PyMuPDF 来处理PDF: pip install PyMuPDF[/yellow]")
                console.print("[cyan]或者请直接粘贴PDF中的原文内容[/cyan]")
                result['success'] = False
        
        except Exception as e:
            console.print(f"[red]PDF提取失败: {e}[/red]")
        
        return result
    
    def extract_from_url(self, url: str) -> ExpertOpinion:
        """
        从网页提取专家观点原文
        """
        console.print(f"[cyan]正在提取网页内容: {url[:50]}...[/cyan]")
        
        try:
            response = self.session.get(url, timeout=20)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 提取标题
            title = ''
            title_tag = soup.find('h1') or soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)
            
            # 提取正文
            content_selectors = [
                'article',
                '.article-content',
                '.post-content',
                '.entry-content',
                '.content-body',
                'main article',
                '.rich_media_content',  # 微信公众号
            ]
            
            content_text = ""
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # 清理
                    for tag in content_elem.find_all(['script', 'style', 'nav', 'aside']):
                        tag.decompose()
                    content_text = content_elem.get_text(separator='\n')
                    break
            
            # 提取原文引用
            key_quotes = self._extract_key_quotes(content_text)
            
            # 提取专家信息
            expert_name = self._extract_expert_name(soup, title)
            position = self._extract_position(soup)
            
            return ExpertOpinion(
                title=title,
                expert=expert_name,
                position=position,
                source=url.split('/')[2],  # 域名
                url=url,
                date=datetime.now().strftime('%Y-%m-%d'),
                key_quotes=key_quotes
            )
            
        except Exception as e:
            console.print(f"[red]网页提取失败: {e}[/red]")
            return None
    
    def _extract_key_quotes(self, text: str) -> List[str]:
        """
        提取关键原文引用
        原则：必须是原文，不总结
        """
        quotes = []
        
        # 按段落分割
        paragraphs = text.split('\n')
        
        # 关键词权重
        high_value_keywords = [
            '我认为', '我们预计', '预计到', '预计', '将达到', '超过',
            'I think', 'I believe', 'we expect', 'will reach',
            '关键', '核心', '重点', '突破', '创新',
            'first', 'largest', 'most important',
            '$', '亿', 'million', 'billion',
        ]
        
        for para in paragraphs:
            para = para.strip()
            
            # 跳过太短或太长的段落
            if len(para) < 30 or len(para) > 500:
                continue
            
            # 检查是否包含高价值关键词
            has_keyword = any(kw.lower() in para.lower() for kw in high_value_keywords)
            
            if has_keyword:
                quotes.append(para)
                
                if len(quotes) >= 10:  # 最多10条
                    break
        
        return quotes
    
    def _extract_expert_name(self, soup, title: str) -> str:
        """提取专家姓名"""
        # 从作者标签提取
        author_tag = soup.find(class_=re.compile(r'author|byline', re.I))
        if author_tag:
            return author_tag.get_text(strip=True)
        
        # 从标题提取常见名字
        common_names = ['Karpathy', 'Ng', 'Altman', 'Amodei', 'Hinton', 'LeCun', 
                       'Bengio', 'Musk', 'Pichai', 'Nadella']
        for name in common_names:
            if name in title:
                return name
        
        return ""
    
    def _extract_position(self, soup) -> str:
        """提取职位"""
        # 尝试从meta标签提取
        meta = soup.find('meta', attrs={'name': 'author'})
        if meta:
            return meta.get('content', '')
        return ""


class ResearchViewFormatter:
    """研究观点格式化器"""
    
    def format_research_section(self, items: List[Dict]) -> str:
        """格式化研究观点摘录部分"""
        if not items:
            return ""
        
        md = "## 研究观点摘录\n\n"
        
        for i, item in enumerate(items, 1):
            if 'key_quotes' in item:
                # 专家观点格式
                md += self._format_expert_view(i, item)
            else:
                # 研报格式
                md += self._format_report_view(i, item)
        
        return md
    
    def _format_expert_view(self, index: int, item) -> str:
        """格式化专家观点"""
        md = f"### {index}. {item.title}\n\n"
        
        if item.expert:
            md += f"> {item.expert}"
            if item.position:
                md += f" | {item.position}"
            md += "\n\n"
        
        md += "**核心观点（原文）：**\n\n"
        
        for i, quote in enumerate(item.key_quotes, 1):
            md += f"> {quote}\n\n"
        
        md += f"来源：[{item.source}]({item.url})\n\n"
        md += "---\n\n"
        
        return md
    
    def _format_report_view(self, index: int, item) -> str:
        """格式化研报观点"""
        md = f"### {index}. {item.get('title', '')}\n\n"
        
        if item.get('source'):
            md += f"> 来源：{item['source']}\n\n"
        
        md += "**核心观点（原文）：**\n\n"
        
        for i, quote in enumerate(item.get('key_quotes', []), 1):
            md += f"> {quote}\n\n"
        
        # 图片
        for img_path in item.get('images', []):
            if os.path.exists(img_path):
                md += f"![图表]({img_path})\n\n"
        
        md += "---\n\n"
        
        return md


# 交互式入口
def interactive_research_input():
    """交互式研究内容输入"""
    console.print("\n[bold cyan]===== 研究观点摘录 =====[/bold cyan]\n")
    
    discovery = ResearchDiscovery()
    extractor = ContentExtractor()
    
    # 询问用户类型
    console.print("请选择输入类型：")
    console.print("1. 自动搜索研报/专家访谈")
    console.print("2. 手动输入研报PDF路径")
    console.print("3. 手动输入专家访谈URL")
    console.print("4. 直接粘贴原文内容")
    
    choice = console.input("\n请输入选项 [1-4]: ").strip()
    
    results = []
    
    if choice == '1':
        # 自动搜索
        console.print("\n正在搜索相关内容...")
        
        # 搜索研报
        reports = discovery.discover_reports()
        discovery.display_reports(reports)
        
        # 搜索专家访谈
        opinions = discovery.discover_expert_opinions()
        discovery.display_expert_opinions(opinions)
        
        console.print("\n[yellow]请根据上述列表，手动输入PDF路径或URL[/yellow]")
        
    elif choice == '2':
        # 手动输入PDF
        pdf_path = console.input("请输入PDF文件路径: ").strip()
        if os.path.exists(pdf_path):
            result = extractor.extract_from_pdf(pdf_path)
            results.append(result)
        else:
            console.print(f"[red]文件不存在: {pdf_path}[/red]")
    
    elif choice == '3':
        # 手动输入URL
        url = console.input("请输入访谈URL: ").strip()
        result = extractor.extract_from_url(url)
        if result:
            results.append(result)
    
    elif choice == '4':
        # 直接粘贴原文
        console.print("请粘贴原文内容（输入空行结束）:")
        lines = []
        while True:
            line = console.input()
            if not line:
                break
            lines.append(line)
        
        content = '\n'.join(lines)
        key_quotes = extractor._extract_key_quotes(content)
        
        title = console.input("请输入标题: ").strip()
        source = console.input("请输入来源: ").strip()
        
        results.append({
            'title': title,
            'source': source,
            'key_quotes': key_quotes
        })
    
    return results


if __name__ == '__main__':
    # 测试
    results = interactive_research_input()
    print(f"\n提取到 {len(results)} 条内容")
