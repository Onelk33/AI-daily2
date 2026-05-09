#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""清理重复数据 - 确保每个条目只出现在一个分类中"""

import json
from pathlib import Path
from datetime import datetime

def clean_duplicates(date_str: str = None):
    """清理重复数据"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    data_file = Path(__file__).parent / "data" / "site_data" / f"{date_str}.json"
    
    if not data_file.exists():
        print(f"数据文件不存在: {data_file}")
        return
    
    with open(data_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 收集所有 URL
    all_urls = set()
    
    # 清理后的数据
    cleaned = {
        "policy": [],
        "news": [],
        "research": []
    }
    
    stats = {"removed_policy": 0, "removed_news": 0, "removed_research": 0}
    
    # 1. 先处理研报（优先级最高 - 因为研报是最专门的分类）
    for item in data.get("research", []):
        url = item.get("url", "")
        if url and url not in all_urls:
            cleaned["research"].append(item)
            all_urls.add(url)
        else:
            stats["removed_research"] += 1
    
    # 2. 处理政策（优先级第二）
    for item in data.get("policy", []):
        url = item.get("url", "")
        if url and url not in all_urls:
            cleaned["policy"].append(item)
            all_urls.add(url)
        else:
            stats["removed_policy"] += 1
    
    # 3. 处理行业资讯（优先级最低）
    for item in data.get("news", []):
        url = item.get("url", "")
        if url and url not in all_urls:
            cleaned["news"].append(item)
            all_urls.add(url)
        else:
            stats["removed_news"] += 1
    
    # 添加统计信息
    cleaned["stats"] = {
        "policy_count": len(cleaned["policy"]),
        "news_count": len(cleaned["news"]),
        "research_count": len(cleaned["research"]),
        "date": date_str
    }
    
    # 保存清理后的数据
    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)
    
    print(f"\n数据清理完成!")
    print(f"  政策动向: {len(cleaned['policy'])} 条 (移除重复 {stats['removed_policy']} 条)")
    print(f"  行业资讯: {len(cleaned['news'])} 条 (移除重复 {stats['removed_news']} 条)")
    print(f"  每日研报: {len(cleaned['research'])} 条 (移除重复 {stats['removed_research']} 条)")
    
    return cleaned

if __name__ == "__main__":
    clean_duplicates()