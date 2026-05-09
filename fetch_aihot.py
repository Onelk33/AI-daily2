#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""直接获取 AIHOT 数据并合并到 site_data"""

import json
from pathlib import Path
from datetime import datetime
import sys

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.aihot import AIHOTScraper

def fetch_and_merge(date_str: str = None):
    """获取 AIHOT 数据并合并"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    data_dir = Path("data")
    site_data_file = data_dir / "site_data" / f"{date_str}.json"
    research_file = data_dir / "global_research_reports.json"
    
    # 加载现有数据
    if site_data_file.exists():
        with open(site_data_file, 'r', encoding='utf-8') as f:
            site_data = json.load(f)
    else:
        site_data = {"policy": [], "news": [], "research": [], "stats": {}}
    
    # 加载研报数据
    research_items = []
    if research_file.exists():
        with open(research_file, 'r', encoding='utf-8') as f:
            research_items = json.load(f)
    
    # 获取 AIHOT 数据
    print("正在获取 AIHOT 数据...")
    scraper = AIHOTScraper()
    
    # 行业资讯
    industry_items = scraper.fetch_industry_news(days=7)
    print(f"AIHOT 行业资讯: {len(industry_items)} 条")
    
    # 政策动向
    policy_items = scraper.fetch_policy_news(days=7)
    print(f"AIHOT 政策动向: {len(policy_items)} 条")
    
    # 转换为字典格式
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
    
    # 合并数据 - 先收集所有 URL
    all_urls = set()
    merged = {"policy": [], "news": [], "research": []}
    
    # 1. 研报优先
    for item in research_items:
        url = item.get("url", "")
        if url and url not in all_urls:
            merged["research"].append(item)
            all_urls.add(url)
    
    # 2. 政策
    for item in policy_data:
        url = item.get("url", "")
        if url and url not in all_urls:
            merged["policy"].append(item)
            all_urls.add(url)
    
    # 3. 行业资讯
    for item in news_data:
        url = item.get("url", "")
        if url and url not in all_urls:
            merged["news"].append(item)
            all_urls.add(url)
    
    # 添加统计
    merged["stats"] = {
        "policy_count": len(merged["policy"]),
        "news_count": len(merged["news"]),
        "research_count": len(merged["research"]),
        "date": date_str
    }
    
    # 保存
    site_data_file.parent.mkdir(parents=True, exist_ok=True)
    with open(site_data_file, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    
    print(f"\n数据合并完成!")
    print(f"  政策动向: {len(merged['policy'])} 条")
    print(f"  行业资讯: {len(merged['news'])} 条")
    print(f"  每日研报: {len(merged['research'])} 篇")
    print(f"保存到: {site_data_file}")
    
    return merged

if __name__ == "__main__":
    fetch_and_merge()