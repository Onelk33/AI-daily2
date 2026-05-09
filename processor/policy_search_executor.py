#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
政策搜索执行脚本
使用 web_search 工具主动搜索政策信息
"""
import json
from datetime import datetime
from pathlib import Path

# 搜索关键词列表
SEARCH_KEYWORDS = [
    '工信部 人工智能 政策 2026',
    '国务院 自动驾驶 政策',
    '发改委 智能汽车 通知',
    '网信办 算法 管理 办法',
    '科技部 大模型 规划',
]

def create_policy_item(title: str, url: str, content: str, keyword: str) -> dict:
    """从搜索结果创建政策条目"""
    # 提取摘要（取前300字）
    summary = content[:500] if content else ""
    
    # 提取来源
    source = "网络搜索"
    if '工信部' in title or '工业和信息化部' in title:
        source = "工信部"
    elif '国务院' in title:
        source = "国务院"
    elif '发改委' in title:
        source = "发改委"
    elif '网信办' in title:
        source = "网信办"
    
    return {
        'title': title,
        'summary': summary,
        'source': source,
        'url': url,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'search_keyword': keyword,
        'policy_source_type': '搜索获取',
    }


def save_search_policies(items: list, date_str: str = None):
    """保存搜索到的政策"""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    data_dir = Path('data')
    search_file = data_dir / 'search_policies' / f'{date_str}.json'
    search_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(search_file, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    
    print(f"[搜索政策] 保存 {len(items)} 条到 {search_file}")
    return search_file


def load_search_policies(date_str: str = None) -> list:
    """加载搜索到的政策"""
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    data_dir = Path('data')
    search_file = data_dir / 'search_policies' / f'{date_str}.json'
    
    if search_file.exists():
        with open(search_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


if __name__ == '__main__':
    print("政策搜索模块")
    print("使用方法: python -m processor.policy_search_executor")
    print("或在 fetch_filtered.py 中调用 load_search_policies()")