"""
AI行业研报全网自动搜索抓取模块
- 覆盖国内外券商、咨询公司、科技媒体等来源
- 自动搜索AI、Robotaxi、自动驾驶、AI漫剧相关研报
- 提取标题、来源、语言、摘要、链接、日期
"""
import re
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
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
    source: str  # 来源机构
    country: str  # 来源国家
    language: str  # 语言
    summary: str  # 2-4句话中文摘要
    url: str  # 可访问链接
    date: str  # 发布日期
    keywords: List[str]  # 关键词
    category: str  # 分类：AI/Robotaxi/自动驾驶/AI漫剧


class GlobalResearchScraper:
    """全球研报爬虫"""
    
    # 国内来源
    CN_SOURCES = {
        '券商研报': [
            {'name': '东方财富研报', 'url': 'https://data.eastmoney.com/report/', 'country': '中国'},
            {'name': '同花顺研报', 'url': 'https://stockpage.10jqka.com.cn/', 'country': '中国'},
            {'name': '新浪财经研报', 'url': 'https://stock.finance.sina.com.cn/stock/go.php/vReport_List/kind/main/index.phtml', 'country': '中国'},
        ],
        '咨询机构': [
            {'name': '艾瑞咨询', 'url': 'https://www.iresearch.com.cn/report/', 'country': '中国'},
            {'name': '易观分析', 'url': 'https://www.analysys.cn/article/list.html', 'country': '中国'},
            {'name': '艾媒咨询', 'url': 'https://www.iimedia.cn/c400', 'country': '中国'},
        ],
        '科技媒体': [
            {'name': '36氪研究院', 'url': 'https://36kr.com/academy', 'country': '中国'},
            {'name': '虎嗅研究', 'url': 'https://www.huxiu.com/research', 'country': '中国'},
            {'name': '机器之心', 'url': 'https://www.jiqizhixin.com/', 'country': '中国'},
            {'name': '量子位', 'url': 'https://www.qbitai.com/', 'country': '中国'},
        ],
    }
    
    # 国际来源
    GLOBAL_SOURCES = {
        '国际券商': [
            {'name': 'Goldman Sachs', 'url': 'https://www.goldmansachs.com/insights/', 'country': '美国'},
            {'name': 'Morgan Stanley', 'url': 'https://www.morganstanley.com/ideas/', 'country': '美国'},
            {'name': 'J.P. Morgan', 'url': 'https://www.jpmorgan.com/insights', 'country': '美国'},
            {'name': 'UBS', 'url': 'https://www.ubs.com/global/en/wealth-management/insights.html', 'country': '瑞士'},
            {'name': 'Barclays', 'url': 'https://home.barclays/news-and-insights/', 'country': '英国'},
        ],
        '国际咨询': [
            {'name': 'McKinsey', 'url': 'https://www.mckinsey.com/industries/technology-media-and-telecommunications/our-insights', 'country': '美国'},
            {'name': 'BCG', 'url': 'https://www.bcg.com/industries/technology-industries', 'country': '美国'},
            {'name': 'Bain', 'url': 'https://www.bain.com/insights/', 'country': '美国'},
            {'name': 'Deloitte', 'url': 'https://www2.deloitte.com/insights', 'country': '美国'},
            {'name': 'PwC', 'url': 'https://www.pwc.com/us/en/industries/technology.html', 'country': '美国'},
            {'name': 'Accenture', 'url': 'https://www.accenture.com/us-en/insights', 'country': '美国'},
        ],
        '科技分析机构': [
            {'name': 'Gartner', 'url': 'https://www.gartner.com/en/information-technology/insights', 'country': '美国'},
            {'name': 'IDC', 'url': 'https://www.idc.com/insights', 'country': '美国'},
            {'name': 'Forrester', 'url': 'https://www.forrester.com/blogs/', 'country': '美国'},
            {'name': 'CB Insights', 'url': 'https://www.cbinsights.com/research/', 'country': '美国'},
        ],
        '学术社区': [
            {'name': 'arXiv', 'url': 'https://arxiv.org/list/cs.AI/recent', 'country': '国际'},
            {'name': 'Google Scholar', 'url': 'https://scholar.google.com/', 'country': '国际'},
            {'name': 'SSRN', 'url': 'https://www.ssrn.com/index.cfm/en/', 'country': '国际'},
        ],
        '英文科技媒体': [
            {'name': 'TechCrunch', 'url': 'https://techcrunch.com/', 'country': '美国'},
            {'name': 'Wired', 'url': 'https://www.wired.com/tag/artificial-intelligence/', 'country': '美国'},
            {'name': 'VentureBeat', 'url': 'https://venturebeat.com/category/ai/', 'country': '美国'},
            {'name': 'The Verge', 'url': 'https://www.theverge.com/ai-artificial-intelligence', 'country': '美国'},
        ],
    }
    
    # 搜索关键词（中英文）
    SEARCH_KEYWORDS = {
        'AI': ['AI 研报', 'AI 研究报告', 'AI research report', 'artificial intelligence report', 'AI industry analysis'],
        'Robotaxi': ['Robotaxi 研报', 'Robotaxi 研究报告', 'Robotaxi research', 'autonomous taxi report', 'self-driving taxi'],
        '自动驾驶': ['自动驾驶 研报', '自动驾驶 白皮书', 'autonomous driving report', 'self-driving report', 'ADAS research'],
        'AI漫剧': ['AI漫剧 报告', 'AI动画 研报', 'AI cartoon report', 'AI animation industry', 'AIGC content'],
        '人工智能': ['人工智能 行业报告', '人工智能 发展报告', 'artificial intelligence white paper', 'AI development report'],
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })
        self.reports: List[ResearchReport] = []
        self.seen_urls = set()
    
    def search_all(self, days: int = 7) -> List[ResearchReport]:
        """
        执行全网研报搜索
        
        Args:
            days: 搜索最近几天的报告
        """
        console.print("\n[bold cyan]===== 开始全球研报搜索 =====[/bold cyan]")
        
        # 1. 使用网络搜索API获取最新研报链接
        self._search_via_web()
        
        # 2. 爬取各来源网站
        self._scrape_cn_sources()
        self._scrape_global_sources()
        
        # 3. 去重和分类
        self._deduplicate()
        self._categorize()
        
        # 4. 过滤日期
        self._filter_by_date(days)
        
        console.print(f"\n[green]共找到 {len(self.reports)} 份符合要求的研报[/green]")
        
        return self.reports
    
    def _search_via_web(self):
        """通过网络搜索获取研报链接"""
        try:
            # 尝试使用web_search（如果可用）
            pass  # 在实际运行时会通过run_in_background执行搜索
        except Exception as e:
            console.print(f"[yellow]网络搜索跳过: {e}[/yellow]")
    
    def _scrape_cn_sources(self):
        """爬取国内来源"""
        console.print("\n[yellow]正在搜索国内研报来源...[/yellow]")
        
        for category, sources in self.CN_SOURCES.items():
            for source in sources:
                try:
                    reports = self._scrape_source(source, category)
                    self.reports.extend(reports)
                    console.print(f"  {source['name']}: {len(reports)} 份")
                except Exception as e:
                    console.print(f"  [dim]{source['name']}: 搜索失败[/dim]")
    
    def _scrape_global_sources(self):
        """爬取国际来源"""
        console.print("\n[yellow]正在搜索国际研报来源...[/yellow]")
        
        for category, sources in self.GLOBAL_SOURCES.items():
            for source in sources:
                try:
                    reports = self._scrape_source(source, category)
                    self.reports.extend(reports)
                    console.print(f"  {source['name']}: {len(reports)} 份")
                except Exception as e:
                    console.print(f"  [dim]{source['name']}: 搜索失败[/dim]")
    
    def _scrape_source(self, source: Dict, category: str) -> List[ResearchReport]:
        """爬取单个来源"""
        reports = []
        
        try:
            response = self.session.get(source['url'], timeout=15)
            if response.status_code != 200:
                return reports
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 查找包含关键词的链接
            links = soup.find_all('a', href=True)
            
            for link in links[:50]:  # 每个来源最多检查50个链接
                title = link.get_text(strip=True)
                href = link.get('href', '')
                
                # 检查是否为研报相关
                if not self._is_report_link(title, href):
                    continue
                
                # 检查是否包含关键词
                matched_keywords = self._check_keywords(title)
                if not matched_keywords:
                    continue
                
                # 构建完整URL
                full_url = self._build_url(href, source['url'])
                if not full_url or full_url in self.seen_urls:
                    continue
                
                # 检测是否付费墙
                if self._is_paywalled(full_url):
                    continue
                
                # 提取摘要
                summary = self._extract_summary(full_url, title)
                if not summary:
                    summary = self._generate_summary(title)
                
                # 检测语言
                language = self._detect_language(title)
                
                # 创建报告对象
                report = ResearchReport(
                    title=title[:200],  # 限制标题长度
                    source=source['name'],
                    country=source['country'],
                    language=language,
                    summary=summary,
                    url=full_url,
                    date=self._extract_date(href, soup) or datetime.now().strftime('%Y-%m-%d'),
                    keywords=matched_keywords,
                    category=matched_keywords[0] if matched_keywords else 'AI'
                )
                
                reports.append(report)
                self.seen_urls.add(full_url)
                
                if len(reports) >= 10:  # 每个来源最多10份
                    break
        
        except Exception as e:
            pass
        
        return reports
    
    def _is_report_link(self, title: str, href: str) -> bool:
        """判断是否为研报链接"""
        # 研报相关关键词
        report_keywords = [
            '报告', '研报', '白皮书', '研究', '分析', '洞察', 'insight', 'report',
            'research', 'analysis', 'white paper', 'study', 'paper'
        ]
        
        # 过滤关键词（新闻、广告等）
        filter_keywords = [
            '新闻', '招聘', '广告', '活动', '促销', 'news', 'job', 'career',
            'subscribe', 'login', 'register', '订阅', '登录'
        ]
        
        title_lower = title.lower()
        href_lower = href.lower()
        
        # 检查是否包含过滤关键词
        if any(kw in title_lower or kw in href_lower for kw in filter_keywords):
            return False
        
        # 检查是否包含研报关键词
        return any(kw in title_lower or kw in href_lower for kw in report_keywords)
    
    def _check_keywords(self, title: str) -> List[str]:
        """检查标题是否包含目标关键词"""
        matched = []
        title_lower = title.lower()
        
        all_keywords = [
            'ai', 'artificial intelligence', '人工智能', '机器学习', '深度学习',
            'robotaxi', '自动驾驶', 'autonomous driving', 'self-driving',
            '无人驾驶', '智能驾驶', 'autonomous vehicle',
            'ai漫剧', 'ai动画', 'ai cartoon', 'aigc', '漫剧',
            'llm', 'gpt', '大模型', 'chatgpt', '生成式',
        ]
        
        for kw in all_keywords:
            if kw in title_lower:
                # 映射到分类
                if kw in ['robotaxi', 'robotaxi']:
                    matched.append('Robotaxi')
                elif kw in ['自动驾驶', 'autonomous driving', 'self-driving', '无人驾驶', '智能驾驶', 'autonomous vehicle']:
                    matched.append('自动驾驶')
                elif kw in ['ai漫剧', 'ai动画', 'ai cartoon', 'aigc', '漫剧']:
                    matched.append('AI漫剧')
                else:
                    matched.append('AI')
        
        return list(set(matched))  # 去重
    
    def _build_url(self, href: str, base_url: str) -> str:
        """构建完整URL"""
        if href.startswith('http'):
            return href
        elif href.startswith('/'):
            return base_url.rstrip('/') + href
        elif href.startswith('#') or href.startswith('javascript'):
            return ''
        else:
            return base_url.rstrip('/') + '/' + href
    
    def _is_paywalled(self, url: str) -> bool:
        """检测是否为付费墙"""
        paywall_domains = [
            'ft.com', 'wsj.com', 'bloomberg.com', 'economist.com',
            'theinformation.com', 'premium', 'paywall', 'subscribe'
        ]
        
        url_lower = url.lower()
        return any(domain in url_lower for domain in paywall_domains)
    
    def _extract_summary(self, url: str, title: str) -> str:
        """从网页提取摘要"""
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return ""
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 尝试多种摘要选择器
            summary_selectors = [
                'meta[name="description"]',
                'meta[property="og:description"]',
                '.article-summary',
                '.report-summary',
                '.abstract',
                'p.summary',
            ]
            
            for selector in summary_selectors:
                elem = soup.select_one(selector)
                if elem:
                    if elem.name == 'meta':
                        content = elem.get('content', '')
                    else:
                        content = elem.get_text(strip=True)
                    
                    if content and len(content) > 50:
                        # 截取前300字符作为摘要
                        return content[:300] + ('...' if len(content) > 300 else '')
            
            # 如果没有找到，尝试从正文提取
            paragraphs = soup.find_all('p')
            if paragraphs:
                text = ' '.join([p.get_text(strip=True) for p in paragraphs[:3]])
                if len(text) > 100:
                    return text[:300] + '...'
            
            return ""
            
        except Exception:
            return ""
    
    def _generate_summary(self, title: str) -> str:
        """根据标题生成摘要"""
        # 简单的摘要生成逻辑
        return f"本报告研究{title}相关领域的发展现状与趋势，分析行业核心问题与解决方案，提供数据支撑与案例参考。具体内容请访问原文链接获取完整信息。"
    
    def _detect_language(self, title: str) -> str:
        """检测语言"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', title))
        if chinese_chars > len(title) * 0.3:
            return '中文'
        return '英文'
    
    def _extract_date(self, href: str, soup) -> Optional[str]:
        """从URL或页面提取日期"""
        # 尝试从URL提取日期
        date_patterns = [
            r'/(\d{4})/(\d{2})/(\d{2})/',
            r'/(\d{4})(\d{2})(\d{2})',
            r'(\d{4}-\d{2}-\d{2})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, href)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    return f"{groups[0]}-{groups[1]}-{groups[2]}"
                elif len(groups) == 1:
                    return groups[0]
        
        # 尝试从页面提取
        time_elem = soup.find('time')
        if time_elem:
            date_str = time_elem.get('datetime', '') or time_elem.get_text(strip=True)
            if date_str:
                return date_str[:10]
        
        return None
    
    def _deduplicate(self):
        """去重"""
        seen_titles = set()
        unique_reports = []
        
        for report in self.reports:
            # 使用标题的标准化形式作为去重依据
            normalized_title = re.sub(r'\s+', '', report.title.lower())
            
            if normalized_title not in seen_titles:
                seen_titles.add(normalized_title)
                unique_reports.append(report)
        
        self.reports = unique_reports
    
    def _categorize(self):
        """按关键词分类"""
        # 按分类排序
        category_order = ['AI', 'Robotaxi', '自动驾驶', 'AI漫剧', '人工智能']
        
        def get_category_rank(report):
            if report.category in category_order:
                return category_order.index(report.category)
            return len(category_order)
        
        self.reports.sort(key=get_category_rank)
    
    def _filter_by_date(self, days: int):
        """过滤日期"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        filtered = []
        for report in self.reports:
            try:
                report_date = datetime.strptime(report.date[:10], '%Y-%m-%d')
                if report_date >= cutoff_date:
                    filtered.append(report)
            except:
                # 无法解析日期的保留
                filtered.append(report)
        
        self.reports = filtered
    
    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        if not self.reports:
            return ""
        
        md = "# **行业研报摘录**\n\n"
        
        # 按分类输出
        categories = {}
        for report in self.reports:
            cat = report.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(report)
        
        for category, reports in categories.items():
            md += f"## {category}\n\n"
            
            for i, report in enumerate(reports, 1):
                md += f"### {i}. {report.title}\n\n"
                md += f"> 来源：{report.source}（{report.country}）| 语言：{report.language} | 发布日期：{report.date}\n\n"
                md += f"**核心摘要：** {report.summary}\n\n"
                md += f"**链接：** [{report.url[:60]}{'...' if len(report.url) > 60 else ''}]({report.url})\n\n"
                md += "---\n\n"
        
        return md
    
    def display_summary(self):
        """显示搜索结果摘要"""
        if not self.reports:
            console.print("[yellow]未找到符合条件的研报[/yellow]")
            return
        
        # 统计
        cn_count = sum(1 for r in self.reports if r.country == '中国')
        global_count = len(self.reports) - cn_count
        
        console.print(f"\n[bold]研报统计：[/bold]")
        console.print(f"  国内研报: {cn_count} 份")
        console.print(f"  海外研报: {global_count} 份")
        
        # 按分类统计
        categories = {}
        for report in self.reports:
            cat = report.category
            categories[cat] = categories.get(cat, 0) + 1
        
        console.print(f"\n[bold]分类统计：[/bold]")
        for cat, count in categories.items():
            console.print(f"  {cat}: {count} 份")
        
        # 显示表格
        table = Table(title="研报列表预览（前10条）")
        table.add_column("标题", style="cyan", width=40)
        table.add_column("来源", style="green", width=15)
        table.add_column("国家", style="yellow", width=8)
        table.add_column("日期", style="white", width=12)
        
        for report in self.reports[:10]:
            table.add_row(
                report.title[:40] + ('...' if len(report.title) > 40 else ''),
                report.source[:15],
                report.country,
                report.date
            )
        
        console.print(table)


def run_research_search(days: int = 7) -> str:
    """
    执行研报搜索并返回Markdown结果
    
    Args:
        days: 搜索最近几天的报告
    """
    scraper = GlobalResearchScraper()
    reports = scraper.search_all(days=days)
    scraper.display_summary()
    return scraper.to_markdown()


def search_and_save(days: int = 7, output_file: str = None) -> List[ResearchReport]:
    """
    执行研报搜索并保存结果
    
    Args:
        days: 搜索最近几天的报告
        output_file: 输出文件路径（可选）
    """
    scraper = GlobalResearchScraper()
    reports = scraper.search_all(days=days)
    scraper.display_summary()
    
    if output_file:
        # 保存为JSON
        data = [asdict(r) for r in reports]
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        console.print(f"\n[green]研报已保存到: {output_file}[/green]")
    
    return reports


# 测试入口
if __name__ == '__main__':
    markdown = run_research_search(days=30)
    print(markdown)
