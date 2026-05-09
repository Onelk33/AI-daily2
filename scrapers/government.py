"""
政府网站爬虫模块
抓取国务院、发改委、工信部等官方政策发布
"""
from typing import List, Dict
from datetime import datetime
from core import BaseScraper, NewsItem, console


class GovernmentScraper(BaseScraper):
    """政府网站爬虫"""
    
    def scrape(self) -> List[NewsItem]:
        """爬取所有配置的政府网站"""
        if not self.config.get('sources.government.enabled', False):
            return []
        
        items = []
        sites = self.config.get('sources.government.sites', [])
        
        for site in sites:
            console.print(f"[cyan]正在爬取: {site['name']}...[/cyan]")
            try:
                site_items = self._scrape_site(site)
                items.extend(site_items)
                console.print(f"[green]获取 {len(site_items)} 条政策信息[/green]")
            except Exception as e:
                console.print(f"[red]爬取 {site['name']} 失败: {e}[/red]")
        
        return items
    
    def _scrape_site(self, site: Dict) -> List[NewsItem]:
        """爬取单个政府网站"""
        items = []
        html = self.fetch_page(site['url'])
        if not html:
            return items
        
        soup = self.parse_html(html)
        
        # 根据不同网站使用不同的解析规则（注意：先匹配更具体的域名）
        if 'ndrc.gov.cn' in site['url']:
            items = self._parse_ndrc(soup, site)
        elif 'miit.gov.cn' in site['url']:
            items = self._parse_miit(soup, site)
        elif 'gov.cn' in site['url']:
            items = self._parse_gov_cn(soup, site)
        else:
            items = self._parse_generic(soup, site)
        
        # 过滤已缓存的条目
        new_items = []
        for item in items:
            if not self.cache.exists(item):
                self.cache.save(item)
                new_items.append(item)
        
        return new_items
    
    def _parse_gov_cn(self, soup, site: Dict) -> List[NewsItem]:
        """解析国务院网站"""
        items = []
        # 国务院网站通常有特定的列表结构
        links = soup.select('div.xxgkneiright_list li a, div.list_con li a')
        
        for link in links[:20]:  # 限制数量
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5:
                continue
            
            # 构建完整 URL
            if href.startswith('/'):
                href = f"http://www.gov.cn{href}"
            elif not href.startswith('http'):
                href = f"http://www.gov.cn/zhengce/{href}"
            
            item = NewsItem(
                title=title,
                content="",  # 可以后续抓取详情页
                source=site['name'],
                source_url=href,
                publish_time=datetime.now().strftime("%Y-%m-%d"),
                category="policy"
            )
            items.append(item)
        
        return items
    
    def _parse_ndrc(self, soup, site: Dict) -> List[NewsItem]:
        """解析发改委网站"""
        items = []
        # 发改委网站使用简单的链接列表结构
        links = soup.select('a')
        
        # 基础 URL（去掉最后一段路径）
        base_url = site['url'].rstrip('/')
        
        for link in links[:30]:
            # 获取链接文本和 href
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            # 过滤：标题长度至少10个字符
            if not title or len(title) < 10:
                continue
            
            # 只处理以 ./ 开头的相对路径链接（这些是新闻链接）
            if not href.startswith('./'):
                continue
            
            # 构建完整 URL
            # href 格式: ./202604/t20260427_1404893.html
            # base_url: https://www.ndrc.gov.cn/xwdt/tzgg
            # 结果: https://www.ndrc.gov.cn/xwdt/tzgg/202604/t20260427_1404893.html
            href = base_url + '/' + href[2:]  # 去掉 './'
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="policy"
            )
            items.append(item)
        
        return items
    
    def _parse_miit(self, soup, site: Dict) -> List[NewsItem]:
        """解析工信部网站"""
        items = []
        links = soup.select('div.con_list li a, ul.list_con li a')
        
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5:
                continue
            
            if href.startswith('/'):
                href = f"https://www.miit.gov.cn{href}"
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="policy"
            )
            items.append(item)
        
        return items
    
    def _parse_generic(self, soup, site: Dict) -> List[NewsItem]:
        """通用解析方法"""
        items = []
        # 尝试多种常见的列表选择器
        selectors = [
            'li a',
            '.news-list a',
            '.list a',
            'article a',
            '.item a'
        ]
        
        links = []
        for selector in selectors:
            found = soup.select(selector)
            if found:
                links.extend(found)
        
        for link in links[:20]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            if not title or len(title) < 5 or not href:
                continue
            
            # 确保 URL 是完整的
            if not href.startswith('http'):
                base_url = '/'.join(site['url'].split('/')[:3])
                href = base_url + ('/' if not href.startswith('/') else '') + href
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=href,
                category="policy"
            )
            items.append(item)
        
        return items