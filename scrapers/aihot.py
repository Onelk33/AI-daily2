"""
AI HOT 爬虫模块
从 aihot.virxact.com 拉取 AI 行业资讯
"""
import json
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import requests
from rich.console import Console

console = Console()


@dataclass
class AIHOTItem:
    """AI HOT 条目"""
    id: str
    title: str
    title_en: Optional[str]
    url: str
    source: str
    published_at: Optional[str]
    summary: Optional[str]
    category: Optional[str]


class AIHOTScraper:
    """AI HOT 爬虫"""
    
    BASE_URL = "https://aihot.virxact.com/api/public"
    
    # 必须带 User-Agent，否则会被 403
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    
    # 分类映射
    CATEGORY_MAP = {
        'ai-models': 'AI模型发布',
        'ai-products': 'AI产品发布',
        'industry': '行业动态',
        'paper': '论文研究',
        'tip': '技巧与观点'
    }
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
    
    def fetch_items(
        self,
        mode: str = "selected",
        category: str = None,
        q: str = None,
        since: str = None,
        take: int = 50
    ) -> List[AIHOTItem]:
        """
        拉取 AI 动态条目
        
        Args:
            mode: "selected"（精选）或 "all"（全部）
            category: 分类（ai-models/ai-products/industry/paper/tip）
            q: 关键词搜索
            since: 时间窗口起点（ISO 8601）
            take: 获取数量（1-100）
        """
        params = {
            'mode': mode,
            'take': min(take, 100)
        }
        
        if category:
            params['category'] = category
        if q:
            params['q'] = q
        if since:
            params['since'] = since
        
        try:
            response = self.session.get(
                f"{self.BASE_URL}/items",
                params=params,
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            items = []
            
            for item in data.get('items', []):
                items.append(AIHOTItem(
                    id=item.get('id', ''),
                    title=item.get('title', ''),
                    title_en=item.get('title_en'),
                    url=item.get('url', ''),
                    source=item.get('source', '未知来源'),
                    published_at=item.get('publishedAt'),
                    summary=item.get('summary'),
                    category=item.get('category')
                ))
            
            return items
            
        except Exception as e:
            console.print(f"[yellow]AI HOT API 调用失败: {str(e)[:50]}[/yellow]")
            return []
    
    def fetch_industry_news(self, days: int = 1, keywords: List[str] = None) -> List[AIHOTItem]:
        """
        拉取行业资讯（用于行业资讯板块强化）
        
        Args:
            days: 时间范围（天数）
            keywords: 额外的关键词过滤
        """
        console.print(f"[cyan]正在从 AI HOT 拉取行业资讯...[/cyan]")
        
        # 计算时间窗口
        since = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        all_items = []
        
        # 拉取行业动态、模型发布、产品发布
        categories = ['industry', 'ai-models', 'ai-products']
        
        for category in categories:
            items = self.fetch_items(
                mode='selected',
                category=category,
                since=since,
                take=30
            )
            all_items.extend(items)
            time.sleep(0.2)  # 串行调用，避免限流
        
        # 如果有额外关键词，搜索补充
        if keywords:
            for keyword in keywords:
                items = self.fetch_items(
                    mode='selected',
                    q=keyword,
                    since=since,
                    take=20
                )
                all_items.extend(items)
                time.sleep(0.2)
        
        # 去重
        seen_ids = set()
        unique_items = []
        for item in all_items:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                unique_items.append(item)
        
        console.print(f"[green]从 AI HOT 获取 {len(unique_items)} 条行业资讯[/green]")
        
        return unique_items
    
    def fetch_policy_news(self, days: int = 7) -> List[AIHOTItem]:
        """
        拉取政策动向（用于政策动向板块补漏）
        
        Args:
            days: 时间范围（天数）
        """
        console.print(f"[cyan]正在从 AI HOT 搜索政策动向...[/cyan]")
        
        # 计算时间窗口
        since = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # 政策相关关键词
        policy_keywords = [
            '政策', 'regulation', '立法', '标准', '法规',
            'law', 'policy', '合规', '监管'
        ]
        
        all_items = []
        
        for keyword in policy_keywords:
            items = self.fetch_items(
                mode='selected',
                q=keyword,
                since=since,
                take=15
            )
            all_items.extend(items)
            time.sleep(0.2)  # 串行调用
        
        # 去重
        seen_ids = set()
        unique_items = []
        for item in all_items:
            if item.id not in seen_ids:
                seen_ids.add(item.id)
                unique_items.append(item)
        
        console.print(f"[green]从 AI HOT 获取 {len(unique_items)} 条政策相关资讯[/green]")
        
        return unique_items
    
    def fetch_all_for_daily_report(self, days: int = 1) -> Dict[str, List[AIHOTItem]]:
        """
        为日报拉取所有相关数据
        
        Args:
            days: 时间范围（天数）
            
        Returns:
            {
                'industry': [...],  # 行业资讯
                'policy': [...]     # 政策动向
            }
        """
        result = {
            'industry': [],
            'policy': []
        }
        
        # 拉取行业资讯
        industry_keywords = ['自动驾驶', 'robotaxi', '人工智能', 'autonomous', 'AI']
        result['industry'] = self.fetch_industry_news(days=days, keywords=industry_keywords)
        
        time.sleep(0.3)
        
        # 拉取政策动向
        result['policy'] = self.fetch_policy_news(days=days)
        
        return result
    
    def to_news_items(self, items: List[AIHOTItem], default_category: str = 'news') -> List:
        """
        将 AIHOTItem 转换为 NewsItem 格式
        
        Args:
            items: AI HOT 条目列表
            default_category: 默认分类
        """
        from core import NewsItem
        
        news_items = []
        
        for item in items:
            # 确定分类
            category = default_category
            if item.category == 'industry' or '政策' in item.title or 'regulation' in item.title.lower():
                category = 'policy'
            
            # 构建内容
            content = item.summary or ""
            if item.title_en and item.title_en != item.title:
                content = f"[原文: {item.title_en}]\n\n{content}"
            
            # 格式化时间
            publish_time = None
            if item.published_at:
                try:
                    dt = datetime.fromisoformat(item.published_at.replace('Z', '+00:00'))
                    publish_time = dt.strftime('%Y-%m-%d')
                except:
                    pass
            
            news_item = NewsItem(
                title=item.title,
                content=content,
                source=item.source,
                source_url=item.url,
                category=category,
                publish_time=publish_time
            )
            
            news_items.append(news_item)
        
        return news_items


def fetch_aihot_data(days: int = 1) -> Dict[str, List]:
    """
    便捷函数：拉取 AI HOT 数据
    
    Args:
        days: 时间范围（天数）
    """
    scraper = AIHOTScraper()
    data = scraper.fetch_all_for_daily_report(days=days)
    
    # 转换为 NewsItem 格式
    result = {
        'industry': scraper.to_news_items(data['industry'], default_category='news'),
        'policy': scraper.to_news_items(data['policy'], default_category='policy')
    }
    
    return result


if __name__ == '__main__':
    # 测试
    import sys
    from pathlib import Path
    
    # 添加项目根目录到 Python 路径
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    data = fetch_aihot_data(days=1)
    print(f"\n行业资讯: {len(data['industry'])} 条")
    print(f"政策动向: {len(data['policy'])} 条")
    
    if data['industry']:
        print("\n示例（行业资讯）:")
        item = data['industry'][0]
        print(f"  标题: {item.title}")
        print(f"  来源: {item.source}")
        print(f"  链接: {item.source_url}")