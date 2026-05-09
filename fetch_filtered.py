#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
获取并过滤数据 v7-official-first
- 政策动向：内容主体优先（政府为主体，不限来源）+ 搜索扩展，仅当天/前一天
- 行业资讯：官网优先+Skill补全，AD/AI平衡，40% AD配额，重大AD事件强制保留
- 研报：黑名单过滤+四级链接强制验证（强化版）
"""

import json
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent))

from scrapers.aihot import AIHOTScraper
from scrapers.gov_policy import fetch_gov_policies
from scrapers.company_official import (
    fetch_all_official_ad_news,
    supplementary_search_ad_news,
    merge_official_and_skill,
)
from processor.content_filter import (
    clean_policy_items,
    filter_news,
    filter_reports
)
from processor.policy_search import (
    filter_policy_candidates,
    get_search_keywords_for_today,
)


def load_lessons_learned():
    """读取踩坑记录，打印提醒"""
    lessons_path = Path.home() / '.codex' / 'skills' / 'researcher-handbook' / 'LESSONS_LEARNED.md'
    if not lessons_path.exists():
        print("[提醒] LESSONS_LEARNED.md 未找到，跳过")
        return

    print("\n" + "=" * 60)
    print("[研究员手册] 读取 LESSONS_LEARNED.md 踩坑记录")
    print("=" * 60)

    try:
        with open(lessons_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取关键提醒
        reminders = []
        if '时效性红线' in content:
            reminders.append("时效性：只保留昨天/今天的文章")
        if '英文必须翻译' in content:
            reminders.append("翻译：所有英文标题必须翻译中文")
        if 'Nuro' in content:
            reminders.append("必查：Nuro许可动态、Tesla Robotaxi、Waymo扩张")
        if '坏来源' in content:
            reminders.append("来源：CB Insights等坏来源已过滤")

        for r in reminders:
            print(f"  - {r}")

        print("=" * 60 + "\n")
    except Exception as e:
        print(f"[提醒] 读取 LESSONS_LEARNED.md 失败: {e}")

# 搜索统计
search_stats = {
    'baidu_total': 0,
    'google_total': 0,
    'baidu_passed': 0,
    'google_passed': 0,
}


def search_policies_baidu() -> list:
    """加载搜索到的政策信息"""
    from pathlib import Path
    from datetime import datetime

    date_str = datetime.now().strftime('%Y-%m-%d')
    search_file = Path(f'data/search_policies/{date_str}.json')

    if search_file.exists():
        with open(search_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        print(f"  加载搜索结果: {len(results)} 条")
        return results

    keywords = get_search_keywords_for_today()
    print(f"\n[百度搜索] 待搜索关键词 ({len(keywords)} 个):")
    for i, kw in enumerate(keywords[:5], 1):
        print(f"  {i}. {kw}")
    print("  提示: 搜索结果文件不存在，请先执行搜索")
    return []


def search_policies_google() -> list:
    """Google 搜索政策信息"""
    return []


def supplementary_ad_search(date_str: str) -> list:
    """
    补充搜索自动驾驶新闻
    当AD内容不足时，尝试加载预存的补充数据或触发外部搜索标记
    """
    # 尝试加载预存的补充AD数据（可由Agent通过skill搜索后提供）
    supp_file = Path(f'data/supplementary_ad/{date_str}.json')
    if supp_file.exists():
        try:
            with open(supp_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            print(f"  加载补充AD数据: {len(results)} 条")
            return results
        except Exception as e:
            print(f"  加载补充AD数据失败: {e}")

    # 如果没有预存数据，返回空列表（由上层Agent触发skill搜索）
    return []


def print_search_summary():
    """打印搜索统计摘要"""
    total = search_stats['baidu_total'] + search_stats['google_total']
    passed = search_stats['baidu_passed'] + search_stats['google_passed']

    if total > 0:
        print("\n[搜索统计]")
        print(f"  百度搜索: {search_stats['baidu_total']} 条 -> 保留 {search_stats['baidu_passed']} 条")
        print(f"  Google搜索: {search_stats['google_total']} 条 -> 保留 {search_stats['google_passed']} 条")
        print(f"  总计: {total} 条 -> 保留 {passed} 条")


def fetch_and_filter(date_str: str = None, skip_url_check: bool = False, include_gov: bool = True, include_search: bool = True):
    """获取数据并严格过滤"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    data_dir = Path("data")
    site_data_file = data_dir / "site_data" / f"{date_str}.json"
    research_file = data_dir / "global_research_reports.json"

    print("=" * 60)
    print(f"[数据获取与过滤] {date_str}")
    print("=" * 60)

    # 读取踩坑记录
    load_lessons_learned()

    # 1. 获取政府官网政策（优先级最高）
    gov_policy_data = []
    if include_gov:
        print("\n[1/5] 获取政府官网政策...")
        try:
            gov_policy_data = fetch_gov_policies()
            print(f"  政府官网政策: {len(gov_policy_data)} 条")
        except Exception as e:
            print(f"  政府官网爬取失败: {str(e)[:50]}")

    # 2. 搜索扩展（百度 + Google）
    search_policy_data = []
    if include_search:
        print("\n[2/5] 搜索政策新闻...")
        baidu_results = search_policies_baidu()
        if baidu_results:
            filtered_baidu = filter_policy_candidates(baidu_results)
            search_policy_data.extend(filtered_baidu)
            search_stats['baidu_total'] = len(baidu_results)
            search_stats['baidu_passed'] = len(filtered_baidu)

        google_results = search_policies_google()
        if google_results:
            filtered_google = filter_policy_candidates(google_results)
            search_policy_data.extend(filtered_google)
            search_stats['google_total'] = len(google_results)
            search_stats['google_passed'] = len(filtered_google)

    # 3. 第一优先级：抓取自动驾驶公司官网新闻
    print("\n[3/5] 第一优先级：抓取自动驾驶公司官网...")
    official_ad_news = []
    try:
        official_ad_news = fetch_all_official_ad_news()
    except Exception as e:
        print(f"  官网抓取失败: {str(e)[:60]}")

    # 4. 第二优先级：Skill 补充搜索 AD 新闻
    print("\n[4/5] 第二优先级：Skill 补充搜索 AD 新闻...")
    skill_ad_news = []
    try:
        skill_ad_news = supplementary_search_ad_news()
    except Exception as e:
        print(f"  Skill 搜索失败: {str(e)[:60]}")

    # 合并官网和 Skill 新闻（官网优先）
    combined_ad_news = merge_official_and_skill(official_ad_news, skill_ad_news)
    print(f"\n[AD新闻合并] 官网 {len(official_ad_news)} + Skill {len(skill_ad_news)} -> 去重后 {len(combined_ad_news)} 条")

    # 5. 获取 AIHOT 数据（AI + 通用行业资讯）
    print("\n[5/5] 获取 AIHOT 数据...")
    scraper = AIHOTScraper()

    industry_items = scraper.fetch_industry_news(days=2)
    print(f"  行业资讯原始: {len(industry_items)} 条 (最近2天)")

    policy_items = scraper.fetch_policy_news(days=2)
    print(f"  政策动向原始: {len(policy_items)} 条 (最近2天)")

    # 6. 加载研报数据
    print("\n[6/7] 加载研报数据...")
    research_items = []
    if research_file.exists():
        with open(research_file, 'r', encoding='utf-8') as f:
            research_items = json.load(f)
    print(f"  研报原始: {len(research_items)} 篇")

    # 7. 转换格式并合并
    news_data = []
    for item in industry_items:
        news_data.append({
            "title": item.title,
            "summary": item.summary or "",
            "source": item.source,
            "url": item.url,
            "country": item.category or "industry",
            "date": item.published_at or "",
            "keywords": []
        })

    # 合并 AD 新闻（官网+Skill 优先）
    print(f"\n[合并] AIHOT 行业资讯 {len(news_data)} + AD 补充 {len(combined_ad_news)} 条")
    existing_urls = {item.get('url', '') for item in news_data}
    ad_added = 0
    for item in combined_ad_news:
        url = item.get('url', '')
        if url and url not in existing_urls:
            news_data.append(item)
            existing_urls.add(url)
            ad_added += 1
    print(f"  -> 实际新增 AD 新闻: {ad_added} 条, 候选池总计: {len(news_data)} 条")

    policy_data = []
    for item in policy_items:
        policy_data.append({
            "title": item.title,
            "summary": item.summary or "",
            "source": item.source,
            "url": item.url,
            "country": item.category or "policy",
            "date": item.published_at or "",
            "keywords": []
        })

    policy_data.extend(gov_policy_data)
    policy_data.extend(search_policy_data)

    # 8. 执行过滤
    print("\n[8/8] 执行严格过滤...")

    # 8.1 清洗政策动向（内容主体优先策略，仅当天/前一天）
    filtered_policy = clean_policy_items(policy_data)

    # 8.2 过滤行业资讯，分离国外政策，支持AD配额
    filtered_news, foreign_policy, news_stats = filter_news(news_data)

    # 8.2a AD补充搜索触发（如果仍然不足）
    if news_stats.get('need_supplement'):
        print("\n[AD补充搜索] 触发补充搜索...")
        supplementary_news = supplementary_ad_search(date_str)
        if supplementary_news:
            supp_filtered, supp_foreign, supp_stats = filter_news(supplementary_news)
            existing_urls = {item.get('url', '') for item in filtered_news}
            for item in supp_filtered:
                url = item.get('url', '')
                if url and url not in existing_urls:
                    filtered_news.append(item)
                    existing_urls.add(url)
            print(f"  补充后AD新闻: {supp_stats.get('ad_count', 0)} 条")

    # 8.3 过滤研报（四级链接强制验证）
    filtered_research = filter_reports(research_items, check_url=not skip_url_check)

    print(f"\n[过滤统计]")
    print(f"  政策动向: {len(policy_data)} -> {len(filtered_policy)}")
    print(f"  行业资讯: {len(news_data)} -> {len(filtered_news)} + {len(foreign_policy)}(国外政策)")
    print(f"  研报: {len(research_items)} -> {len(filtered_research)}")

    # 9. 去重合并
    print("\n[9/9] 去重合并...")
    all_urls = set()
    merged = {"policy": [], "news": [], "research": []}

    # 研报优先
    for item in filtered_research:
        url = item.get("url", "")
        if url and url not in all_urls:
            merged["research"].append(item)
            all_urls.add(url)

    # 政策
    for item in filtered_policy:
        url = item.get("url", "")
        if url and url not in all_urls:
            merged["policy"].append(item)
            all_urls.add(url)

    # 行业资讯（包含国外政策）
    for item in filtered_news + foreign_policy:
        url = item.get("url", "")
        if url and url not in all_urls:
            merged["news"].append(item)
            all_urls.add(url)

    # 统计
    gov_count = sum(1 for p in merged['policy'] if p.get('policy_source_type') == '政府官网')
    media_count = sum(1 for p in merged['policy'] if p.get('policy_source_type') == '权威媒体')
    other_count = sum(1 for p in merged['policy'] if p.get('policy_source_type') == '其他媒体')

    # AD/AI 比例统计
    ad_news_count = news_stats.get('ad_count', 0)
    ai_news_count = news_stats.get('ai_count', 0)
    ad_ratio = news_stats.get('ad_ratio', 0)
    need_supplement = news_stats.get('need_supplement', False)

    merged["stats"] = {
        "policy_count": len(merged["policy"]),
        "gov_policy_count": gov_count,
        "media_policy_count": media_count,
        "other_policy_count": other_count,
        "news_count": len(merged["news"]),
        "research_count": len(merged["research"]),
        "foreign_policy_count": len(foreign_policy),
        "ad_news_count": ad_news_count,
        "ai_news_count": ai_news_count,
        "ad_ratio": ad_ratio,
        "need_ad_supplement": need_supplement,
        "date": date_str
    }

    # 保存
    site_data_file.parent.mkdir(parents=True, exist_ok=True)
    with open(site_data_file, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    # 打印搜索统计
    print_search_summary()

    print("\n" + "=" * 60)
    print("[最终结果]")
    print(f"  政策动向: {len(merged['policy'])} 条")
    if len(merged['policy']) == 0:
        print("    - 当日无重大政策发布")
    else:
        print(f"    - 政府官网: {gov_count} 条")
        print(f"    - 权威媒体: {media_count} 条")
        print(f"    - 其他媒体: {other_count} 条")
    print(f"  行业资讯: {len(merged['news'])} 条 (含 {len(foreign_policy)} 条国外政策)")
    print(f"    - AD新闻: {ad_news_count} 条, AI新闻: {ai_news_count} 条 (AD占比: {ad_ratio}%)")
    if need_supplement:
        print(f"    ⚠️ AD内容不足，建议通过skill补充搜索")
    print(f"  每日研报: {len(merged['research'])} 篇 (已验证)")
    print(f"  总计: {sum([len(merged['policy']), len(merged['news']), len(merged['research'])])} 条")
    print(f"  保存到: {site_data_file}")
    print("=" * 60)

    return merged


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', help='日期 YYYY-MM-DD')
    parser.add_argument('--skip-url-check', action='store_true', help='跳过URL验证')
    parser.add_argument('--no-gov', action='store_true', help='不爬取政府官网')
    parser.add_argument('--no-search', action='store_true', help='不执行搜索扩展')
    args = parser.parse_args()

    fetch_and_filter(args.date, args.skip_url_check,
                    include_gov=not args.no_gov,
                    include_search=not args.no_search)
