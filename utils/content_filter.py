#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
内容过滤器 - 严格筛选高质量AI/自动驾驶资讯和研报
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
    policy_original: int = 0
    policy_filtered: int = 0
    removed_reasons: Dict[str, int] = None
    
    def __post_init__(self):
        if self.removed_reasons is None:
            self.removed_reasons = {}


class ContentFilter:
    """内容过滤器"""
    
    # AI领域头部公司
    AI_COMPANIES = [
        'openai', 'google deepmind', 'deepmind', 'anthropic', 'meta ai', 
        'microsoft ai', 'nvidia', '百度', '华为', '字节跳动', '阿里巴巴', '腾讯',
        'google', 'anthropic', 'stability ai', 'midjourney', 'suno',
        'perplexity', 'claude', 'chatgpt', 'gemini', 'llama', 'gpt',
        '文心一言', '通义千问', '讯飞星火', '智谱', '月之暗面', 'kimi',
        'minimax', 'deepseek', '深度求索', '百川智能', '零一万物'
    ]
    
    # 自动驾驶/智能汽车头部公司
    AUTO_COMPANIES = [
        'tesla', 'fsd', 'waymo', 'cruise', 'zoox', 'mobileye', 
        '百度apollo', 'apollo', '小鹏', '小马智行', 'pony.ai', '理想汽车', 
        '小米汽车', '华为ads', '比亚迪', '地平线', '黑芝麻智能', 
        '文远智行', 'weride', '吉利', '曹操出行', '蔚来', '哪吒汽车',
        '自动驾驶', '无人驾驶', 'robotaxi', '无人车', '智能汽车',
        '端到端', 'noa', '领航辅助', '智能驾驶', '智驾'
    ]
    
    # 前沿技术关键词
    TECH_KEYWORDS = [
        '大语言模型', 'llm', '多模态', '具身智能', '世界模型', 
        '端到端自动驾驶', '无图noa', 'ai视频生成', 'ai硬件', 
        'ai芯片', '机器人', 'aigc', '生成式ai', 'agi',
        'transformer', 'diffusion', 'gan', '视觉语言模型',
        '推理模型', 'o1', 'o3', 'deepseek', 'r1'
    ]
    
    # 研报允许主题（必须匹配至少一个）
    RESEARCH_TOPICS = [
        # 大模型
        r'大模型|llm|多模态|agi|模型训练|模型推理|开源模型|闭源模型|大语言模型',
        # 自动驾驶
        r'自动驾驶|robotaxi|端到端|感知|规控|无图noa|l2|l3|l4|无人驾驶|智能驾驶',
        # 中美科技竞争
        r'芯片制裁|ai出口|出口管制|供应链脱钩|地缘|科技竞争|芯片禁令',
        # AI影响
        r'ai对.*影响|ai与.*就业|ai.*经济|ai.*社会|ai.*伦理|ai治理|ai监管|ai政策'
    ]
    
    # 需要排除的低质量内容关键词
    LOW_QUALITY_KEYWORDS = [
        '观点', '评论：', '分析师称', '专家认为', '业内人士表示',
        '软文', '推广', '广告', '赞助', '活动报名',
        '小额融资', '天使轮', '种子轮',  # 只排除小额，大额融资保留
        '综述', '盘点', '汇总',  # 无实质内容的综述
        '震惊', '重磅', '突发', '刚刚'  # 标题党
    ]
    
    def __init__(self, today: str = None):
        """
        初始化过滤器
        
        Args:
            today: 今日日期，格式 YYYY-MM-DD
        """
        self.today = today or datetime.now().strftime("%Y-%m-%d")
        self.stats = FilterStats()
    
    def is_priority_company(self, title: str, content: str = "") -> bool:
        """
        判断是否涉及优先公司
        
        Args:
            title: 标题
            content: 内容（可选）
            
        Returns:
            是否涉及优先公司
        """
        text = (title + " " + content).lower()
        
        # 检查AI公司
        for company in self.AI_COMPANIES:
            if company.lower() in text:
                return True
        
        # 检查自动驾驶公司
        for company in self.AUTO_COMPANIES:
            if company.lower() in text:
                return True
        
        return False
    
    def is_frontier_tech(self, title: str, content: str = "") -> bool:
        """
        判断是否涉及前沿技术
        
        Args:
            title: 标题
            content: 内容（可选）
            
        Returns:
            是否涉及前沿技术
        """
        text = (title + " " + content).lower()
        
        for keyword in self.TECH_KEYWORDS:
            if keyword.lower() in text:
                return True
        
        return False
    
    def is_low_quality(self, title: str, content: str = "") -> Tuple[bool, str]:
        """
        判断是否为低质量内容
        
        Args:
            title: 标题
            content: 内容（可选）
            
        Returns:
            (是否低质量, 原因)
        """
        text = title + " " + content
        
        for keyword in self.LOW_QUALITY_KEYWORDS:
            if keyword in text:
                return True, f"低质量关键词: {keyword}"
        
        return False, ""
    
    def has_meaningful_summary(self, summary: str, min_length: int = 40) -> bool:
        """
        判断摘要是否有实质内容
        
        Args:
            summary: 摘要
            min_length: 最小长度
            
        Returns:
            是否有实质内容
        """
        if not summary:
            return False
        
        # 去除空白字符后检查长度
        clean_summary = re.sub(r'\s+', '', summary)
        
        return len(clean_summary) >= min_length
    
    def filter_news_item(self, item: Dict) -> Tuple[bool, str]:
        """
        过滤单条行业资讯
        
        Args:
            item: 资讯条目
            
        Returns:
            (是否保留, 原因)
        """
        title = item.get('title', '')
        summary = item.get('summary', '')
        url = item.get('url', '')
        
        # 1. 检查是否为优先公司动态
        if self.is_priority_company(title, summary):
            # 检查摘要质量
            if not self.has_meaningful_summary(summary, 30):  # 优先公司放宽到30字
                return False, "优先公司但摘要不足30字"
            return True, "优先公司动态"
        
        # 2. 检查是否为前沿技术
        if self.is_frontier_tech(title, summary):
            if not self.has_meaningful_summary(summary, 40):
                return False, "前沿技术但摘要不足40字"
            return True, "前沿技术"
        
        # 3. 检查是否为低质量内容
        is_low, reason = self.is_low_quality(title, summary)
        if is_low:
            return False, reason
        
        # 4. 其他内容需要有完整摘要
        if not self.has_meaningful_summary(summary, 40):
            return False, "摘要不足40字"
        
        # 5. 检查是否有实质内容
        if '本报告研究' in summary or '相关领域的发展现状' in summary:
            return False, "模板化摘要"
        
        return True, "通过基础筛选"
    
    def validate_report(self, report: Dict) -> Tuple[bool, str]:
        """
        验证研报是否有效
        
        Args:
            report: 研报数据
            
        Returns:
            (是否有效, 原因)
        """
        title = report.get('title', '')
        summary = report.get('summary', '')
        url = report.get('url', '')
        date = report.get('date', '')
        source = report.get('source', '')
        
        # 1. 检查必填字段
        if not title:
            return False, "无标题"
        
        if not url:
            return False, "无链接"
        
        if not source:
            return False, "无来源"
        
        # 2. 检查日期有效性（不能是未来日期）
        if date:
            try:
                report_date = datetime.strptime(date, "%Y-%m-%d")
                today_date = datetime.strptime(self.today, "%Y-%m-%d")
                
                if report_date > today_date:
                    return False, f"日期无效（未来日期: {date}）"
                
                # 检查是否在合理时间范围内（最近30天）
                if (today_date - report_date).days > 30:
                    return False, f"日期过期（{date}）"
            except ValueError:
                pass  # 日期格式错误，继续检查其他条件
        
        # 3. 检查主题相关性（必须匹配至少一个允许主题）
        text = title + " " + summary
        topic_matched = False
        
        for pattern in self.RESEARCH_TOPICS:
            if re.search(pattern, text, re.IGNORECASE):
                topic_matched = True
                break
        
        if not topic_matched:
            return False, "主题不相关"
        
        # 4. 检查链接有效性（不能是首页或搜索页）
        invalid_urls = [
            'cbinsights.com/#',  # 首页锚点
            'cbinsights.com/what-we-offer',  # 功能页面
            'forrester.com/blogs/research',  # 博客列表
            '/topics/',  # 主题页
            '/search?',  # 搜索页
        ]
        
        for invalid in invalid_urls:
            if invalid in url:
                return False, "非研报页面"
        
        # 5. 检查内容质量
        # 模板化摘要
        if summary and '本报告研究' in summary and '相关领域的发展现状' in summary:
            # 允许保留，但需要主题匹配（已通过）
            pass
        
        # 6. 检查是否为无关领域
        exclude_keywords = [
            '食品', '板栗', '零食', '消费品', '零售',
            '服装', '餐饮', '旅游', '酒店', '航空',
            '房地产', '建筑', '农业', '渔业'
        ]
        
        for keyword in exclude_keywords:
            if keyword in title and 'ai' not in title.lower() and '人工智能' not in title:
                return False, f"无关领域: {keyword}"
        
        return True, "验证通过"
    
    def filter_news(self, items: List[Dict]) -> List[Dict]:
        """
        批量过滤行业资讯
        
        Args:
            items: 资讯列表
            
        Returns:
            过滤后的列表
        """
        self.stats.news_original = len(items)
        filtered = []
        
        # 用于去重的URL集合
        seen_urls = set()
        
        for item in items:
            url = item.get('url', '')
            
            # 去重
            if url and url in seen_urls:
                self.stats.removed_reasons['重复'] = self.stats.removed_reasons.get('重复', 0) + 1
                continue
            
            # 过滤
            should_keep, reason = self.filter_news_item(item)
            
            if should_keep:
                filtered.append(item)
                if url:
                    seen_urls.add(url)
            else:
                self.stats.removed_reasons[reason] = self.stats.removed_reasons.get(reason, 0) + 1
        
        self.stats.news_filtered = len(filtered)
        
        return filtered
    
    def filter_research(self, items: List[Dict]) -> List[Dict]:
        """
        批量过滤研报
        
        Args:
            items: 研报列表
            
        Returns:
            过滤后的列表
        """
        self.stats.research_original = len(items)
        filtered = []
        
        # 用于去重的URL集合
        seen_urls = set()
        
        for item in items:
            url = item.get('url', '')
            
            # 去重
            if url and url in seen_urls:
                self.stats.removed_reasons['研报重复'] = self.stats.removed_reasons.get('研报重复', 0) + 1
                continue
            
            # 验证
            is_valid, reason = self.validate_report(item)
            
            if is_valid:
                filtered.append(item)
                if url:
                    seen_urls.add(url)
            else:
                self.stats.removed_reasons[f'研报-{reason}'] = self.stats.removed_reasons.get(f'研报-{reason}', 0) + 1
        
        self.stats.research_filtered = len(filtered)
        
        return filtered
    
    def filter_policy(self, items: List[Dict]) -> List[Dict]:
        """
        批量过滤政策资讯
        
        Args:
            items: 政策列表
            
        Returns:
            过滤后的列表
        """
        self.stats.policy_original = len(items)
        filtered = []
        
        # 用于去重的URL集合
        seen_urls = set()
        
        for item in items:
            url = item.get('url', '')
            
            # 去重
            if url and url in seen_urls:
                self.stats.removed_reasons['政策重复'] = self.stats.removed_reasons.get('政策重复', 0) + 1
                continue
            
            # 政策资讯要求有实质内容
            title = item.get('title', '')
            summary = item.get('summary', '')
            
            if not title:
                self.stats.removed_reasons['政策无标题'] = self.stats.removed_reasons.get('政策无标题', 0) + 1
                continue
            
            if not self.has_meaningful_summary(summary, 30):
                self.stats.removed_reasons['政策摘要不足'] = self.stats.removed_reasons.get('政策摘要不足', 0) + 1
                continue
            
            filtered.append(item)
            if url:
                seen_urls.add(url)
        
        self.stats.policy_filtered = len(filtered)
        
        return filtered
    
    def get_stats_report(self) -> str:
        """
        获取过滤统计报告
        
        Returns:
            统计报告字符串
        """
        lines = []
        lines.append("=" * 50)
        lines.append("内容过滤统计报告")
        lines.append("=" * 50)
        
        lines.append(f"\n行业资讯: {self.stats.news_original} -> {self.stats.news_filtered} 条")
        lines.append(f"政策动向: {self.stats.policy_original} -> {self.stats.policy_filtered} 条")
        lines.append(f"每日研报: {self.stats.research_original} -> {self.stats.research_filtered} 篇")
        
        if self.stats.removed_reasons:
            lines.append("\n过滤原因统计:")
            for reason, count in sorted(self.stats.removed_reasons.items(), key=lambda x: -x[1]):
                lines.append(f"  - {reason}: {count} 条")
        
        return "\n".join(lines)


# 使用示例
if __name__ == "__main__":
    # 测试过滤器
    filter = ContentFilter()
    
    # 测试行业资讯
    test_news = [
        {"title": "OpenAI发布GPT-5", "summary": "OpenAI今日发布了GPT-5模型，性能较GPT-4提升50%，支持更长上下文。", "url": "https://example.com/1"},
        {"title": "某公司观点", "summary": "专家认为AI行业前景广阔", "url": "https://example.com/2"},  # 低质量
        {"title": "特斯拉FSD新进展", "summary": "特斯拉FSD V12在中国开始推送，实现端到端自动驾驶。", "url": "https://example.com/3"},
    ]
    
    filtered = filter.filter_news(test_news)
    print(filter.get_stats_report())
