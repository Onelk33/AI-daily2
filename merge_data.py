#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""合并所有数据源并去重"""

import json
from pathlib import Path
from datetime import datetime

def merge_and_dedupe(date_str: str = None):
    """合并所有数据源并去重"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    data_dir = Path("data")
    
    # 收集所有数据
    policy_items = []
    news_items = []
    research_items = []
    
    # 1. 加载研报数据（最高优先级）
    research_file = data_dir / "global_research_reports.json"
    if research_file.exists():
        with open(research_file, 'r', encoding='utf-8') as f:
            research_items = json.load(f)
        print(f"研报数据: {len(research_items)} 条")
    
    # 2. 加载 AIHOT 数据
    aihot_file = data_dir / "aihot_industry.json"
    if aihot_file.exists():
        with open(aihot_file, 'r', encoding='utf-8') as f:
            aihot_data = json.load(f)
            if isinstance(aihot_data, list):
                news_items.extend(aihot_data)
        print(f"AIHOT 行业: {len(aihot_data) if isinstance(aihot_data, list) else 0} 条")
    
    aihot_policy_file = data_dir / "aihot_policy.json"
    if aihot_policy_file.exists():
        with open(aihot_policy_file, 'r', encoding='utf-8') as f:
            aihot_policy = json.load(f)
            if isinstance(aihot_policy, list):
                policy_items.extend(aihot_policy)
        print(f"AIHOT 政策: {len(aihot_policy) if isinstance(aihot_policy, list) else 0} 条")
    
    # 3. 加载 RSS 缓存数据
    for cache_file in data_dir.glob("*.json"):
        if cache_file.name in ["global_research_reports.json", "aihot_industry.json", "aihot_policy.json", "site_data"]:
            continue
        if "cache" not in cache_file.name and "research_candidates" not in cache_file.name:
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    items = json.load(f)
                if isinstance(items, list):
                    for item in items:
                        title = item.get('title', '').lower()
                        # 简单判断分类
                        if any(kw in title for kw in ['政策', '法规', '标准', '监管', '立法', 'regulation', 'policy', 'law']):
                            policy_items.append(item)
                        else:
                            news_items.append(item)
            except:
                pass
    
    print(f"总数据: 政策 {len(policy_items)}, 行业 {len(news_items)}, 研报 {len(research_items)}")
    
    # 去重
    all_urls = set()
    cleaned = {
        "policy": [],
        "news": [],
        "research": []
    }
    
    # 研报优先
    for item in research_items:
        url = item.get("url", "")
        if url and url not in all_urls:
            cleaned["research"].append(item)
            all_urls.add(url)
    
    # 政策第二
    for item in policy_items:
        url = item.get("url", "")
        if url and url not in all_urls:
            cleaned["policy"].append(item)
            all_urls.add(url)
    
    # 行业资讯最后
    for item in news_items:
        url = item.get("url", "")
        if url and url not in all_urls:
            cleaned["news"].append(item)
            all_urls.add(url)
    
    # 添加统计
    cleaned["stats"] = {
        "policy_count": len(cleaned["policy"]),
        "news_count": len(cleaned["news"]),
        "research_count": len(cleaned["research"]),
        "date": date_str
    }
    
    # 保存
    output_file = data_dir / "site_data" / f"{date_str}.json"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    
    print(f"\n合并完成并已保存到: {output_file}")
    print(f"  政策动向: {len(cleaned['policy'])} 条")
    print(f"  行业资讯: {len(cleaned['news'])} 条")
    print(f"  每日研报: {len(cleaned['research'])} 篇")
    
    return cleaned

if __name__ == "__main__":
    merge_and_dedupe()