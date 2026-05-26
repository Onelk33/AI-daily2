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
from ddgs import DDGS

# 搜索关键词
POLICY_QUERIES = [
    "自动驾驶 智能网联汽车 政策 发布",
    "人工智能 监管 政策 新规",
    "工信部 自动驾驶 准入 试点",
    "交通运输部 智能网联 道路测试",
    "L3 自动驾驶 法规 政策",
    "数据安全 人工智能 管理办法",
    "robotaxi 政策 监管 许可",
    "百度 Apollo 自动驾驶 政策",
]

NEWS_QUERIES = [
    "Robotaxi 商业化 运营 城市",
    "特斯拉 FSD Robotaxi 进展",
    "英伟达 自动驾驶 芯片 发布",
    "OpenAI 大模型 发布 更新",
    "百度 Apollo 萝卜快跑 自动驾驶",
    "华为 智能驾驶 乾崑 ADS",
    "字节跳动 豆包 大模型 发布",
    "小马智行 文远知行 融资 合作",
    "自动驾驶 L3 L4 量产 落地",
    "Waymo Cruise 自动驾驶 扩张",
]

RESEARCH_QUERIES = [
    "智能驾驶 券商 研报 2026",
    "自动驾驶 行业分析 证券",
    "Robotaxi 投资 研报 券商",
    "AI 大模型 券商 研报",
    "自动驾驶 深度报告 证券",
]

SYSTEM_PROMPT = """你是一位专业的 AI/自动驾驶行业日报编辑，服务于"跟进时事+积累素材"的双重目标。今天是 {today_date}。

你收到三组搜索结果。你的任务是筛选出高质量、时效性强的内容。

## 时效性铁律（最高优先级）
- 只收录 {today_date}（今天）或昨天发布的内容
- 如果搜索结果的标题或摘要中显示的日期早于昨天，坚决排除
- 如果没有明确日期信息，但内容明显是旧闻（如"2025年底""去年""此前已公布"），坚决排除
- 企业官网的静态介绍页、产品页、招聘页，一律排除——这些不是新闻

## 禁止收录的内容类型
- 企业官网静态页面（如 tesla.com/robotaxi 产品介绍页）
- 百科、问答平台的内容（知乎问答、百度百科等）
- 文档分享站的内容（原创力文档、道客巴巴等）
- 自媒体/个人博客的转载或洗稿文章
- 明显由AI生成的低质量内容
- 日期不明确或明显过时的内容
- 没有实质信息量的标题党文章

## 任务1：政策动向
从政策素材中筛选政府部门的正式政策发布、法规征求意见稿、试点通知等。每条必须：
- 发布主体为国务院、部委、地方政府等政府机构
- 有明确的政策名称或文件编号
- 有实质内容（不能是"关注""将出台"这类模糊表述）
- 只收录今天（{today_date}）或昨天发布的内容
如果没有符合条件的政策，policy返回空数组。

## 任务2：行业资讯
从行业素材中筛选与AI、自动驾驶、大模型、芯片相关的重大动态。每条必须：
- 是"发生了什么事"——有明确的事件、动作、数据
- 对百度有直接或间接的战略参考价值
- 优先收录：产品发布、技术突破、商业合作、投融资、政策影响、市场数据
- 坚决排除：预测性文章、行业综述、观点评论（无新事件）
- 只收录今天（{today_date}）或昨天发布的内容

## 任务3：每日研报
从研报素材中提取真正的券商/研究机构研报。每条必须：
- 来源为真实金融机构：中信证券、中金公司、国泰君安、海通证券、华泰证券、招商证券、申万宏源、广发证券、东方证券、光大证券、天风证券、兴业证券、国信证券、长城证券、东北证券、中银证券、国泰海通等
- 有明确的研报标题和核心观点摘要
- 只收录今天（{today_date}）或昨天发布的内容
- 如果搜索结果中没有符合条件的真实研报，research返回空数组——禁止编造！禁止基于行业素材写"简评"冒充研报！

## 输出格式
必须是标准 JSON，不要任何 markdown 代码块标记。date 字段必须是 YYYY-MM-DD 格式（例如 2026-05-15）：
{
  "policy": [
    {"title": "...", "summary": "...", "source": "...", "url": "...", "date": "2026-05-15", "country": "中国/美国/国际"}
  ],
  "news": [...],
  "research": [
    {"title": "...", "summary": "...", "source": "...", "url": "...", "date": "2026-05-15", "country": "中国/美国/国际"}
  ],
  "stats": {"policy_count": 0, "news_count": 0, "research_count": 0, "paywall_skipped": 0}
}

重要：宁可少而精，不要多而滥。但如果素材质量不错且日期在合理范围内，请尽量收录，不要过度过滤导致空日报。"""


# 研报来源白名单
RESEARCH_SOURCE_WHITELIST = {
    "中信证券", "中金公司", "国泰君安", "海通证券", "华泰证券", "招商证券",
    "申万宏源", "广发证券", "东方证券", "光大证券", "天风证券", "兴业证券",
    "国信证券", "长城证券", "东北证券", "中银证券", "国泰海通", "中信建投",
    "平安证券", "浙商证券", "国盛证券", "华西证券", "东吴证券", "长江证券",
    "财通证券", "安信证券", "银河证券", "方正证券", "中泰证券", "国金证券",
    " Goldman Sachs", "Morgan Stanley", "JPMorgan", "UBS", "Deutsche Bank",
    "Bank of America", "Citigroup", "Barclays", "HSBC",
}


def is_whitelisted_research_source(source: str) -> bool:
    """检查研报来源是否在白名单中"""
    if not source:
        return False
    source_lower = source.lower()
    for valid in RESEARCH_SOURCE_WHITELIST:
        if valid.lower() in source_lower:
            return True
    return False


import time

def search_duckduckgo(queries: List[str], max_results: int = 5, timelimit: str = "d", retries: int = 3) -> List[Dict]:
    """使用 DuckDuckGo 搜索，带重试和退避
    timelimit: "d"=最近一天, "w"=最近一周, "m"=最近一月, None=不限
    """
    all_results = []
    seen_urls = set()
    with DDGS() as ddgs:
        for q in queries:
            for attempt in range(retries):
                try:
                    kwargs = {"max_results": max_results}
                    if timelimit:
                        kwargs["timelimit"] = timelimit
                    results = ddgs.text(q, **kwargs)
                    count = 0
                    for r in results:
                        url = r.get("href", "")
                        if url in seen_urls:
                            continue
                        seen_urls.add(url)
                        all_results.append({
                            "title": r.get("title", ""),
                            "url": url,
                            "summary": r.get("body", "")[:400],
                        })
                        count += 1
                    if count > 0:
                        print(f"[OK] DDG '{q}' ({timelimit}): {count} results")
                    break  # 成功，跳出重试
                except Exception as e:
                    print(f"[WARN] DDG search failed for '{q}' (attempt {attempt+1}/{retries}): {e}")
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)  # 1s, 2s, 4s
                    else:
                        print(f"[ERROR] DDG '{q}' all retries exhausted")
    return all_results


def search_with_fallback(queries: List[str], max_results: int = 5, timelimit: str = "d") -> List[Dict]:
    """先尝试带时间限制的搜索，如果为空则尝试不带时间限制"""
    results = search_duckduckgo(queries, max_results=max_results, timelimit=timelimit)
    if not results:
        print(f"[FALLBACK] No results with timelimit='{timelimit}', trying without timelimit...")
        results = search_duckduckgo(queries, max_results=max_results, timelimit=None)
    return results


def extract_json(text: str) -> str:
    """从可能包含 markdown 代码块的文本中提取 JSON"""
    import re
    # 尝试匹配 ```json ... ``` 或 ``` ... ```
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


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
        "temperature": 0.1,
        "max_tokens": 4000
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            json=payload,
            headers=headers,
            timeout=120
        )
        resp.raise_for_status()

        content = resp.json()["choices"][0]["message"]["content"]
        print(f"[DEBUG] DeepSeek raw output length: {len(content)}")
        print(f"[DEBUG] DeepSeek raw output preview: {content[:500]}")

        # 保存原始输出到日志文件，方便诊断
        log_dir = Path("data/debug_logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"deepseek_{target_date}.txt"
        try:
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"[DEBUG] DeepSeek raw output saved to {log_file}")
        except Exception as e:
            print(f"[WARN] Failed to save debug log: {e}")

        json_text = extract_json(content)
        data = json.loads(json_text)
        return data
    except Exception as e:
        print(f"[ERROR] DeepSeek API failed: {e}")
        print("[WARN] DeepSeek failed, returning empty report instead of raw garbage")
        # Fallback: 返回空日报，不塞原始低质量结果
        return {
            "policy": [], "news": [], "research": [],
            "stats": {"policy_count": 0, "news_count": 0, "research_count": 0, "paywall_skipped": 0}
        }


def parse_date(date_str: str) -> datetime:
    """尝试多种格式解析日期"""
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y年%m月%d日",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y%m%d",
        "%d-%m-%Y",
        "%m/%d/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    raise ValueError(f"无法解析日期: {date_str}")


def is_reasonable_date(date_str: str, target_date: str, max_days: int = 7) -> bool:
    """检查日期是否在合理范围内（允许1天未来容错，避免DeepSeek日期标注误差误杀）"""
    if not date_str:
        return False
    try:
        from datetime import timedelta
        item_date = parse_date(date_str)
        target = datetime.strptime(target_date, "%Y-%m-%d")
        delta = target - item_date
        # 允许日期在未来1天内（DeepSeek可能把今天的政策标成明天）
        # 也允许早于target_date最多max_days天
        return timedelta(days=-1) <= delta <= timedelta(days=max_days)
    except Exception as e:
        print(f"[WARN] Date parse failed for '{date_str}': {e}")
        return False


def validate_and_filter(data: Dict, target_date: str) -> Dict:
    """后处理校验：过滤日期异常、来源不合格的条目"""
    filtered = {"policy": [], "news": [], "research": []}
    stats = {"policy_skipped": 0, "news_skipped": 0, "research_skipped": 0}

    # 政策：只保留当天和前一天（严格时效性）
    for item in data.get("policy", []):
        if is_reasonable_date(item.get("date"), target_date, max_days=1):
            filtered["policy"].append(item)
        else:
            stats["policy_skipped"] += 1
            print(f"[FILTER] Skip policy (bad date): {item.get('title', '')[:50]} date={item.get('date', 'N/A')}")

    # 新闻：只保留当天和前一天（严格时效性）
    for item in data.get("news", []):
        if is_reasonable_date(item.get("date"), target_date, max_days=1):
            filtered["news"].append(item)
        else:
            stats["news_skipped"] += 1
            print(f"[FILTER] Skip news (bad date): {item.get('title', '')[:50]} date={item.get('date', 'N/A')}")

    # 研报：只保留当天和前一天 + 来源白名单
    for item in data.get("research", []):
        date_ok = is_reasonable_date(item.get("date"), target_date, max_days=1)
        source_ok = is_whitelisted_research_source(item.get("source", ""))
        if date_ok and source_ok:
            filtered["research"].append(item)
        else:
            stats["research_skipped"] += 1
            reason = []
            if not date_ok:
                reason.append("bad_date")
            if not source_ok:
                reason.append("bad_source")
            print(f"[FILTER] Skip research ({','.join(reason)}): {item.get('title', '')[:50]} date={item.get('date', 'N/A')} source={item.get('source', 'N/A')}")

    print(f"[INFO] Validation: policy={len(filtered['policy'])}/{len(filtered['policy'])+stats['policy_skipped']}, "
          f"news={len(filtered['news'])}/{len(filtered['news'])+stats['news_skipped']}, "
          f"research={len(filtered['research'])}/{len(filtered['research'])+stats['research_skipped']}")

    filtered["stats"] = {
        "policy_count": len(filtered["policy"]),
        "news_count": len(filtered["news"]),
        "research_count": len(filtered["research"]),
        "paywall_skipped": 0
    }
    return filtered


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

    # 搜索策略：
    # - 政策：放宽到一周，政策发布频率低
    # - 新闻：严格一天，确保时效性（fallback到不限时间）
    # - 研报：放宽到一周，研报不是每天都有
    policy_results = search_with_fallback(POLICY_QUERIES, max_results=8, timelimit="w")
    news_results = search_with_fallback(NEWS_QUERIES, max_results=5, timelimit="d")
    research_results = search_with_fallback(RESEARCH_QUERIES, max_results=8, timelimit="w")

    print(f"[INFO] Raw results - Policy: {len(policy_results)}, News: {len(news_results)}, Research: {len(research_results)}")

    all_results = policy_results + news_results + research_results

    if not all_results:
        print("[WARN] No search results, falling back to empty report")
        data = {
            "policy": [], "news": [], "research": [],
            "stats": {"policy_count": 0, "news_count": 0, "research_count": 0, "paywall_skipped": 0}
        }
    else:
        print(f"[INFO] Generating report with DeepSeek...")
        raw_data = generate_daily_report(policy_results, news_results, research_results, target_date, api_key)
        print("[INFO] Validating and filtering results...")
        data = validate_and_filter(raw_data, target_date)

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
