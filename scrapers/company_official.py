#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动驾驶公司官网新闻爬虫
第一优先级抓取：Tesla、Waymo、Cruise、小鹏、蔚来等官网新闻
"""
import re
import json
import time
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# 浏览器 User-Agent
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

# 自动驾驶公司官网配置
AD_COMPANIES = [
    {
        'name': 'Tesla',
        'url': 'https://www.tesla.com/news',
        'base_url': 'https://www.tesla.com',
        'enabled': True,
    },
    {
        'name': 'Waymo',
        'url': 'https://waymo.com/blog/',
        'base_url': 'https://waymo.com',
        'enabled': True,
    },
    {
        'name': 'Cruise',
        'url': 'https://getcruise.com/news/',
        'base_url': 'https://getcruise.com',
        'enabled': True,
    },
    {
        'name': 'Zoox',
        'url': 'https://zoox.com/newsroom',
        'base_url': 'https://zoox.com',
        'enabled': True,
    },
    {
        'name': 'Nuro',
        'url': 'https://nuro.ai/blog',
        'base_url': 'https://nuro.ai',
        'enabled': True,
    },
    {
        'name': 'Mobileye',
        'url': 'https://www.mobileye.com/news/',
        'base_url': 'https://www.mobileye.com',
        'enabled': True,
    },
    {
        'name': '小鹏汽车',
        'url': 'https://www.xiaopeng.com/news.html',
        'base_url': 'https://www.xiaopeng.com',
        'enabled': True,
    },
    {
        'name': '蔚来',
        'url': 'https://www.nio.com/news',
        'base_url': 'https://www.nio.com',
        'enabled': True,
    },
    {
        'name': '理想汽车',
        'url': 'https://www.lixiang.com/news',
        'base_url': 'https://www.lixiang.com',
        'enabled': True,
    },
    {
        'name': '文远知行',
        'url': 'https://weride.ai/news',
        'base_url': 'https://weride.ai',
        'enabled': True,
    },
    {
        'name': '小马智行',
        'url': 'https://www.pony.ai/news',
        'base_url': 'https://www.pony.ai',
        'enabled': True,
    },
    {
        'name': 'AutoX',
        'url': 'https://www.autox.ai/news',
        'base_url': 'https://www.autox.ai',
        'enabled': True,
    },
]

# 自动驾驶关键词（用于标题筛选）
AD_TITLE_KEYWORDS = [
    '自动驾驶', '无人驾驶', '智能驾驶', '智驾',
    'robotaxi', 'fsd', 'full self-driving',
    '端到端', '城市noa', 'noa',
    '激光雷达', '视觉感知', '决策规划',
    '无人车', '智能车', '无人化',
    'l3级', 'l4级', 'l3自动驾驶', 'l4自动驾驶',
    '路测', '牌照', '许可', '准入',
    '获批', '批准', '发放牌照',
    '事故', '安全',
    '交付', '量产', '上市', '开售',
    '扩张', '运营', '落地',
]


def fetch_page(url: str, timeout: int = 15) -> Optional[str]:
    """获取页面HTML"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"    [失败] {url}: {str(e)[:60]}")
        return None


def extract_links_from_page(html: str, base_url: str) -> List[Dict]:
    """
    从页面中提取所有文章链接
    通用方法：提取所有<a>标签，通过标题关键词筛选
    """
    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    articles = []
    seen_urls = set()

    for link in soup.find_all('a', href=True):
        href = link.get('href', '').strip()
        title = link.get_text(strip=True)

        if not href or not title:
            continue
        if len(title) < 10 or len(title) > 200:
            continue

        # 构建完整URL
        full_url = urljoin(base_url, href)

        # 过滤非文章链接（javascript、锚点、图片等）
        if href.startswith('javascript:') or href.startswith('#'):
            continue
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # 通过标题关键词判断是否可能是AD相关文章
        title_lower = title.lower()
        is_ad_related = any(kw.lower() in title_lower for kw in AD_TITLE_KEYWORDS)

        # 如果没有AD关键词，但URL包含blog/news/press，也保留（后面再判断）
        if not is_ad_related:
            path_lower = href.lower()
            if not any(p in path_lower for p in ['/blog', '/news', '/press', '/article', '/post']):
                continue

        articles.append({
            'title': title,
            'url': full_url,
            'is_ad_related': is_ad_related,
        })

    return articles


def fetch_company_news(company: Dict, date_window_days: int = 2) -> List[Dict]:
    """
    抓取单个公司官网新闻
    返回标准格式的字典列表
    """
    name = company['name']
    url = company['url']
    base_url = company.get('base_url', url)

    print(f"  [官网] 正在抓取 {name} ({url})...")

    html = fetch_page(url, timeout=15)
    if not html:
        return []

    links = extract_links_from_page(html, base_url)

    # 转换为统一格式
    results = []
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    for link in links[:15]:  # 每站最多15条
        # 尝试访问文章页面获取摘要（简要实现）
        summary = f'来自{name}官网的自动驾驶相关动态。'
        try:
            article_html = fetch_page(link['url'], timeout=10)
            if article_html:
                article_soup = BeautifulSoup(article_html, 'html.parser')
                # 尝试提取meta description
                meta_desc = article_soup.find('meta', attrs={'name': 'description'})
                if meta_desc and meta_desc.get('content'):
                    summary = meta_desc['content'][:300]
                else:
                    # 提取前几个段落
                    paragraphs = article_soup.find_all('p')
                    texts = [p.get_text(strip=True) for p in paragraphs[:3] if len(p.get_text(strip=True)) > 20]
                    if texts:
                        summary = ' '.join(texts)[:300]
        except Exception:
            pass

        item = {
            'title': link['title'],
            'summary': summary,
            'source': f'{name}官网',
            'url': link['url'],
            'country': 'industry',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'keywords': [],
            'is_official': True,
            'company': name,
        }
        results.append(item)

    print(f"    -> 获得 {len(results)} 条")
    return results


def fetch_all_official_ad_news() -> List[Dict]:
    """
    抓取所有配置的自动驾驶公司官网新闻
    返回统一格式的字典列表
    """
    all_news = []
    success_count = 0

    print("\n[官网抓取] 开始爬取自动驾驶公司官网...")

    for company in AD_COMPANIES:
        if not company.get('enabled', True):
            continue

        try:
            news = fetch_company_news(company)
            if news:
                success_count += 1
                all_news.extend(news)
            time.sleep(0.5)  # 礼貌间隔
        except Exception as e:
            print(f"  [错误] {company['name']}: {str(e)[:60]}")

    print(f"[官网抓取] 完成: 成功 {success_count}/{len(AD_COMPANIES)} 个站点, 共 {len(all_news)} 篇文章")
    return all_news


def run_technology_search_skill(keyword: str, limit: int = 15) -> List[Dict]:
    """
    调用 technology-search skill 搜索AD新闻
    返回统一格式的字典列表
    """
    import subprocess
    import os

    # skill 路径
    skill_path = os.path.expanduser('~/.codex/skills/technology-search/scripts/search_news.js')
    if not os.path.exists(skill_path):
        print(f"  [Skill] technology-search 未找到: {skill_path}")
        return []

    cmd = ['node', skill_path, keyword, '--limit', str(limit), '--max-per-source', '5', '--max-age', '3']

    print(f"  [Skill] technology-search 搜索: '{keyword}'...")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            encoding='utf-8',
            errors='replace'
        )

        if result.returncode != 0:
            print(f"    [错误] 搜索失败: {result.stderr[:100]}")
            return []

        # 解析JSON输出
        data = json.loads(result.stdout)
        items = data.get('results', [])

        # 转换为统一格式
        news = []
        for item in items:
            news.append({
                'title': item.get('title', ''),
                'summary': item.get('summary', '')[:300],
                'source': item.get('source', '未知来源'),
                'url': item.get('url', ''),
                'country': 'industry',
                'date': item.get('published_at', datetime.now().strftime('%Y-%m-%d'))[:10],
                'keywords': [],
                'is_skill': True,
            })

        print(f"    -> 获得 {len(news)} 条")
        return news

    except subprocess.TimeoutExpired:
        print(f"    [超时] technology-search 搜索超时(300s)")
        return []
    except json.JSONDecodeError as e:
        print(f"    [错误] JSON解析失败: {e}")
        return []
    except Exception as e:
        print(f"    [错误] 搜索异常: {str(e)[:80]}")
        return []


def run_baidu_search_skill(keyword: str, limit: int = 10) -> List[Dict]:
    """
    调用 baidu-search skill（通过 skill 工具不可直接调用，这里预留接口）
    实际实现：通过运行 skill 脚本或返回空列表由外部处理
    """
    # baidu-search skill 没有直接可执行的脚本，需要外部通过 Comate 调用
    # 这里返回空列表，由 Agent 在外层调用 skill 后写入 data/supplementary_ad/
    print(f"  [Skill] 百度搜索 '{keyword}' 需外部调用，跳过")
    return []


def supplementary_search_ad_news() -> List[Dict]:
    """
    补充搜索自动驾驶新闻
    1. technology-search skill
    2. 预存的补充数据
    """
    all_news = []

    # 搜索关键词列表
    search_keywords = [
        '自动驾驶 最新',
        'Robotaxi 运营',
        'Tesla FSD',
        'Waymo 扩张',
        '端到端自动驾驶',
        '城市NOA',
        'L3上路',
    ]

    print("\n[Skill补充] 开始搜索补充AD新闻...")

    for keyword in search_keywords:
        try:
            news = run_technology_search_skill(keyword, limit=10)
            all_news.extend(news)
            time.sleep(0.3)
        except Exception as e:
            print(f"    [错误] 关键词 '{keyword}': {e}")

    # 去重
    seen_urls = set()
    unique_news = []
    for item in all_news:
        url = item.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_news.append(item)

    print(f"[Skill补充] 完成: 去重后 {len(unique_news)} 条")
    return unique_news


def merge_official_and_skill(official_news: List[Dict], skill_news: List[Dict]) -> List[Dict]:
    """
    合并官网和Skill新闻，官网来源优先
    去重原则：同一URL只保留一次，官网优先
    """
    merged = []
    seen_urls = set()

    # 先添加官网新闻（优先）
    for item in official_news:
        url = item.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            merged.append(item)

    # 再添加Skill新闻（仅添加不重复的）
    for item in skill_news:
        url = item.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            merged.append(item)

    return merged


if __name__ == '__main__':
    # 测试
    print("测试官网爬虫...")
    official = fetch_all_official_ad_news()
    print(f"\n官网新闻: {len(official)} 条")
    for item in official[:5]:
        print(f"  - [{item['source']}] {item['title'][:50]}...")

    print("\n测试Skill搜索...")
    skill = supplementary_search_ad_news()
    print(f"Skill新闻: {len(skill)} 条")
    for item in skill[:5]:
        print(f"  - [{item['source']}] {item['title'][:50]}...")
