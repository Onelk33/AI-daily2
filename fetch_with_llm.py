"""
基于 DuckDuckGo 搜索 + DeepSeek LLM 的日报生成脚本
将 baidu-search / aihot / technology-search 的 Skill 能力定义直接注入 system prompt
"""
import os
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import requests
from duckduckgo_search import DDGS

# 搜索关键词
POLICY_QUERIES = [
    "site:gov.cn 自动驾驶 智能网联汽车",
    "site:xinhuanet.com 人工智能 政策",
    "site:people.com.cn 自动驾驶 监管",
    "工信部 自动驾驶 智能网联汽车 政策",
    "网信办 人工智能 规范 意见",
]

NEWS_QUERIES = [
    "Robotaxi 商业化 运营 最新",
    "特斯拉 FSD Robotaxi 最新进展",
    "英伟达 AI 投资 芯片 最新",
    "OpenAI Anthropic 大模型 融资 最新",
    "百度 Apollo 萝卜快跑 自动驾驶 最新",
    "华为 智能驾驶 乾崑 最新",
    "字节跳动 AI 大模型 豆包 最新",
    "小马智行 文远知行 自动驾驶 最新",
    "自动驾驶 L3 L4 量产 最新",
]

RESEARCH_QUERIES = [
    "自动驾驶 研报 投资策略 2026",
    "智能驾驶 深度研究 券商 2026",
    "Robotaxi 研究报告 行业分析 2026",
    "AI 大模型 行业报告 券商 2026",
    "site:stcn.com 自动驾驶 研报",
    "site:cs.com.cn 智能驾驶 研究",
    "site:eastmoney.com 自动驾驶 研报",
]

SYSTEM_PROMPT = """你是一位专业的 AI/自动驾驶行业日报编辑，服务于"跟进时事+积累素材"的双重目标。

你收到三组搜索结果：
1. 【政策素材】来自政府网站和官方媒体的搜索结果
2. 【行业素材】来自科技/财经媒体的搜索结果
3. 【研报素材】来自券商、研报平台的搜索结果（包含真实的研报标题和摘要）

你的任务：

1. 【政策动向】从政策素材中筛选最近48小时内发布的政府政策、法规、实施意见。每条必须主体为政府部门，有明确政策条文。如果没有近期政策，policy为空数组。

2. 【行业资讯】从行业素材中筛选与AI、自动驾驶、大模型、芯片相关的重大企业动态、技术突破、投融资、商业化进展。优先收录对百度战略有参考价值的内容。严格排除48小时以前的旧闻。

3. 【研报】从研报素材中提取真正的券商研报内容。不要自己编造！必须从搜索结果中找到真实的研报标题、机构名称、核心观点。如果搜索结果中没有研报素材，可以基于当天行业素材写一份简评，但标题要注明"行业简评"而非"研报"。

时效性铁律：严格只收录最近48小时内的内容。如果搜索结果中某条内容的发布时间明显早于这两天，坚决排除。

选稿标准：每条内容必须能回答"这对百度有什么意义"或"这能成为研讨会的什么论据"。

输出格式必须是标准 JSON，不要有任何 markdown 代码块标记：
{
  "policy": [
    {"title": "...", "summary": "...", "source": "...", "url": "...", "date": "YYYY-MM-DD", "country": "中国/美国/国际"}
  ],
  "news": [...],
  "research": [
    {"title": "...", "summary": "...", "source": "...", "url": "...", "date": "YYYY-MM-DD", "country": "中国"}
  ],
  "stats": {"policy_count": 0, "news_count": 0, "research_count": 0, "paywall_skipped": 0}
}

today_date: {today_date}
"""


def search_duckduckgo(queries: List[str], max_results: int = 5) -> List[Dict]:
    """使用 DuckDuckGo 搜索"""
    all_results = []
    with DDGS() as ddgs:
        for q in queries:
            try:
                results = ddgs.text(q, max_results=max_results)
                for r in results:
                    all_results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "summary": r.get("body", "")[:400],
                    })
            except Exception as e:
                print(f"[WARN] DDG search failed for '{q}': {e}")
    return all_results


def generate_daily_report(policy_results: List[Dict], news_results: List[Dict], research_results: List[Dict], target_date: str, api_key: str) -> Dict:
    """调用 DeepSeek API 生成日报"""
    
    def fmt_items(items, label):
        lines = [f"=== {label} ==="]
        for i, r in enumerate(items[:20], 1):
            lines.append(f"[{i}] {r['title']}\nURL: {r['url']}\n摘要: {r['summary']}")
        return "\n\n".join(lines)
    
    material = "\n\n".join([
        fmt_items(policy_results, "政策素材"),
        fmt_items(news_results, "行业素材"),
        fmt_items(research_results, "研报素材"),
    ])
    
    system = SYSTEM_PROMPT.replace("{today_date}", target_date)
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"以下是今天搜索到的原始素材，请生成日报：\n\n{material}"}
        ],
        "temperature": 0.3,
        "max_tokens": 4000,
        "response_format": {"type": "json_object"}
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    resp = requests.post(
        "https://api.deepseek.com/chat/completions",
        json=payload,
        headers=headers,
        timeout=120
    )
    resp.raise_for_status()
    
    content = resp.json()["choices"][0]["message"]["content"]
    data = json.loads(content)
    return data


def save_data(data: Dict, target_date: str):
    output_dir = Path("data/site_data")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{target_date}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[INFO] Saved to {output_file}")


def main():
    target_date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    
    if not api_key:
        print("[ERROR] DEEPSEEK_API_KEY not set")
        sys.exit(1)
    
    print(f"[INFO] Searching for {target_date}...")
    
    policy_results = search_duckduckgo(POLICY_QUERIES, max_results=5)
    news_results = search_duckduckgo(NEWS_QUERIES, max_results=3)
    research_results = search_duckduckgo(RESEARCH_QUERIES, max_results=5)
    
    print(f"[INFO] Policy: {len(policy_results)}, News: {len(news_results)}, Research: {len(research_results)}")
    
    all_results = policy_results + news_results + research_results
    
    if not all_results:
        print("[WARN] No search results, falling back to empty report")
        data = {
            "policy": [], "news": [], "research": [],
            "stats": {"policy_count": 0, "news_count": 0, "research_count": 0, "paywall_skipped": 0}
        }
    else:
        print(f"[INFO] Generating report with DeepSeek...")
        data = generate_daily_report(policy_results, news_results, research_results, target_date, api_key)
    
    if "stats" not in data:
        data["stats"] = {
            "policy_count": len(data.get("policy", [])),
            "news_count": len(data.get("news", [])),
            "research_count": len(data.get("research", [])),
            "paywall_skipped": 0
        }
    
    save_data(data, target_date)
    print(f"[INFO] Done: policy={data['stats']['policy_count']}, news={data['stats']['news_count']}, research={data['stats']['research_count']}")


if __name__ == "__main__":
    main()
