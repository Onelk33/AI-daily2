"""
基于 Tavily Search API 的日报数据抓取脚本
替代旧的爬虫方案，解决时效性和稳定性问题
"""
import os
import re
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict

from tavily import TavilyClient

# 搜索关键词配置
SEARCH_QUERIES = {
    "policy": [
        "site:gov.cn 自动驾驶 智能网联汽车",
        "site:xinhuanet.com 人工智能 政策",
        "site:people.com.cn 自动驾驶 监管",
        "site:mofcom.gov.cn 人工智能 智能网联",
        "工信部 自动驾驶 智能网联汽车 政策",
        "网信办 人工智能 规范 意见",
        "自动驾驶 法规 新规 发布",
    ],
    "news": [
        "Robotaxi 商业化 运营 2026",
        "特斯拉 FSD Robotaxi 2026",
        "Waymo 自动驾驶 运营 2026",
        "英伟达 AI 投资 2026",
        "OpenAI Anthropic 融资 估值 2026",
        "百度 Apollo 萝卜快跑 自动驾驶 2026",
        "小马智行 文远知行 自动驾驶 2026",
        "华为 智能驾驶 乾崑 2026",
        "字节跳动 AI 大模型 2026",
        "自动驾驶 L3 L4 量产 2026",
    ],
    "research": [
        "自动驾驶 研报 投资策略 2026",
        "Robotaxi 研究报告 行业分析 2026",
        "智能驾驶 深度研究 券商 2026",
        "AI 大模型 行业报告 2026",
    ],
}


def get_target_date() -> str:
    """获取目标日期（今天）"""
    return datetime.now().strftime("%Y-%m-%d")


def get_date_patterns(target_date: str) -> List[str]:
    """生成目标日期和昨天的各种匹配模式"""
    dt = datetime.strptime(target_date, "%Y-%m-%d")
    yesterday = dt - timedelta(days=1)

    patterns = []
    for d in [dt, yesterday]:
        y, m, day = d.year, d.month, d.day
        patterns.extend([
            f"{y}-{m:02d}-{day:02d}",       # 2026-05-11
            f"{y}年{m}月{day}日",            # 2026年5月11日
            f"{m}月{day}日",                 # 5月11日
            f"{m:02d}-{day:02d}",            # 05-11
            f"{y}{m:02d}{day:02d}",          # 20260511
            f"{y}/{m:02d}/{day:02d}",        # 2026/05/11
        ])
    return patterns


def is_recent(text: str, target_date: str) -> bool:
    """检查文本是否包含目标日期或昨天的日期标记"""
    if not text:
        return False
    patterns = get_date_patterns(target_date)
    text_lower = text.lower()
    return any(p in text_lower for p in patterns)


def is_policy_item(item: Dict) -> bool:
    """判断是否为政策类"""
    url = item.get("url", "").lower()
    title = item.get("title", "")
    policy_domains = [
        "gov.cn", "xinhuanet.com", "people.com.cn", "mofcom.gov.cn",
        "miit.gov.cn", "cac.gov.cn", "ndrc.gov.cn",
    ]
    policy_keywords = ["政策", "意见", "通知", "法规", "印发", "出台", "细则", "规范", "试行", "管理办法"]
    return any(d in url for d in policy_domains) or any(k in title for k in policy_keywords)


def is_research_item(item: Dict) -> bool:
    """判断是否为研报类"""
    title = item.get("title", "")
    url = item.get("url", "").lower()
    research_keywords = ["研报", "研究报告", "分析报告", "投资策略", "深度研究", "行业报告", "证券研究"]
    return any(k in title for k in research_keywords) or "pdf.dfcfw.com" in url


def deduplicate(items: List[Dict]) -> List[Dict]:
    """按 URL 去重"""
    seen = set()
    result = []
    for item in items:
        url = item.get("url", "")
        if url and url not in seen:
            seen.add(url)
            result.append(item)
    return result


def search_with_tavily(client: TavilyClient, query: str, target_date: str) -> List[Dict]:
    """调用 Tavily API 搜索并筛选近期结果"""
    try:
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=10,
            include_answer=False,
        )
        results = response.get("results", [])

        filtered = []
        for r in results:
            title = r.get("title", "")
            content = r.get("content", "")
            url = r.get("url", "")
            # 组合标题+摘要+URL 做日期匹配
            combined = f"{title} {content} {url}"
            if is_recent(combined, target_date):
                filtered.append({
                    "title": title,
                    "url": url,
                    "summary": content[:500] if content else "",
                    "source": extract_source(url),
                    "date": target_date,
                    "country": "中国" if ".cn" in url else "美国" if ".com" in url else "国际",
                })
        return filtered
    except Exception as e:
        print(f"[ERROR] Tavily search failed for '{query}': {e}")
        return []


def extract_source(url: str) -> str:
    """从 URL 提取来源域名"""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace("www.", "")
        source_map = {
            "xinhuanet.com": "新华网",
            "people.com.cn": "人民网",
            "sina.com.cn": "新浪财经",
            "qq.com": "腾讯新闻",
            "163.com": "网易新闻",
            "sohu.com": "搜狐网",
            "ifeng.com": "凤凰网",
            "36kr.com": "36氪",
            "cls.cn": "财联社",
            "stcn.com": "证券时报",
            "cs.com.cn": "中证网",
            "eastmoney.com": "东方财富",
            "gov.cn": "政府网站",
        }
        for k, v in source_map.items():
            if k in domain:
                return v
        return domain
    except:
        return "未知来源"


def fetch_daily_data(target_date: str = None) -> Dict:
    """抓取日报数据"""
    if target_date is None:
        target_date = get_target_date()

    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        print("[ERROR] TAVILY_API_KEY not set")
        sys.exit(1)

    client = TavilyClient(api_key=api_key)

    all_policy = []
    all_news = []
    all_research = []

    print(f"[INFO] Fetching daily report for {target_date}")

    # 搜索政策
    for q in SEARCH_QUERIES["policy"]:
        results = search_with_tavily(client, q, target_date)
        for r in results:
            if is_policy_item(r):
                all_policy.append(r)
            else:
                all_news.append(r)
        print(f"[INFO] Policy query '{q}' -> {len(results)} recent results")

    # 搜索行业资讯
    for q in SEARCH_QUERIES["news"]:
        results = search_with_tavily(client, q, target_date)
        for r in results:
            if is_research_item(r):
                all_research.append(r)
            else:
                all_news.append(r)
        print(f"[INFO] News query '{q}' -> {len(results)} recent results")

    # 搜索研报
    for q in SEARCH_QUERIES["research"]:
        results = search_with_tavily(client, q, target_date)
        for r in results:
            if is_research_item(r):
                all_research.append(r)
            else:
                all_news.append(r)
        print(f"[INFO] Research query '{q}' -> {len(results)} recent results")

    # 去重
    all_policy = deduplicate(all_policy)
    all_news = deduplicate(all_news)
    all_research = deduplicate(all_research)

    # 限制条数
    all_policy = all_policy[:8]
    all_news = all_news[:12]
    all_research = all_research[:5]

    data = {
        "policy": all_policy,
        "news": all_news,
        "research": all_research,
        "stats": {
            "policy_count": len(all_policy),
            "news_count": len(all_news),
            "research_count": len(all_research),
            "paywall_skipped": 0,
        }
    }

    return data


def save_data(data: Dict, target_date: str = None):
    """保存数据到文件"""
    if target_date is None:
        target_date = get_target_date()

    output_dir = Path("data/site_data")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f"{target_date}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[INFO] Saved to {output_file}")
    print(f"[INFO] Policy: {data['stats']['policy_count']}, News: {data['stats']['news_count']}, Research: {data['stats']['research_count']}")


if __name__ == "__main__":
    target_date = sys.argv[1] if len(sys.argv) > 1 else None
    data = fetch_daily_data(target_date)
    save_data(data, target_date)
