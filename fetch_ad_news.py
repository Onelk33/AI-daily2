#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动驾驶行业资讯抓取模块
实现"官网优先 + Skill 补全"策略
"""
import json
import time
import subprocess
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path

# ============ 配置区 ============

# 浏览器 User-Agent
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

# 自动驾驶公司官网配置
AD_COMPANIES = [
    # 国外
    {'name': 'Tesla', 'url': 'https://www.tesla.com/news', 'base_url': 'https://www.tesla.com'},
    {'name': 'Waymo', 'url': 'https://waymo.com/blog/', 'base_url': 'https://waymo.com'},
    {'name': 'Cruise', 'url': 'https://getcruise.com/news/', 'base_url': 'https://getcruise.com'},
    {'name': 'Zoox', 'url': 'https://zoox.com/newsroom', 'base_url': 'https://zoox.com'},
    {'name': 'Nuro', 'url': 'https://nuro.ai/blog', 'base_url': 'https://nuro.ai'},
    {'name': 'Mobileye', 'url': 'https://www.mobileye.com/news/', 'base_url': 'https://www.mobileye.com'},
    # 国内
    {'name': '小鹏汽车', 'url': 'https://www.xiaopeng.com/news.html', 'base_url': 'https://www.xiaopeng.com'},
    {'name': '蔚来', 'url': 'https://www.nio.com/news', 'base_url': 'https://www.nio.com'},
    {'name': '理想汽车', 'url': 'https://www.lixiang.com/news', 'base_url': 'https://www.lixiang.com'},
    {'name': '比亚迪', 'url': 'https://www.byd.com/cn/news.html', 'base_url': 'https://www.byd.com'},
    {'name': '小米汽车', 'url': 'https://www.xiaomiev.com/news', 'base_url': 'https://www.xiaomiev.com'},
    {'name': '文远知行', 'url': 'https://weride.ai/news', 'base_url': 'https://weride.ai'},
    {'name': '小马智行', 'url': 'https://www.pony.ai/news', 'base_url': 'https://www.pony.ai'},
    {'name': 'AutoX', 'url': 'https://www.autox.ai/news', 'base_url': 'https://www.autox.ai'},
]

# 自动驾驶关键词（用于标题筛选）
AD_TITLE_KEYWORDS = [
    '自动驾驶', '无人驾驶', '智能驾驶', '智驾', '智驾',
    'robotaxi', 'fsd', 'full self-driving', 'self-driving',
    '端到端', '城市noa', 'noa', '城市导航',
    '激光雷达', '视觉感知', '决策规划',
    '无人车', '智能车', '无人化',
    'l3级', 'l4级', 'l3自动驾驶', 'l4自动驾驶', 'l3', 'l4',
    '路测', '牌照', '许可', '准入', '获批', '批准',
    '事故', '安全',
    '交付', '量产', '上市', '开售',
    '扩张', '运营', '落地', '商业化',
    'fremont', 'austin', 'phoenix', 'sf', 'san francisco',
    '测试', '试点', '部署',
]

# Skill 搜索关键词
SKILL_SEARCH_KEYWORDS = [
    '自动驾驶 最新',
    '无人驾驶 许可',
    'Robotaxi 运营',
    'Tesla FSD',
    'Waymo 扩张',
    'Cruise 恢复',
    'Nuro 许可',
    '端到端自动驾驶',
    '城市NOA',
    'L3上路',
    '无人驾驶 牌照',
    '自动驾驶 商业化',
]


# ============ 工具函数 ============

def fetch_page(url: str, timeout: int = 15) -> Optional[str]:
    """获取页面HTML"""
    import requests
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return None


def extract_articles_from_html(html: str, base_url: str, company_name: str) -> List[Dict]:
    """
    从页面中提取文章列表
    使用 BeautifulSoup 通用解析方法
    """
    from bs4 import BeautifulSoup

    if not html:
        return []

    soup = BeautifulSoup(html, 'html.parser')
    articles = []
    seen_urls = set()

    # 通用解析：查找所有可能是文章链接的 <a> 标签
    for link in soup.find_all('a', href=True):
        href = link.get('href', '').strip()
        title = link.get_text(strip=True)

        if not href or not title:
            continue
        if len(title) < 10 or len(title) > 200:
            continue

        # 构建完整URL
        if href.startswith('//'):
            full_url = 'https:' + href
        elif href.startswith('/'):
            full_url = base_url.rstrip('/') + href
        elif not href.startswith('http'):
            continue
        else:
            full_url = href

        # 过滤非文章链接
        if full_url in seen_urls:
            continue
        if 'javascript:' in href or href.startswith('#'):
            continue
        seen_urls.add(full_url)

        # 通过标题关键词判断
        title_lower = title.lower()
        is_ad_related = any(kw.lower() in title_lower for kw in AD_TITLE_KEYWORDS)

        # 如果没有AD关键词，检查URL中是否包含blog/news/press
        if not is_ad_related:
            path_lower = href.lower()
            if not any(p in path_lower for p in ['/blog', '/news', '/press', '/article', '/post', '/updates']):
                continue

        articles.append({
            'title': title,
            'url': full_url,
            'is_ad_related': is_ad_related,
        })

    return articles


def extract_article_summary(url: str) -> str:
    """从文章页面提取摘要"""
    html = fetch_page(url, timeout=10)
    if not html:
        return f'来自官网的自动驾驶相关动态。'

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')

    # 尝试提取 meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc and meta_desc.get('content'):
        return meta_desc['content'][:300]

    # 尝试提取前几个段落
    paragraphs = soup.find_all('p')
    texts = [p.get_text(strip=True) for p in paragraphs[:3] if len(p.get_text(strip=True)) > 20]
    if texts:
        return ' '.join(texts)[:300]

    return f'来自官网的自动驾驶相关动态。'


# ============ 官网爬取 ============

def fetch_company_news(company: Dict, date_window: Tuple[datetime, datetime]) -> List[Dict]:
    """
    抓取单个公司官网新闻

    Args:
        company: 公司配置字典
        date_window: (昨天00:00, 今天18:00) 时间窗口

    Returns:
        文章列表
    """
    name = company['name']
    url = company['url']
    base_url = company.get('base_url', url)

    try:
        html = fetch_page(url, timeout=15)
        if not html:
            return []

        articles = extract_articles_from_html(html, base_url, name)

        results = []
        today = date_window[1].date()
        yesterday = date_window[0].date()

        # 时间窗口：昨天00:00 到 今天18:00
        window_start = datetime.combine(yesterday, datetime.min.time())
        window_end = datetime.combine(today, datetime.strptime('18:00', '%H:%M').time())

        for article in articles[:15]:
            summary = extract_article_summary(article['url'])

            item = {
                'title': article['title'],
                'summary': summary,
                'source': f'{name}官网',
                'url': article['url'],
                'country': 'industry',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'keywords': [],
                'is_official': True,
                'company': name,
            }
            results.append(item)

        return results

    except Exception as e:
        return []


def fetch_all_official_ad_news() -> Tuple[List[Dict], Dict]:
    """
    抓取所有配置的自动驾驶公司官网新闻

    Returns:
        (文章列表, 统计字典)
    """
    all_news = []
    success_count = 0
    fail_count = 0
    total_articles = 0

    # 时间窗口：昨天00:00 到 今天18:00
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    window_start = datetime.combine(yesterday, datetime.min.time())
    window_end = datetime.combine(today, datetime.strptime('18:00', '%H:%M').time())

    print("\n[官网抓取] 开始爬取自动驾驶公司官网...")

    for company in AD_COMPANIES:
        name = company['name']
        url = company['url']

        try:
            print(f"  [官网] 正在抓取 {name} ({url})...")
            news = fetch_company_news(company, (window_start, window_end))

            if news:
                success_count += 1
                all_news.extend(news)
                total_articles += len(news)
                print(f"    -> 获得 {len(news)} 条")
            else:
                print(f"    -> 无相关内容")

            time.sleep(0.5)  # 礼貌间隔

        except Exception as e:
            fail_count += 1
            print(f"  [失败] {name}: {str(e)[:60]}")

    print(f"\n[官网抓取] 完成: 成功 {success_count}/{len(AD_COMPANIES)} 个站点, 共 {total_articles} 篇文章")

    stats = {
        'success_count': success_count,
        'fail_count': fail_count,
        'total_articles': total_articles,
    }

    return all_news, stats


# ============ Skill 补充搜索 ============

def run_technology_search_skill(keyword: str, limit: int = 15) -> Tuple[List[Dict], int]:
    """
    调用 technology-search skill 搜索AD新闻

    Returns:
        (文章列表, 返回条数)
    """
    skill_path = os.path.expanduser('~/.codex/skills/technology-search/scripts/search_news.js')
    if not os.path.exists(skill_path):
        print(f"  [Skill] technology-search 未找到: {skill_path}")
        return [], 0

    cmd = ['node', skill_path, keyword, '--limit', str(limit), '--max-per-source', '5', '--max-age', '3']

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
            return [], 0

        # 解析JSON输出
        data = json.loads(result.stdout)
        items = data.get('results', [])

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

        return news, len(news)

    except subprocess.TimeoutExpired:
        print(f"    [超时] technology-search 搜索超时(300s)")
        return [], 0
    except json.JSONDecodeError as e:
        print(f"    [错误] JSON解析失败: {e}")
        return [], 0
    except Exception as e:
        print(f"    [错误] 搜索异常: {str(e)[:80]}")
        return [], 0


def run_baidu_search_skill(keyword: str, limit: int = 10) -> Tuple[List[Dict], int]:
    """
    调用百度搜索 skill（通过 subprocess 调用）

    Returns:
        (文章列表, 返回条数)
    """
    # 尝试调用 baidu-search skill 脚本
    baidu_skill_path = os.path.expanduser('~/.codex/skills/baidu-search/scripts/search.py')
    if not os.path.exists(baidu_skill_path):
        print(f"  [Skill] baidu-search 未找到")
        return [], 0

    try:
        cmd = ['python', baidu_skill_path, '--keyword', keyword, '--limit', str(limit)]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            encoding='utf-8',
            errors='replace'
        )

        if result.returncode != 0:
            return [], 0

        data = json.loads(result.stdout)
        items = data.get('results', [])

        news = []
        for item in items:
            news.append({
                'title': item.get('title', ''),
                'summary': item.get('snippet', '')[:300],
                'source': item.get('source', '百度搜索'),
                'url': item.get('url', ''),
                'country': 'industry',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'keywords': [],
                'is_skill': True,
                'skill_type': 'baidu',
            })

        return news, len(news)

    except Exception:
        return [], 0


def run_google_search_skill(keyword: str, limit: int = 10) -> Tuple[List[Dict], int]:
    """
    调用 Google Search Console skill（如果有）

    Returns:
        (文章列表, 返回条数)
    """
    # 尝试调用 google_search_console-automation skill
    google_skill_path = os.path.expanduser('~/.codex/skills/google_search_console-automation/scripts/search.js')
    if not os.path.exists(google_skill_path):
        print(f"  [Skill] google_search_console-automation 未找到")
        return [], 0

    try:
        cmd = ['node', google_skill_path, '--query', keyword, '--limit', str(limit)]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            encoding='utf-8',
            errors='replace'
        )

        if result.returncode != 0:
            return [], 0

        data = json.loads(result.stdout)
        items = data.get('results', [])

        news = []
        for item in items:
            news.append({
                'title': item.get('title', ''),
                'summary': item.get('snippet', '')[:300],
                'source': item.get('source', 'Google搜索'),
                'url': item.get('url', ''),
                'country': 'industry',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'keywords': [],
                'is_skill': True,
                'skill_type': 'google',
            })

        return news, len(news)

    except Exception:
        return [], 0


def supplementary_search_ad_news() -> Tuple[List[Dict], Dict]:
    """
    补充搜索自动驾驶新闻

    Returns:
        (文章列表, 统计字典)
    """
    all_news = []
    stats = {
        'technology_search': 0,
        'baidu_search': 0,
        'google_search': 0,
    }

    print("\n[Skill补充] 开始搜索补充AD新闻...")

    for keyword in SKILL_SEARCH_KEYWORDS:
        # 1. technology-search
        news, count = run_technology_search_skill(keyword, limit=15)
        all_news.extend(news)
        stats['technology_search'] += count
        time.sleep(0.3)

        # 2. 百度搜索
        news, count = run_baidu_search_skill(keyword, limit=10)
        all_news.extend(news)
        stats['baidu_search'] += count
        time.sleep(0.2)

        # 3. Google 搜索
        news, count = run_google_search_skill(keyword, limit=10)
        all_news.extend(news)
        stats['google_search'] += count
        time.sleep(0.2)

    # 去重
    seen_urls = set()
    unique_news = []
    for item in all_news:
        url = item.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_news.append(item)

    print(f"\n[Skill补充] 完成: technology-search返回{stats['technology_search']}条, "
          f"百度返回{stats['baidu_search']}条, Google返回{stats['google_search']}条")
    print(f"[Skill补充] 去重后: {len(unique_news)} 条")

    return unique_news, stats


# ============ 合并与去重 ============

def merge_official_and_skill(official_news: List[Dict], skill_news: List[Dict]) -> List[Dict]:
    """
    合并官网和Skill新闻

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


# ============ 主入口函数 ============

def fetch_ad_industry_news() -> Tuple[List[Dict], Dict]:
    """
    主函数：抓取自动驾驶行业资讯

    实现"官网优先 + Skill 补全"策略：
    1. 第一优先级：直接爬取重点自动驾驶公司官网
    2. 第二优先级：使用 Skills 补充媒体/聚合源

    Returns:
        (合并后的文章列表, 统计字典)
    """
    stats = {
        'official': {'success_count': 0, 'total_articles': 0},
        'skill': {'technology_search': 0, 'baidu_search': 0, 'google_search': 0},
        'merged': {'total_candidates': 0, 'after_filter': 0, 'ad_count': 0, 'ad_ratio': 0},
    }

    # ========== 步骤1：官网抓取（第一优先级）==========
    print("\n" + "=" * 60)
    print("[行业资讯抓取] 第一优先级：官网爬取")
    print("=" * 60)

    official_news, official_stats = fetch_all_official_ad_news()
    stats['official'] = official_stats

    print(f"\n[官网] 成功爬取 {official_stats['success_count']}/{len(AD_COMPANIES)} 个站点, "
          f"获得 {official_stats['total_articles']} 篇文章")

    # ========== 步骤2：Skill 补充（第二优先级）==========
    print("\n" + "=" * 60)
    print("[行业资讯抓取] 第二优先级：Skill 补充")
    print("=" * 60)

    skill_news, skill_stats = supplementary_search_ad_news()
    stats['skill'] = skill_stats

    print(f"\n[Skill补充] technology-search 返回 {skill_stats['technology_search']} 条, "
          f"百度返回 {skill_stats['baidu_search']} 条, Google返回 {skill_stats['google_search']} 条")

    # ========== 步骤3：合并去重 ===========
    print("\n" + "=" * 60)
    print("[行业资讯抓取] 合并去重")
    print("=" * 60)

    merged_news = merge_official_and_skill(official_news, skill_news)
    stats['merged']['total_candidates'] = len(merged_news)

    print(f"\n[合并去重] 官网 {len(official_news)} + Skill {len(skill_news)} = 候选 {len(merged_news)} 条")

    # ========== 步骤4：基础过滤（保留自动驾驶相关）==========
    print("\n" + "=" * 60)
    print("[行业资讯抓取] 自动驾驶相关性过滤")
    print("=" * 60)

    # 使用 content_filter 中的函数
    from processor.content_filter import is_autonomous_driving_news

    ad_news = []
    non_ad_news = []

    for item in merged_news:
        title = item.get('title', '')
        summary = item.get('summary', '') or ''
        if is_autonomous_driving_news(title, summary):
            ad_news.append(item)
        else:
            non_ad_news.append(item)

    stats['merged']['ad_count'] = len(ad_news)
    stats['merged']['ad_ratio'] = round(len(ad_news) / len(merged_news) * 100, 1) if merged_news else 0

    print(f"\n[过滤结果] 候选 {len(merged_news)} 条 -> 自动驾驶相关 {len(ad_news)} 条 (占比 {stats['merged']['ad_ratio']}%)")
    print(f"  - 自动驾驶新闻: {len(ad_news)} 条")
    print(f"  - 其他AI新闻: {len(non_ad_news)} 条（可与AI HOT数据合并）")

    # ========== 最终统计输出 ===========
    print("\n" + "=" * 60)
    print("[行业资讯抓取] 最终统计")
    print("=" * 60)
    print(f"[官网] 成功爬取 {stats['official']['success_count']} 个站点, "
          f"获得 {stats['official']['total_articles']} 篇文章")
    print(f"[Skill补充] technology-search 返回 {stats['skill']['technology_search']} 条, "
          f"百度返回 {stats['skill']['baidu_search']} 条, Google返回 {stats['skill']['google_search']} 条")
    print(f"[合并去重] 行业资讯候选 {stats['merged']['total_candidates']} 条, "
          f"自动驾驶相关 {stats['merged']['ad_count']} 条 (占比 {stats['merged']['ad_ratio']}%)")

    return ad_news, stats


def save_ad_news_to_file(news: List[Dict], date_str: str = None):
    """保存AD新闻到数据文件"""
    from pathlib import Path

    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')

    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)

    output_file = data_dir / f'ad_official_news_{date_str}.json'

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(news, f, ensure_ascii=False, indent=2)

    print(f"[保存] AD行业资讯已保存到: {output_file}")

    return str(output_file)


if __name__ == '__main__':
    print("=" * 60)
    print("自动驾驶行业资讯抓取 - 官网优先 + Skill 补全")
    print("=" * 60)

    # 测试抓取
    ad_news, stats = fetch_ad_industry_news()

    print(f"\n最终结果: {len(ad_news)} 条自动驾驶行业资讯")

    if ad_news:
        print("\n示例（前5条）:")
        for i, item in enumerate(ad_news[:5], 1):
            print(f"  {i}. [{item['source']}] {item['title'][:60]}...")

    # 保存
    save_ad_news_to_file(ad_news)