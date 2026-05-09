#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""重新构建网站（使用已清理的数据）"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from build_site import SiteBuilder, SiteConfig

def rebuild_site(date_str: str = None):
    """使用清理后的数据重新构建网站"""
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    # 从环境变量获取网站URL
    site_url = os.environ.get('SITE_URL', '')
    
    # 配置网站
    site_config = SiteConfig(
        site_name="AI日报",
        site_description="每日政策动向、行业资讯与全球研报",
        base_url=site_url,
        timezone="UTC+8"
    )
    
    # 创建网站构建器
    builder = SiteBuilder(docs_dir="docs", config=site_config)
    
    # 构建网站
    builder.build_all(date_str)
    
    # 读取并显示统计
    data_file = Path("data/site_data") / f"{date_str}.json"
    if data_file.exists():
        import json
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n网站统计:")
        print(f"  政策动向: {len(data.get('policy', []))} 条")
        print(f"  行业资讯: {len(data.get('news', []))} 条")
        print(f"  每日研报: {len(data.get('research', []))} 篇")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('date', nargs='?', help='日期 YYYY-MM-DD')
    args = parser.parse_args()
    rebuild_site(args.date)