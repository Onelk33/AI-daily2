#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
政策搜索模块 - 使用百度搜索和 Google 搜索主动扩展政策信源
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

# ============ 政策搜索关键词 ============

POLICY_SEARCH_KEYWORDS = [
    # 中央政策
    '国务院 人工智能 政策 {year}',
    '工信部 自动驾驶 管理办法',
    '发改委 智能汽车 通知',
    '科技部 人工智能 规划',
    '网信办 算法 管理',
    '中央 深改委 人工智能 会议',
    
    # 地方政策
    '市政府 无人驾驶 试点',
    '省发改委 人工智能 产业',
    '智能网联汽车 政策',
    
    # 监管新规
    '新能源车 监管 新规',
    '人工智能 监管 办法',
    '自动驾驶 许可 管理',
]

# 权威媒体域名
AUTHORITATIVE_MEDIA_DOMAINS = [
    'xinhuanet.com',      # 新华社
    'people.com.cn',      # 人民日报
    'cctv.com',           # 央视新闻
    'cnr.cn',             # 央广网
    'china.com.cn',       # 中国网
    'ce.cn',              # 经济日报
    'gmw.cn',             # 光明日报
    'chinanews.com',      # 中国新闻网
    'thepaper.cn',        # 澎湃新闻
    'jiemian.com',        # 界面新闻
    'caixin.com',         # 财新网
    'yicai.com',          # 第一财经
    '21jingji.com',       # 21世纪经济报道
]

# 政府机构关键词
GOV_AGENCY_KEYWORDS = [
    '国务院', '国务院办公厅',
    '发改委', '发展和改革委员会',
    '工信部', '工业和信息化部',
    '科技部', '科学技术部',
    '网信办', '网络安全和信息化委员会',
    '交通部', '交通运输部',
    '公安部', '公共安全部',
    '教育部', '财政部', '商务部',
    '人民银行', '央行',
    '市场监管总局', '国家标准委',
    '中央政治局', '深改委', '国常会',
    '中央财经委员会',
    # 地方政府
    '省政府', '市政府', '县政府',
    '北京市', '上海市', '广东省', '江苏省', '浙江省',
    '经信局', '发改委', '科委',
]

# AI/自动驾驶相关关键词
AI_KEYWORDS = [
    '人工智能', 'AI', '大模型', '深度学习',
    '自动驾驶', '智能网联', '无人驾驶', '智能汽车',
    '算法', '算力', '芯片', '数据要素',
    '机器人', '智能制造',
]

# 排除词汇（非政策主体）
EXCLUDE_KEYWORDS = [
    '专家称', '专家表示', '业内人士',
    '机构分析', '分析师认为',
    '企业回应', '企业呼吁', '企业声明',
    '公司表示', '负责人称',
    '协会发布', '学会倡议', '联盟声明',
]


def is_government_policy(title: str, summary: str, source: str) -> Tuple[bool, str]:
    """
    判断内容主体是否为政府政策
    
    Args:
        title: 标题
        summary: 摘要
        source: 来源
        
    Returns:
        (是否为政府政策, 判断原因)
    """
    full_text = (title + ' ' + summary).lower()
    
    # 1. 检查排除词汇
    for kw in EXCLUDE_KEYWORDS:
        if kw in title or kw in summary:
            return False, f'含排除词({kw})'
    
    # 2. 检查是否有政府机构
    has_gov_agency = False
    matched_agency = ''
    for agency in GOV_AGENCY_KEYWORDS:
        if agency in title or agency in summary:
            has_gov_agency = True
            matched_agency = agency
            break
    
    if not has_gov_agency:
        return False, '无政府机构主体'
    
    # 3. 检查是否涉及 AI/自动驾驶
    has_ai = any(kw in title or kw in summary for kw in AI_KEYWORDS)
    if not has_ai:
        return False, '不涉及AI/自动驾驶'
    
    # 4. 检查是否有政策文件特征
    policy_patterns = ['办法', '规定', '条例', '意见', '通知', '方案', 
                      '规划', '决定', '令', '政策', '部署', '会议', '试点']
    has_policy = any(pt in title for pt in policy_patterns)
    
    if not has_policy:
        # 宽松一点，只要有政府主体和AI相关即可
        pass
    
    return True, f'政府政策主体({matched_agency})'


def is_authoritative_source(url: str) -> bool:
    """检查是否来自权威媒体"""
    if not url:
        return False
    url_lower = url.lower()
    for domain in AUTHORITATIVE_MEDIA_DOMAINS:
        if domain in url_lower:
            return True
    return False


def is_gov_domain(url: str) -> bool:
    """检查是否来自政府域名"""
    if not url:
        return False
    return '.gov.cn' in url.lower()


def search_baidu_policy(year: int = None) -> List[Dict]:
    """
    使用百度搜索获取政策信息
    
    注意：此函数需要配合 baidu-search skill 使用
    返回占位数据，实际调用时由 skill 执行
    """
    if year is None:
        year = datetime.now().year
    
    results = []
    
    # 生成搜索关键词
    for keyword_template in POLICY_SEARCH_KEYWORDS[:5]:  # 限制搜索次数
        keyword = keyword_template.format(year=year)
        results.append({
            'keyword': keyword,
            'source': 'baidu_search',
            'status': 'pending'
        })
    
    return results


def search_google_policy(year: int = None) -> List[Dict]:
    """
    使用 Google 搜索获取政策信息
    
    注意：此函数需要配合搜索工具使用
    返回占位数据，实际调用时由外部工具执行
    """
    if year is None:
        year = datetime.now().year
    
    results = []
    
    # 生成搜索关键词
    for keyword_template in POLICY_SEARCH_KEYWORDS[5:10]:
        keyword = keyword_template.format(year=year)
        results.append({
            'keyword': keyword,
            'source': 'google_search',
            'status': 'pending'
        })
    
    return results


def filter_policy_candidates(items: List[Dict]) -> List[Dict]:
    """
    过滤政策候选条目
    
    Args:
        items: 候选条目列表
        
    Returns:
        过滤后的政策列表
    """
    filtered = []
    stats = {'total': len(items), 'passed': 0, 'rejected': {}}
    
    for item in items:
        title = item.get('title', '')
        summary = item.get('summary', '') or ''
        source = item.get('source', '')
        url = item.get('url', '')
        
        # 验证政策主体
        is_policy, reason = is_government_policy(title, summary, source)
        
        if is_policy:
            # 标记来源类型
            if is_gov_domain(url):
                item['policy_source_type'] = '政府官网'
            elif is_authoritative_source(url):
                item['policy_source_type'] = '权威媒体'
            else:
                item['policy_source_type'] = '其他媒体'
            
            filtered.append(item)
            stats['passed'] += 1
        else:
            stats['rejected'][reason] = stats['rejected'].get(reason, 0) + 1
    
    print(f"[政策主体验证] 原始: {stats['total']} -> 保留: {stats['passed']}")
    for reason, count in sorted(stats['rejected'].items(), key=lambda x: -x[1])[:5]:
        print(f"  - {reason}: {count}")
    
    return filtered


def get_search_keywords_for_today() -> List[str]:
    """获取今天的政策搜索关键词"""
    year = datetime.now().year
    keywords = []
    for template in POLICY_SEARCH_KEYWORDS:
        keywords.append(template.format(year=year))
    return keywords


if __name__ == '__main__':
    # 测试政策主体验证
    test_cases = [
        {
            'title': '工信部发布《智能网联汽车管理办法》',
            'summary': '工业和信息化部近日发布管理办法，规范智能网联汽车产业发展。',
            'source': '新华社',
            'url': 'https://xinhuanet.com/test'
        },
        {
            'title': '专家称人工智能将改变未来',
            'summary': '业内人士表示AI技术将深刻影响各行各业。',
            'source': '某媒体',
            'url': 'https://example.com/test'
        },
        {
            'title': '国务院常务会议部署人工智能产业发展',
            'summary': '会议提出加快人工智能基础设施建设，推动产业高质量发展。',
            'source': '央视新闻',
            'url': 'https://cctv.com/test'
        },
    ]
    
    print("政策主体验证测试:")
    for item in test_cases:
        is_policy, reason = is_government_policy(
            item['title'], item['summary'], item['source']
        )
        print(f"  [{is_policy}] {item['title'][:30]}... - {reason}")