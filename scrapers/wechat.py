"""
微信公众号文章爬虫模块

注意：微信公众号有严格的反爬机制，这里提供两种方案：
1. 使用搜狗微信搜索（公开接口，但可能被限制）
2. 手动输入文章链接（最可靠）

建议：使用第三方服务（如新榜、清博等）的 API 获取公众号文章
"""
from typing import List, Dict
from datetime import datetime
import re
import time
from urllib.parse import quote
from core import BaseScraper, NewsItem, console


class WechatScraper(BaseScraper):
    """微信公众号爬虫"""
    
    def __init__(self, config, cache):
        super().__init__(config, cache)
        self.sogou_url = "https://weixin.sogou.com/weixin"
    
    def scrape(self) -> List[NewsItem]:
        """爬取微信公众号文章"""
        if not self.config.get('sources.wechat.enabled', False):
            return []
        
        items = []
        
        # 方法1：从 Web 录入系统读取用户手动添加的文章（优先）
        items.extend(self._scrape_from_web_input())
        
        # 方法2：通过搜狗微信搜索（备选）
        accounts = self.config.get('sources.wechat.accounts', [])
        keywords = self.config.get('sources.wechat.keywords', [])
        
        for account in accounts:
            console.print(f"[cyan]正在搜索公众号: {account}...[/cyan]")
            try:
                account_items = self._search_by_sogou(account, keywords)
                items.extend(account_items)
                console.print(f"[green]获取 {len(account_items)} 条文章[/green]")
                time.sleep(2)
            except Exception as e:
                console.print(f"[red]搜索 {account} 失败: {e}[/red]")
        
        # 过滤已缓存的条目
        new_items = []
        for item in items:
            if not self.cache.exists(item):
                self.cache.save(item)
                new_items.append(item)
        
        return new_items
    
    def _scrape_from_web_input(self) -> List[NewsItem]:
        """从 Web 录入系统读取用户手动添加的文章"""
        import json
        from pathlib import Path
        
        articles_file = Path('data/wechat_articles.json')
        if not articles_file.exists():
            return []
        
        try:
            with open(articles_file, 'r', encoding='utf-8') as f:
                articles = json.load(f)
        except:
            return []
        
        # 筛选待处理的文章
        pending = [a for a in articles if a.get('status') == 'pending']
        if not pending:
            return []
        
        console.print(f"[cyan]从录入系统读取到 {len(pending)} 篇文章[/cyan]")
        
        urls = [a['url'] for a in pending]
        return self.scrape_by_urls(urls)
    
    def _search_by_sogou(self, account: str, keywords: List[str] = None) -> List[NewsItem]:
        """通过搜狗微信搜索获取公众号文章"""
        items = []
        
        # 构建搜索 URL
        search_query = quote(account)
        search_url = f"{self.sogou_url}?type=1&query={search_query}"
        
        html = self.fetch_page(search_url)
        if not html:
            return items
        
        soup = self.parse_html(html)
        
        # 查找公众号文章列表
        # 注意：搜狗的页面结构可能随时变化
        articles = soup.select('.txt-box h3 a, .news-list li a')
        
        for article in articles[:10]:
            try:
                title = article.get_text(strip=True)
                href = article.get('href', '')
                
                if not title or len(title) < 5:
                    continue
                
                # 检查关键词过滤
                if keywords:
                    if not any(kw in title for kw in keywords):
                        continue
                
                item = NewsItem(
                    title=title,
                    content="",
                    source=f"微信公众号: {account}",
                    source_url=href,
                    category="wechat",
                    keywords=["微信", "公众号"]
                )
                items.append(item)
                
            except Exception as e:
                console.print(f"[yellow]解析文章失败: {e}[/yellow]")
                continue
        
        return items
    
    def scrape_by_urls(self, urls: List[str]) -> List[NewsItem]:
        """
        通过文章 URL 列表抓取（推荐方案）
        
        用户可以手动收集微信公众号文章链接，然后批量抓取
        """
        items = []
        
        for url in urls:
            console.print(f"[cyan]正在抓取微信文章...[/cyan]")
            try:
                item = self._scrape_wechat_article(url)
                if item:
                    items.append(item)
                    console.print(f"[green]成功: {item.title[:50]}...[/green]")
                time.sleep(1)
            except Exception as e:
                console.print(f"[red]抓取失败: {e}[/red]")
        
        return items
    
    def _scrape_wechat_article(self, url: str) -> NewsItem:
        """抓取单个微信文章详情"""
        html = self.fetch_page(url)
        if not html:
            return None
        
        soup = self.parse_html(html)
        
        # 提取标题
        title_elem = soup.select_one('#activity-name, .rich_media_title')
        title = title_elem.get_text(strip=True) if title_elem else "未知标题"
        
        # 提取作者/公众号
        author_elem = soup.select_one('#js_name, .rich_media_meta_nickname')
        author = author_elem.get_text(strip=True) if author_elem else "未知来源"
        
        # 提取正文
        content_elem = soup.select_one('#js_content, .rich_media_content')
        content = ""
        if content_elem:
            # 简单提取文本内容
            content = content_elem.get_text(strip=True)[:500]  # 取前500字
        
        # 提取发布时间
        time_elem = soup.select_one('#publish_time, .rich_media_meta_date')
        publish_time = time_elem.get_text(strip=True) if time_elem else datetime.now().strftime("%Y-%m-%d")
        
        item = NewsItem(
            title=title,
            content=content,
            source=f"微信公众号: {author}",
            source_url=url,
            publish_time=publish_time,
            category="wechat"
        )
        
        return item


class WechatArticleInput:
    """
    微信文章手动输入工具
    用于收集用户手动提供的微信文章链接
    """
    
    def __init__(self, storage_path: str = "data/wechat_articles.txt"):
        self.storage_path = storage_path
    
    def add_article(self, url: str):
        """添加文章链接"""
        from pathlib import Path
        Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.storage_path, 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().isoformat()}|{url}\n")
    
    def get_pending_articles(self) -> List[str]:
        """获取待处理的文章链接"""
        from pathlib import Path
        
        if not Path(self.storage_path).exists():
            return []
        
        urls = []
        with open(self.storage_path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) >= 2:
                    urls.append(parts[1])
        
        return urls
    
    def clear_processed(self):
        """清空已处理的文章"""
        from pathlib import Path
        if Path(self.storage_path).exists():
            Path(self.storage_path).unlink()