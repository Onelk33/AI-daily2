#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
政府政策爬虫 - 从 gov.cn 域名抓取正式政策文件
专门用于"政策动向"板块
"""
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import re

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import BaseScraper, NewsItem, console


class GovPolicyScraper(BaseScraper):
    """政府官网政策爬虫 - 仅抓取正式政策文件"""
    
    # 政府网站配置
    GOV_SITES = [
        {
            'name': '国务院政策文件库',
            'url': 'http://www.gov.cn/zhengce/',
            'domain': 'gov.cn',
            'type': 'central'
        },
        {
            'name': '工信部政策文件',
            'url': 'https://www.miit.gov.cn/jgsj/wls/wjfb/index.html',
            'domain': 'miit.gov.cn',
            'type': 'ministry'
        },
        {
            'name': '发改委政策发布',
            'url': 'https://www.ndrc.gov.cn/xxgk/zcfb/',
            'domain': 'ndrc.gov.cn',
            'type': 'ministry'
        },
        {
            'name': '科技部政策法规',
            'url': 'https://www.most.gov.cn/xxgk/xinxifenlei/fdzdgknr/fgzc/gfxwj/',
            'domain': 'most.gov.cn',
            'type': 'ministry'
        },
        {
            'name': '网信办政策法规',
            'url': 'http://www.cac.gov.cn/xxgk/zhengce/',
            'domain': 'cac.gov.cn',
            'type': 'ministry'
        },
    ]
    
    # AI/自动驾驶相关政策关键词
    AI_KEYWORDS = [
        '人工智能', 'AI', '大模型', '深度学习', '机器学习',
        '自动驾驶', '智能网联', '无人驾驶', '智能汽车',
        '数据要素', '算力', '芯片', '算法',
        '数字化转型', '智能制造', '智慧城市',
    ]
    
    def __init__(self, config=None, cache=None):
        """初始化爬虫"""
        # 使用空配置如果未提供
        if config is None:
            config = type('Config', (), {'get': lambda self, k, d=None: d})()
        if cache is None:
            from core import CacheManager
            cache = CacheManager(db_path=Path(__file__).parent.parent / 'data' / 'cache.db')
        super().__init__(config, cache)
    
    def scrape(self) -> List[NewsItem]:
        """爬取所有政府网站的政策文件"""
        items = []
        
        for site in self.GOV_SITES:
            console.print(f"[cyan]正在爬取: {site['name']}...[/cyan]")
            try:
                site_items = self._scrape_site(site)
                items.extend(site_items)
                console.print(f"[green]获取 {len(site_items)} 条政策文件[/green]")
            except Exception as e:
                console.print(f"[yellow]爬取 {site['name']} 失败: {str(e)[:50]}[/yellow]")
        
        return items
    
    def _scrape_site(self, site: Dict) -> List[NewsItem]:
        """爬取单个政府网站"""
        items = []
        html = self.fetch_page(site['url'])
        if not html:
            return items
        
        soup = self.parse_html(html)
        
        # 通用解析：查找所有政策链接
        links = soup.select('a')
        
        for link in links[:50]:
            title = link.get_text(strip=True)
            href = link.get('href', '')
            
            # 过滤无效链接
            if not title or len(title) < 10:
                continue
            
            # 过滤非政策文件
            if not self._is_policy_file(title):
                continue
            
            # 检查是否与 AI/自动驾驶相关
            if not self._is_ai_related(title):
                continue
            
            # 构建完整 URL
            full_url = self._build_url(href, site)
            
            # 检查域名
            if not self._is_gov_domain(full_url):
                continue
            
            item = NewsItem(
                title=title,
                content="",
                source=site['name'],
                source_url=full_url,
                publish_time=datetime.now().strftime("%Y-%m-%d"),
                category="policy"
            )
            
            # 检查缓存
            if not self.cache.exists(item):
                self.cache.save(item)
                items.append(item)
        
        return items
    
    def _is_policy_file(self, title: str) -> bool:
        """判断是否是正式政策文件"""
        policy_patterns = [
            '办法', '规定', '条例', '意见', '通知', '方案', 
            '规划', '决定', '令', '批复', '函', '公告',
        ]
        return any(pt in title for pt in policy_patterns)
    
    def _is_ai_related(self, title: str) -> bool:
        """判断是否与 AI/自动驾驶相关"""
        return any(kw in title for kw in self.AI_KEYWORDS)
    
    def _build_url(self, href: str, site: Dict) -> str:
        """构建完整 URL"""
        if href.startswith('http'):
            return href
        elif href.startswith('/'):
            return f"https://{site['domain']}{href}"
        else:
            return f"https://{site['domain']}/{href}"
    
    def _is_gov_domain(self, url: str) -> bool:
        """检查是否是政府域名"""
        return '.gov.cn' in url


def fetch_gov_policies() -> List[Dict]:
    """获取政府政策数据（用于数据管道）"""
    # 使用默认配置
    scraper = GovPolicyScraper(config=None)
    items = scraper.scrape()
    
    # 转换为字典格式
    result = []
    for item in items:
        result.append({
            'title': item.title,
            'summary': item.content or f"政策文件：{item.title}",
            'source': item.source,
            'url': item.source_url,
            'date': item.publish_time,
            'keywords': [],
            'is_official_policy': True,  # 标记为官方政策
        })
    
    return result


if __name__ == '__main__':
    # 测试
    policies = fetch_gov_policies()
    print(f"\n获取到 {len(policies)} 条政府政策")
    for p in policies[:5]:
        print(f"  - [{p['source']}] {p['title'][:50]}...")