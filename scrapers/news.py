"""
新闻媒体网站爬虫模块
抓取财新、36氪、第一财经等新闻媒体
"""
from typing import List, Dict
from datetime import datetime
from core import BaseScraper, NewsItem, console


class NewsScraper(BaseScraper):
    """新闻媒体爬虫"""
    
    def scrape(self) -> List[NewsItem]:
        """爬取所有配置的新闻网站"""
        if not self.config.get('sources.news.enabled', False):
            return []
        
        items = []
        sites = self.config.get('sources.news.sites', [])
        
        for site in sites:
            console.print(f"[cyan]正在爬取: {site['name']}...[/cyan]")
            try:
                site_items = self._scrape_site(site)
                items.extend(site_items)
                console.print(f"[green]获取 {len(site_items)} 条新闻[/green]")
            except Exception as e:
                console.print(f"[red]爬取 {site['name']} 失败: {e}[/red]")
        
        return items
    
    def _scrape_site(self, site: Dict) -> List[NewsItem]:
        """爬取单个新闻网站"""
        items = []
        html = self.fetch_page(site['url'])
        if not html:
            return items
        
        soup = self.parse_html(html)
        
        # 根据网站选择不同的解析方法
        site_name = site['name'].lower()
        
        if '财新' in site_name or 'caixin' in site_name:
            items = self._parse_caixin(soup, site)
        elif '36氪' in site_name or '36kr' in site_name:
            items = self._parse_36kr(soup, site)
        elif '第一财经' in site_name or 'yicai' in site_name:
            items = self._parse_yicai(soup, site)
        elif '虎嗅' in site_name or 'huxiu' in site_name:
            items = self._parse_huxiu(soup, site)
        elif '钛媒体' in site_name or 'tmtpost' in site_name:
            items = self._parse_tmtpost(soup, site)
        elif '机器之心' in site_name or 'jiqizhixin' in site_name:
            items = self._parse_jiqizhixin(soup, site)
        elif '量子位' in site_name or 'qbitai' in site_name:
            items = self._parse_qbitai(soup, site)
        elif '新浪科技' in site_name or 'sina' in site_name:
            items = self._parse_sina_tech(soup, site)
        elif 'techcrunch' in site_name:
            items = self._parse_techcrunch(soup, site)
        elif 'reuters' in site_name:
            items = self._parse_reuters(soup, site)
        elif 'business insider' in site_name:
            items = self._parse_business_insider(soup, site)
        elif 'the information' in site_name:
            items = self._parse_the_information(soup, site)
        elif 'driverless report' in site_name:
            items = self._parse_driverless_report(soup, site)
        elif 'av america' in site_name:
            items = self._parse_av_america(soup, site)
        elif 'autonomous vehicles ai' in site_name:
            items = self._parse_av_ai(soup, site)
        elif 'emove360' in site_name:
            items = self._parse_emove360(soup, site)
        else:
            items = self._parse_generic(soup, site)
        
        # 过滤已缓存的条目
        new_items = []
        for item in items:
            if not self.cache.exists(item):
                self.cache.save(item)
                new_items.append(item)
        
        return new_items
    
    def _parse_caixin(self, soup, site: Dict) -> List[NewsItem]:
        """解析财新网"""
        items = []
        # 财新网的新闻列表结构
        links = soup.select('.news-item a, .article-item a, h3 a, .tit a')
        
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5:
                continue
            
            if href.startswith('/'):
                href = f"https://www.caixin.com{href}"
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="news"
            )
            items.append(item)
        
        return items
    
    def _parse_36kr(self, soup, site: Dict) -> List[NewsItem]:
        """解析36氪"""
        items = []
        # 36氪的新闻结构 - 更新选择器
        links = soup.select('a[href*="/p/"], .article-item-title a, .newsflow-item a, a.article-title, h3 a, h2 a')
        
        seen_urls = set()
        for link in links[:30]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5:
                continue
            
            # 36氪的链接可能是相对路径
            if href.startswith('//'):
                href = f"https:{href}"
            elif href.startswith('/'):
                href = f"https://36kr.com{href}"
            elif not href.startswith('http'):
                continue
            
            # 去重
            if href in seen_urls:
                continue
            seen_urls.add(href)
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="news",
                keywords=["科技", "创投"]
            )
            items.append(item)
        
        return items
    
    def _parse_yicai(self, soup, site: Dict) -> List[NewsItem]:
        """解析第一财经"""
        items = []
        # 第一财经 - 更新选择器，尝试多种方式
        links = soup.select('a[href*="/news/"], a[href*="/economy/"], .news-item a, .list-item a, h2 a, .title a, h3 a')
        
        seen_urls = set()
        for link in links[:30]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5:
                continue
            
            # 过滤导航链接
            if any(x in title.lower() for x in ['登录', '注册', '订阅', '广告', '首页']):
                continue
            
            if href.startswith('/'):
                href = f"https://www.yicai.com{href}"
            elif not href.startswith('http'):
                continue
            
            # 去重
            if href in seen_urls:
                continue
            seen_urls.add(href)
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="news",
                keywords=["财经", "经济"]
            )
            items.append(item)
        
        return items
    
    def _parse_techcrunch(self, soup, site: Dict) -> List[NewsItem]:
        """解析 TechCrunch"""
        items = []
        # TechCrunch 文章标题在 h3 标签中
        links = soup.select('h3 a, .article-title a, a[href*="/202"]')
        
        seen_titles = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 10 or title in seen_titles:
                continue
            
            seen_titles.add(title)
            
            if href.startswith('/'):
                href = f"https://techcrunch.com{href}"
            elif not href.startswith('http'):
                continue
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="news",
                keywords=["科技", "创业", "硅谷"]
            )
            items.append(item)
        
        return items
    
    def _parse_reuters(self, soup, site: Dict) -> List[NewsItem]:
        """解析 Reuters"""
        items = []
        # Reuters 新闻链接
        links = soup.select('a[href*="/article/"], a[href*="/technology/"], h3 a')
        
        seen_titles = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 15 or title in seen_titles:
                continue
            
            # 过滤导航链接
            if title.lower() in ['technology', 'world', 'business', 'markets']:
                continue
            
            seen_titles.add(title)
            
            if href.startswith('/'):
                href = f"https://www.reuters.com{href}"
            elif not href.startswith('http'):
                continue
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="news",
                keywords=["科技", "国际"]
            )
            items.append(item)
        
        return items
    
    def _parse_business_insider(self, soup, site: Dict) -> List[NewsItem]:
        """解析 Business Insider"""
        items = []
        # Business Insider 文章
        links = soup.select('h2 a, h3 a, a[href*="/article/"], .tout-title a')
        
        seen_titles = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 10 or title in seen_titles:
                continue
            
            # 过滤重复标题
            if 'Business Insider tells the innovative stories' in title:
                continue
            
            seen_titles.add(title)
            
            if href.startswith('/'):
                href = f"https://www.businessinsider.com{href}"
            elif not href.startswith('http'):
                continue
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="news",
                keywords=["商业", "科技"]
            )
            items.append(item)
        
        return items
    
    def _parse_the_information(self, soup, site: Dict) -> List[NewsItem]:
        """解析 The Information"""
        items = []
        # The Information 文章标题在 h3 标签中
        links = soup.select('h3 a, .article-title a, a[href*="/articles/"], a[href*="/briefings/"]')
        
        seen_titles = set()
        for link in links[:25]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 15 or title in seen_titles:
                continue
            
            # 过滤导航和广告链接
            skip_keywords = ['subscribe', 'sign in', 'pro', 'about', 'start your subscription',
                           'save 25%', 'learn more', 'view all', 'contact', 'careers']
            if any(x in title.lower() for x in skip_keywords):
                continue
            
            seen_titles.add(title)
            
            if href.startswith('/'):
                href = f"https://www.theinformation.com{href}"
            elif not href.startswith('http'):
                continue
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="news",
                keywords=["科技", "硅谷", "深度"]
            )
            items.append(item)
        
        return items
    
    def _parse_driverless_report(self, soup, site: Dict) -> List[NewsItem]:
        """解析 Driverless Report"""
        items = []
        # WordPress 网站结构
        links = soup.select('article h3 a, .entry-title a, h3 a')
        
        seen_titles = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 10 or title in seen_titles:
                continue
            
            seen_titles.add(title)
            
            if href.startswith('/'):
                href = f"https://www.driverlessreport.com{href}"
            elif not href.startswith('http'):
                continue
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="news",
                keywords=["自动驾驶", "无人车"]
            )
            items.append(item)
        
        return items
    
    def _parse_av_america(self, soup, site: Dict) -> List[NewsItem]:
        """解析 AV America"""
        items = []
        # 简单的标题链接结构
        links = soup.select('h3 a, h2 a, .entry-title a')
        
        seen_titles = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 10 or title in seen_titles:
                continue
            
            # 过滤广告链接
            if 'sponsored' in title.lower() or 'advertise' in title.lower():
                continue
            
            seen_titles.add(title)
            
            if href.startswith('/'):
                href = f"https://avamerica.org{href}"
            elif not href.startswith('http'):
                continue
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="news",
                keywords=["自动驾驶", "美国"]
            )
            items.append(item)
        
        return items
    
    def _parse_av_ai(self, soup, site: Dict) -> List[NewsItem]:
        """解析 Autonomous Vehicles AI"""
        items = []
        # 标题在 h2 标签中
        links = soup.select('h2 a, h3 a, .entry-title a')
        
        seen_titles = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 10 or title in seen_titles:
                continue
            
            seen_titles.add(title)
            
            if href.startswith('/'):
                href = f"https://autonomous-vehicles.ai{href}"
            elif not href.startswith('http'):
                continue
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="news",
                keywords=["自动驾驶", "AI"]
            )
            items.append(item)
        
        return items
    
    def _parse_emove360(self, soup, site: Dict) -> List[NewsItem]:
        """解析 eMove360 AI & Automated Driving"""
        items = []
        # 尝试多种选择器
        links = soup.select('a[href*="/20"]')
        
        seen_titles = set()
        for link in links[:30]:
            # 尝试从链接文本或图片alt属性获取标题
            title = link.get_text(strip=True)
            if not title:
                img = link.find('img')
                if img:
                    title = img.get('alt', '') or img.get('title', '')
            
            href = link.get('href', '')
            
            if not title or len(title) < 15 or title in seen_titles:
                continue
            
            # 过滤非文章链接
            if not any(x in href for x in ['/2024', '/2025', '/2026']):
                continue
            
            seen_titles.add(title)
            
            if href.startswith('/'):
                href = f"https://www.emove360.com{href}"
            elif not href.startswith('http'):
                continue
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="news",
                keywords=["自动驾驶", "AI", "欧洲"]
            )
            items.append(item)
        
        return items
    
    def _parse_generic(self, soup, site: Dict) -> List[NewsItem]:
        """通用解析方法"""
        items = []
        links = soup.select('a')
        
        seen_titles = set()
        for link in links[:25]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 10 or title in seen_titles:
                continue
            
            seen_titles.add(title)
            
            base_url = '/'.join(site['url'].split('/')[:3])
            if href.startswith('/'):
                href = base_url + href
            elif not href.startswith('http'):
                continue
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="news"
            )
            items.append(item)
        
        return items
    
    def _parse_huxiu(self, soup, site: Dict) -> List[NewsItem]:
        """解析虎嗅"""
        items = []
        links = soup.select('a[href*="/article/"], .article-item a, h3 a, h2 a')
        
        seen_urls = set()
        for link in links[:30]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5:
                continue
            
            if href.startswith('/'):
                href = f"https://www.huxiu.com{href}"
            elif not href.startswith('http'):
                continue
            
            if href in seen_urls:
                continue
            seen_urls.add(href)
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="news",
                keywords=["科技", "商业"]
            )
            items.append(item)
        
        return items
    
    def _parse_tmtpost(self, soup, site: Dict) -> List[NewsItem]:
        """解析钛媒体"""
        items = []
        links = soup.select('a[href*="/article/"], .article-title a, h3 a, h2 a')
        
        seen_urls = set()
        for link in links[:30]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5:
                continue
            
            if href.startswith('/'):
                href = f"https://www.tmtpost.com{href}"
            elif not href.startswith('http'):
                continue
            
            if href in seen_urls:
                continue
            seen_urls.add(href)
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="news",
                keywords=["科技", "创投"]
            )
            items.append(item)
        
        return items
    
    def _parse_jiqizhixin(self, soup, site: Dict) -> List[NewsItem]:
        """解析机器之心"""
        items = []
        links = soup.select('a[href*="/news/"], a[href*="/article/"], .article-title a, h3 a')
        
        seen_urls = set()
        for link in links[:30]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5:
                continue
            
            if href.startswith('/'):
                href = f"https://www.jiqizhixin.com{href}"
            elif not href.startswith('http'):
                continue
            
            if href in seen_urls:
                continue
            seen_urls.add(href)
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="news",
                keywords=["AI", "人工智能", "机器学习"]
            )
            items.append(item)
        
        return items
    
    def _parse_qbitai(self, soup, site: Dict) -> List[NewsItem]:
        """解析量子位"""
        items = []
        links = soup.select('a[href*="/article/"], .article-title a, h3 a, h2 a')
        
        seen_urls = set()
        for link in links[:30]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5:
                continue
            
            if href.startswith('/'):
                href = f"https://www.qbitai.com{href}"
            elif not href.startswith('http'):
                continue
            
            if href in seen_urls:
                continue
            seen_urls.add(href)
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="news",
                keywords=["AI", "量子计算", "人工智能"]
            )
            items.append(item)
        
        return items
    
    def _parse_sina_tech(self, soup, site: Dict) -> List[NewsItem]:
        """解析新浪科技"""
        items = []
        links = soup.select('a[href*="/doc/"], a[href*="/article/"], .news-item a, h2 a, h3 a')
        
        seen_urls = set()
        for link in links[:30]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5:
                continue
            
            # 过滤导航链接
            if any(x in title for x in ['登录', '注册', '首页', '更多']):
                continue
            
            if href.startswith('/'):
                href = f"https://tech.sina.com.cn{href}"
            elif not href.startswith('http'):
                continue
            
            if href in seen_urls:
                continue
            seen_urls.add(href)
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="news",
                keywords=["科技", "互联网"]
            )
            items.append(item)
        
        return items