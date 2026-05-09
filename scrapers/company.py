"""
重点公司新闻爬虫模块
抓取华为、阿里、腾讯、百度等公司官网新闻
"""
from typing import List, Dict
from datetime import datetime
from core import BaseScraper, NewsItem, console


class CompanyScraper(BaseScraper):
    """公司官网新闻爬虫"""
    
    def scrape(self) -> List[NewsItem]:
        """爬取所有配置的公司新闻"""
        if not self.config.get('sources.companies.enabled', False):
            return []
        
        items = []
        companies = self.config.get('sources.companies.list', [])
        
        for company in companies:
            console.print(f"[cyan]正在爬取: {company['name']} 新闻...[/cyan]")
            try:
                company_items = self._scrape_company(company)
                items.extend(company_items)
                console.print(f"[green]获取 {len(company_items)} 条公司新闻[/green]")
            except Exception as e:
                console.print(f"[red]爬取 {company['name']} 失败: {e}[/red]")
        
        return items
    
    def _scrape_company(self, company: Dict) -> List[NewsItem]:
        """爬取单个公司新闻"""
        items = []
        html = self.fetch_page(company['news_url'])
        if not html:
            return items
        
        soup = self.parse_html(html)
        
        # 根据公司选择不同的解析方法
        company_name = company['name'].lower()
        
        # 自动驾驶公司
        if 'waymo' in company_name:
            items = self._parse_waymo(soup, company)
        elif 'zoox' in company_name:
            items = self._parse_zoox(soup, company)
        elif 'tesla' in company_name:
            items = self._parse_tesla(soup, company)
        elif 'pony' in company_name or '小马' in company_name:
            items = self._parse_pony(soup, company)
        elif 'weride' in company_name or '文远' in company_name:
            items = self._parse_weride(soup, company)
        # 科技公司
        elif '华为' in company_name or 'huawei' in company_name:
            items = self._parse_huawei(soup, company)
        elif '阿里' in company_name or 'alibaba' in company_name:
            items = self._parse_alibaba(soup, company)
        elif '腾讯' in company_name or 'tencent' in company_name:
            items = self._parse_tencent(soup, company)
        elif '百度' in company_name or 'baidu' in company_name:
            items = self._parse_baidu(soup, company)
        else:
            items = self._parse_generic(soup, company)
        
        # 过滤已缓存的条目
        new_items = []
        for item in items:
            if not self.cache.exists(item):
                self.cache.save(item)
                new_items.append(item)
        
        return new_items
    
    def _parse_huawei(self, soup, company: Dict) -> List[NewsItem]:
        """解析华为官网"""
        items = []
        links = soup.select('a.news-item, .news-list a, article a')
        
        for link in links[:15]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5:
                continue
            
            if href.startswith('/'):
                href = f"https://www.huawei.com{href}"
            
            item = NewsItem(
                title=title,
                content="",
                source=f"{company['name']}官网",
                source_url=href,
                category="company"
            )
            items.append(item)
        
        return items
    
    def _parse_alibaba(self, soup, company: Dict) -> List[NewsItem]:
        """解析阿里巴巴官网"""
        items = []
        links = soup.select('.news-item a, .article-item a, a.news-link')
        
        for link in links[:15]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5:
                continue
            
            if href.startswith('/'):
                href = f"https://www.alibabagroup.com{href}"
            
            item = NewsItem(
                title=title,
                content="",
                source=f"{company['name']}官网",
                source_url=href,
                category="company"
            )
            items.append(item)
        
        return items
    
    def _parse_tencent(self, soup, company: Dict) -> List[NewsItem]:
        """解析腾讯官网"""
        items = []
        links = soup.select('.news-item a, .article a, li a')
        
        for link in links[:15]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5:
                continue
            
            if href.startswith('/'):
                href = f"https://www.tencent.com{href}"
            
            item = NewsItem(
                title=title,
                content="",
                source=f"{company['name']}官网",
                source_url=href,
                category="company"
            )
            items.append(item)
        
        return items
    
    def _parse_baidu(self, soup, company: Dict) -> List[NewsItem]:
        """解析百度官网"""
        items = []
        # 百度官网可能需要 JavaScript 渲染
        links = soup.select('a')
        
        for link in links[:15]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5 or not href:
                continue
            
            item = NewsItem(
                title=title,
                content="",
                source=f"{company['name']}官网",
                source_url=href if href.startswith('http') else f"https://www.baidu.com{href}",
                category="company"
            )
            items.append(item)
        
        return items
    
    def _parse_waymo(self, soup, company: Dict) -> List[NewsItem]:
        """解析 Waymo 博客页面"""
        items = []
        # Waymo 博客文章通常在特定的容器中
        links = soup.select('a')
        
        seen_titles = set()
        for link in links:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            # 过滤
            if not title or len(title) < 20:
                continue
            
            # 过滤导航链接
            skip_titles = ['company news', 'technology', 'life at waymo', 'waymo driver', 
                          'safety report', 'read more', 'waymo', 'blog', 'updates']
            if title.lower() in skip_titles or title in seen_titles:
                continue
            
            # 只保留博客文章链接
            if '/blog/' not in href and 'Read more' not in title:
                continue
            
            seen_titles.add(title)
            
            # 清理标题
            if title.startswith('Read more:'):
                title = title.replace('Read more:', '').strip()
            if title.startswith('Read more'):
                title = title.replace('Read more', '').strip(':').strip()
            
            # 构建完整 URL
            if href.startswith('/'):
                href = f"https://waymo.com{href}"
            elif not href.startswith('http'):
                continue
            
            item = NewsItem(
                title=title,
                content="",
                source=f"{company['name']}官网",
                source_url=href,
                category="company",
                keywords=["自动驾驶", "Robotaxi"]
            )
            items.append(item)
            
            if len(items) >= 10:
                break
        
        return items
    
    def _parse_zoox(self, soup, company: Dict) -> List[NewsItem]:
        """解析 Zoox 新闻页面"""
        items = []
        # Zoox 新闻文章 - 尝试多种选择器
        links = soup.select('a')
        
        seen_titles = set()
        for link in links:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            # 过滤
            if not title or len(title) < 15:
                continue
            
            # 过滤导航和Cookie相关
            skip_titles = ['read article', 'news', 'press room', 'accept', 'reject', 
                          'cookie', 'privacy', 'logo', 'how to ride']
            if any(skip in title.lower() for skip in skip_titles):
                continue
            
            if title in seen_titles:
                continue
            
            seen_titles.add(title)
            
            # 构建完整 URL
            if href.startswith('/'):
                href = f"https://zoox.com{href}"
            elif not href.startswith('http'):
                continue
            
            item = NewsItem(
                title=title,
                content="",
                source=f"{company['name']}官网",
                source_url=href,
                category="company",
                keywords=["自动驾驶", "Robotaxi"]
            )
            items.append(item)
            
            if len(items) >= 10:
                break
        
        return items
    
    def _parse_tesla(self, soup, company: Dict) -> List[NewsItem]:
        """解析特斯拉新闻页面"""
        items = []
        # 特斯拉投资者关系页面的新闻
        links = soup.select('a[href*="/press"], .news-item a, .press-release a')
        
        for link in links[:15]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 10:
                continue
            
            if href.startswith('/'):
                href = f"https://ir.tesla.com{href}"
            
            item = NewsItem(
                title=title,
                content="",
                source=f"{company['name']}官网",
                source_url=href,
                category="company",
                keywords=["电动车", "自动驾驶"]
            )
            items.append(item)
        
        return items
    
    def _parse_pony(self, soup, company: Dict) -> List[NewsItem]:
        """解析小马智行新闻页面"""
        items = []
        # Pony.ai 新闻链接指向微信公众号
        links = soup.select('a[href*="mp.weixin.qq.com"], .press-item a, .news-item a')
        
        for link in links[:15]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 10:
                continue
            
            # 过滤分页链接
            if 'article_page' in href:
                continue
            
            item = NewsItem(
                title=title,
                content="",
                source=f"{company['name']}官网",
                source_url=href if href.startswith('http') else f"https://pony.ai{href}",
                category="company",
                keywords=["自动驾驶", "Robotaxi"]
            )
            items.append(item)
        
        return items
    
    def _parse_weride(self, soup, company: Dict) -> List[NewsItem]:
        """解析文远知行新闻页面"""
        items = []
        # WeRide 新闻发布页面
        links = soup.select('a[href*="news-releases"], .news-item a, h3 a, h4 a')
        
        for link in links[:15]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 15:
                continue
            
            # 过滤 PDF 链接等
            if 'pdf' in href.lower():
                continue
            
            # 构建完整 URL
            if href.startswith('/'):
                href = f"https://ir.weride.ai{href}"
            elif not href.startswith('http'):
                href = f"https://ir.weride.ai/news-events/news-releases/{href}"
            
            item = NewsItem(
                title=title,
                content="",
                source=f"{company['name']}官网",
                source_url=href,
                category="company",
                keywords=["自动驾驶", "Robotaxi"]
            )
            items.append(item)
        
        return items
    
    def _parse_generic(self, soup, company: Dict) -> List[NewsItem]:
        """通用解析方法"""
        items = []
        links = soup.select('a')
        
        seen_titles = set()
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5 or title in seen_titles:
                continue
            
            seen_titles.add(title)
            
            base_url = '/'.join(company['news_url'].split('/')[:3])
            if href.startswith('/'):
                href = base_url + href
            elif not href.startswith('http'):
                href = base_url + '/' + href
            
            item = NewsItem(
                title=title,
                content="",
                source=f"{company['name']}官网",
                source_url=href,
                category="company"
            )
            items.append(item)
        
        return items