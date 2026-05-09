# -*- coding: utf-8 -*-
"""
高质量内容过滤器
严格筛选AI与自动驾驶领域的高价值内容
"""
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class FilterStats:
    """过滤统计"""
    news_original: int = 0
    news_filtered: int = 0
    research_original: int = 0
    research_filtered: int = 0
    research_date_invalid: int = 0
    research_topic_invalid: int = 0
    research_link_invalid: int = 0
    research_quality_invalid: int = 0


class QualityFilter:
    """高质量内容过滤器"""

    # AI领域头部公司（优先收录）
    AI_COMPANIES = [
        # 国际AI公司
        'openai', 'anthropic', 'deepmind', 'google', 'meta', 'microsoft', 'nvidia',
        'amazon', 'apple', 'xai', 'perplexity', 'mistral', 'cohere', 'stability',
        # 中国AI公司
        '百度', 'baidu', '阿里', 'alibaba', '腾讯', 'tencent', '字节', 'bytedance',
        '华为', 'huawei', '商汤', 'sensetime', '旷视', 'megvii', '云从', 'cloudwalk',
        '依图', 'yitu', '科大讯飞', 'iflytek', '深Seek', 'deepseek', '月之暗面',
        'moonshot', '智谱', 'zhipu', 'minimax', '百川', 'baichuan', '零一万物',
        # AI硬件/芯片
        'amd', 'intel', '高通', 'qualcomm', '联发科', 'mediatek', '寒武纪', 'cambricon',
        '地平线', 'horizon', '黑芝麻', 'black sesame', '壁仞', 'birend', '摩尔线程',
    ]

    # 自动驾驶领域头部公司（优先收录）
    AUTO_COMPANIES = [
        # 国际
        'tesla', 'waymo', 'cruise', 'zoox', 'mobileye', 'aptiv', 'aurora',
        'nuvia', 'nuro', 'argo', 'motional', 'autonomous',
        # 中国
        '小鹏', 'xpeng', '理想', 'li auto', '蔚来', 'nio', '小米汽车', 'xiaomi auto',
        '比亚迪', 'byd', '吉利', 'geely', '长安', 'changan', '长城', 'great wall',
        '华为ads', 'huawei ads', '百度apollo', 'baidu apollo',
        '小马智行', 'pony.ai', '文远知行', 'weride', '元戎启行', 'deeproute',
        'momenta', '禾赛', 'hesai', '图达通', 'innovusion', '速腾聚创', 'robosense',
        '曹操出行', 'caocao', '滴滴', 'didi', '如祺出行', 'on time',
    ]

    # 前沿技术关键词（优先收录）
    TECH_KEYWORDS = [
        '大语言模型', 'llm', 'large language model', 'gpt', 'claude', 'gemini',
        '多模态', 'multimodal', '具身智能', 'embodied ai', '世界模型', 'world model',
        '端到端自动驾驶', 'end-to-end', '无图noa', 'mapless', 'ai视频生成',
        'video generation', 'sora', 'runway', 'pika', '人形机器人', 'humanoid',
        '智能驾驶', 'autonomous driving', 'robotaxi', '自动驾驶', 'fsd', 'l2', 'l3', 'l4',
        'ai芯片', 'ai chip', 'gpu', 'tpu', 'npu', '算力', '训练', '推理',
        'agi', '通用人工智能', '模型训练', 'model training',
    ]

    # 研报主题关键词（必须匹配）
    RESEARCH_TOPICS = [
        # 大模型
        '大语言模型', 'llm', 'large language model', 'gpt', 'chatgpt', 'claude',
        '多模态大模型', 'multimodal model', 'agi', '通用人工智能', '模型训练',
        'model training', '开源模型', 'open source model', '大模型', 'foundation model',
        # 自动驾驶
        '自动驾驶', 'autonomous driving', 'robotaxi', '端到端', 'end-to-end',
        '智能驾驶', 'intelligent driving', '无图noa', 'mapless', 'l2', 'l3', 'l4',
        '感知算法', 'perception', '规控', 'planning control',
        # 中美科技竞争
        '芯片制裁', 'chip sanction', 'ai出口管制', 'ai export control',
        '供应链脱钩', 'supply chain decoupling', '地缘科技', 'geopolitical tech',
        '科技竞争', 'tech competition', '半导体限制', 'semiconductor restriction',
        # AI影响
        'ai对就业', 'ai on employment', 'ai对经济', 'ai on economy',
        'ai影响', 'ai impact', 'ai治理', 'ai governance', 'ai监管', 'ai regulation',
        'ai伦理', 'ai ethics', 'ai社会', 'ai society',
    ]

    # 无效研报主题（排除）
    EXCLUDED_RESEARCH_TOPICS = [
        '食品', 'food', '消费品', 'consumer goods', '传统汽车销量', 'car sales',
        '餐饮', 'restaurant', '服装', 'apparel', '零售', 'retail',
        '房地产', 'real estate', '旅游', 'travel', '教育', 'education',
        '医疗健康', 'healthcare', '医药', 'pharmaceutical',
    ]

    # 软文/推广关键词（过滤）
    SPAM_KEYWORDS = [
        '推广', '广告', '软文', '赞助', '合作推广', '营销', '促销',
        '优惠券', '折扣', '限时', '抢购', '特价',
    ]

    def __init__(self, today: datetime = None):
        self.today = today or datetime.now()
        self.stats = FilterStats()

    def filter_news(self, items: List[Dict]) -> List[Dict]:
        """
        过滤行业资讯
        
        规则：
        1. 优先收录AI/自动驾驶头部公司
        2. 过滤软文、重复、无实质内容
        3. 摘要不少于40字
        """
        self.stats.news_original = len(items)
        filtered = []
        seen_titles = set()

        for item in items:
            title = item.get('title', '').lower()
            summary = item.get('summary', '') or item.get('content', '') or ''
            url = item.get('url', '') or item.get('source_url', '')

            # 1. 去重
            title_key = re.sub(r'[^\w\s]', '', title)[:50]
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            # 2. 过滤软文
            if any(kw in title or kw in summary for kw in self.SPAM_KEYWORDS):
                continue

            # 3. 检查是否匹配优先公司
            is_priority = False
            all_companies = self.AI_COMPANIES + self.AUTO_COMPANIES
            for company in all_companies:
                if company in title or company in summary.lower():
                    is_priority = True
                    break

            # 4. 检查是否匹配前沿技术
            has_tech = False
            for kw in self.TECH_KEYWORDS:
                if kw in title or kw in summary.lower():
                    has_tech = True
                    break

            # 5. 非优先内容需要更严格筛选
            if not is_priority and not has_tech:
                # 检查是否有实质内容
                if len(summary) < 40:
                    continue
                # 检查是否是AI相关
                ai_keywords = ['ai', '人工智能', '机器学习', '深度学习', 'neural', 'gpt', 'llm']
                if not any(kw in title or kw in summary.lower() for kw in ai_keywords):
                    continue

            # 6. 摘要长度检查
            if len(summary) < 40:
                # 如果是优先公司，尝试保留
                if not is_priority:
                    continue

            filtered.append(item)

        self.stats.news_filtered = len(filtered)
        return filtered

    def validate_report(self, report: Dict) -> Tuple[bool, str]:
        """
        验证研报是否有效
        
        Returns:
            (is_valid, reason)
        """
        title = report.get('title', '')
        summary = report.get('summary', '') or ''
        url = report.get('url', '')
        date_str = report.get('date', '')
        source = report.get('source', '')

        # 1. 标题必须存在
        if not title or len(title) < 5:
            self.stats.research_quality_invalid += 1
            return False, "标题缺失或过短"

        # 2. 日期有效性检查
        if date_str:
            try:
                # 解析日期
                if 'T' in date_str:
                    report_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    report_date = datetime.strptime(date_str[:10], '%Y-%m-%d')

                # 不能是未来日期
                if report_date.date() > self.today.date():
                    self.stats.research_date_invalid += 1
                    return False, f"日期无效（未来日期: {date_str}）"

                # 时间窗口检查（可配置）
                # 目前允许任何历史日期

            except Exception as e:
                # 日期格式无效，但可以保留
                pass

        # 3. 主题相关性检查
        text_to_check = f"{title} {summary}".lower()
        topic_matched = False

        for topic in self.RESEARCH_TOPICS:
            if topic.lower() in text_to_check:
                topic_matched = True
                break

        if not topic_matched:
            self.stats.research_topic_invalid += 1
            return False, "主题不匹配"

        # 4. 排除无效主题
        for excluded in self.EXCLUDED_RESEARCH_TOPICS:
            if excluded.lower() in text_to_check:
                # 只有当排除词更突出时才排除
                if excluded.lower() in title.lower():
                    self.stats.research_topic_invalid += 1
                    return False, f"排除主题: {excluded}"

        # 5. 链接有效性检查
        if not url or len(url) < 10:
            self.stats.research_link_invalid += 1
            return False, "链接缺失"

        # 检查是否是首页或搜索页
        invalid_urls = ['google.com/search', 'bing.com/search', 'baidu.com/s?',
                        'homepage', 'index.html', 'index.php']
        for invalid in invalid_urls:
            if invalid in url.lower():
                self.stats.research_link_invalid += 1
                return False, "链接无效（搜索页/首页）"

        # 6. 来源可信度检查
        if not source or len(source) < 2:
            self.stats.research_quality_invalid += 1
            return False, "来源缺失"

        return True, "有效"

    def filter_research(self, reports: List[Dict]) -> List[Dict]:
        """
        过滤研报
        
        规则：
        1. 主题必须匹配
        2. 日期不能是未来
        3. 链接有效
        4. 去重
        """
        self.stats.research_original = len(reports)
        filtered = []
        seen_urls = set()
        seen_titles = set()

        for report in reports:
            # 验证
            is_valid, reason = self.validate_report(report)
            if not is_valid:
                continue

            # 去重
            url = report.get('url', '')
            title = report.get('title', '')[:50]

            if url in seen_urls or title in seen_titles:
                continue

            seen_urls.add(url)
            seen_titles.add(title)

            filtered.append(report)

        self.stats.research_filtered = len(filtered)
        return filtered

    def get_stats_report(self) -> str:
        """获取过滤统计报告"""
        return f"""
=== 内容过滤统计 ===
行业资讯: 原始 {self.stats.news_original} 条 -> 过滤后 {self.stats.news_filtered} 条
研报: 原始 {self.stats.research_original} 篇 -> 过滤后 {self.stats.research_filtered} 篇
  - 日期无效: {self.stats.research_date_invalid} 篇
  - 主题不匹配: {self.stats.research_topic_invalid} 篇
  - 链接无效: {self.stats.research_link_invalid} 篇
  - 质量不合格: {self.stats.research_quality_invalid} 篇
==================="""
