#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
内容过滤器 v4 - 严格筛选规则
- 政策动向：仅限国内政府正式政策文件
- 行业资讯：接收国外政策
- 研报：去除不可靠来源，强制验证
"""
import json
import re
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse

# ============ 政策动向过滤规则 ============

# 政府域名白名单
GOV_DOMAIN_WHITELIST = [
    '.gov.cn',  # 所有政府网站
    'mofcom.gov.cn', 'miit.gov.cn', 'ndrc.gov.cn', 'most.gov.cn', 'cac.gov.cn',
    'beijing.gov.cn', 'shanghai.gov.cn', 'guangdong.gov.cn', 'zhejiang.gov.cn',
    'jiangsu.gov.cn', 'sichuan.gov.cn', 'shandong.gov.cn', 'henan.gov.cn',
]

# 权威媒体白名单（可报道政策新闻，但需标记来源）
AUTHORITATIVE_MEDIA = [
    # 央级媒体
    'xinhuanet.com',      # 新华社
    'people.com.cn',      # 人民日报
    'cctv.com',           # 央视新闻
    'cnr.cn',             # 央广网
    'china.com.cn',       # 中国网
    'ce.cn',              # 经济日报
    'gmw.cn',             # 光明日报
    'chinanews.com',      # 中国新闻网
    # 财经权威媒体
    'thepaper.cn',        # 澎湃新闻
    'jiemian.com',        # 界面新闻
    'caixin.com',         # 财新网
    'yicai.com',          # 第一财经
    '21jingji.com',       # 21世纪经济报道
]

# 政府机构关键词（用于识别发布机构 - 内容主体判断）
GOV_AGENCIES = [
    # 中央政府
    '国务院', '国务院办公厅', '国办',
    # 部委
    '发改委', '发展和改革委员会', '工信部', '工业和信息化部',
    '科技部', '科学技术部', '网信办', '中央网信办',
    '交通部', '交通运输部', '公安部', '公共安全部',
    '教育部', '财政部', '商务部', '人社部', '人社局',
    '国家市场监督', '市场监管总局', '国家标准委', '国标委',
    '中央政治局', '深改委', '国常会', '中央财经委', '中央财经委员会',
    # 地方政府（省级）
    '省政府', '市政府', '县政府', '区政府',
    '北京市', '上海市', '广东省', '江苏省', '浙江省', '山东省', '四川省',
    '北京市政府', '上海市政府', '广东省政府',
    # 地方机构
    '经信局', '工信局', '科委', '发改委', '发改委',
    # 政策发布主体关键词
    '国家发布', '官方发布', '政府发布', '部委发布',
]

# AI/自动驾驶相关关键词（政策必须涉及）
AI_AUTO_KEYWORDS = [
    '人工智能', 'AI', '大模型', '深度学习', '机器学习',
    '自动驾驶', '智能网联', '无人驾驶', '智能汽车', '新能源车',
    '算法', '算力', '数据要素', '机器人', '智能制造',
]

# 内容黑名单词汇（出现即丢弃）
POLICY_BLACKLIST = [
    '协会', '学会', '联盟', '峰会', '论坛',
    '解读', '评论', '观点', '分析', '展望', '观察', '深度',
    '专家称', '专家表示', '业内人士', '机构分析',
    '企业响应', '企业呼吁', '联合声明',
    '倡议', '自律公约', '行业规范',
    '政策问答', '一图读懂', '图解', '权威解读', '答记者问',
    '白皮书', '蓝皮书', '研究报告',
]

# 非政府机构（排除）
NON_GOVERNMENT = [
    '协会', '学会', '联盟', '智库', '研究院', '研究所',
    '中心', '实验室', '委员会', '基金会', '公司', '企业',
]

# ============ 行业资讯过滤规则 ============

# AI头部公司
AI_COMPANIES = [
    'openai', 'anthropic', 'deepmind', 'google', 'meta', 'microsoft', 'nvidia', 'amazon',
    '百度', '华为', '字节', '阿里巴巴', '腾讯', '阿里', '字节跳动',
    '百川智能', '月之暗面', '智谱', 'minimax', 'deepseek', '零一万物',
]

# 自动驾驶头部公司
AUTO_COMPANIES = [
    'tesla', 'waymo', 'cruise', 'zoox', 'mobileye', 'apollo',
    '小鹏', '小马智行', 'pony', '理想', '小米汽车', 'ads', '比亚迪',
    '地平线', '黑芝麻', '文远智行', 'weride', '吉利', '曹操',
]

# 前沿技术关键词
FRONTIER_TECH = [
    '大语言模型', 'llm', '多模态', '具身智能', '世界模型',
    '端到端', '无图', 'robotaxi', 'fsd', '自动驾驶',
    'ai视频', 'ai芯片', '机器人', 'agi', '通用人工智能',
    'reasoning', 'o1', 'o3', 'gpt-5', 'claude', 'gemini',
    '智能体', 'agent', '具身智能', '人形机器人', '智驾',
    '端到端自动驾驶', '城市noa', '高阶智驾',
]

# ============ 重点公司白名单（行业资讯强制检查） ============

# 国外重点公司
FOREIGN_KEY_COMPANIES = [
    'openai', 'anthropic', 'google deepmind', 'deepmind', 'google',
    'meta', 'microsoft', 'nvidia', 'tesla', 'waymo', 'cruise',
    'zoox', 'mobileye', 'apple', 'amazon', 'ibm',
]

# 国内重点公司
DOMESTIC_KEY_COMPANIES = [
    '百度', '华为', '字节跳动', '字节', '阿里巴巴', '阿里', '腾讯',
    '小鹏汽车', '小鹏', '蔚来', '理想汽车', '理想', '小米汽车', '小米',
    '比亚迪', '地平线', '黑芝麻智能', '黑芝麻', '小马智行', 'pony',
    '文远智行', 'weride', 'momenta', '商汤', '旷视', '科大讯飞',
    '大疆', '华为智驾', '鸿蒙智行',
]

# 所有重点公司
KEY_COMPANIES = FOREIGN_KEY_COMPANIES + DOMESTIC_KEY_COMPANIES

# AI/自动驾驶领域判定关键词（用于 is_ai_autonomous_domain）
AI_AUTO_DOMAIN_KEYWORDS = [
    # AI 核心
    '人工智能', 'ai ', '大模型', 'llm', '深度学习', '机器学习',
    '神经网络', 'transformer', 'gpt', 'chatgpt', 'claude',
    '生成式ai', '生成式人工智能', 'aigc', 'agi', '通用人工智能',
    '多模态', '智能体', 'ai agent', '具身智能', '人形机器人',
    # 自动驾驶核心
    '自动驾驶', '无人驾驶', '智能网联', '智能驾驶', '高阶智驾',
    'robotaxi', 'fsd', '端到端', '城市noa', 'noa',
    '激光雷达', '毫米波雷达', '视觉感知', '决策规划',
    # 产业关键词
    '算力', '芯片', 'gpu', 'npu', 'ai芯片', '智算中心',
    '数据要素', '大模型训练', '模型推理', 'ai基础设施',
]

# 重大突破/要闻判定关键词
BREAKTHROUGH_KEYWORDS = [
    # 技术里程碑
    '突破', '里程碑', '首次', '首创', '全球首个', '世界首个',
    '刷新纪录', '超越', 'sota', 'state of the art',
    '开源', '发布', '重磅', '颠覆', '革命性',
    # 产业里程碑
    '量产', '规模化', '商业化', '落地', '交付', '上路',
    '获批', '许可', '牌照', '试点', '运营',
    # 监管里程碑
    '监管', '法规', '标准', '准入', '安全认证',
]

# 排除词汇（中小公司日常动态）
NEWS_EXCLUDE_KEYWORDS = [
    '融资', '轮融资', '天使轮', 'a轮', 'b轮', 'c轮',
    '_pre_', 'ipo', '上市', '定增',
    '人事变动', '高管离职', '新任', '任命', '辞职',
    '小幅升级', '迭代', '补丁', 'bug修复',
    '参展', '参会', '演讲', '分享', '圆桌', '沙龙',
    '战略合作', '签署协议', '备忘录', '意向书',
    '获奖', '榜单', '排名', '评选',
]

# 绝对排除词（即使是重点公司也过滤）
NEWS_HARD_EXCLUDE_KEYWORDS = [
    '未来班', '学员', '培训', '课程', '教育项目',
    '志愿者', '公益活动', '社会责任',
    '趣味应用', '搞笑', '娱乐ai',
    '个人项目展示', '学生作品', '毕业设计',
    '悄然安装', '后台下载', '未经用户同意',
]

# ============ 自动驾驶专项检测规则 ============

# 自动驾驶核心关键词
AD_CORE_KEYWORDS = [
    '自动驾驶', '无人驾驶', '智能网联', '智能驾驶', '高阶智驾',
    'robotaxi', 'fsd', '端到端自动驾驶', '城市noa', 'noa',
    '激光雷达', '毫米波雷达', '视觉感知', '决策规划',
    '智驾', '自动驾驶出租车', '无人车', '智能车',
    'l3级', 'l4级', 'l3自动驾驶', 'l4自动驾驶',
    '自动驾驶许可', '自动驾驶牌照', '路测许可', '路测牌照',
    '自动驾驶事故', '自动驾驶安全', '无人化',
]

# 重大自动驾驶事件检测关键词
AD_MAJOR_EVENT_PATTERNS = {
    '政府许可/牌照': {
        'keywords': ['许可', '牌照', '路测', '测试许可', '运营许可',
                     '商业化许可', '自动驾驶许可', '无人化许可',
                     '获批', '批准', '发放牌照', '准入'],
        'context': ['政府', '部委', '交通部', '工信部', '部',
                   '北京', '上海', '深圳', '广州', '武汉', '重庆',
                   '杭州', '苏州', '长沙', '合肥', '无锡', '德清']
    },
    'Robotaxi动态': {
        'keywords': ['robotaxi', '自动驾驶出租车', '无人出租车',
                     'robotaxi运营', 'robotaxi上线', 'robotaxi发布',
                     'robotaxi投放', 'robotaxi试运营'],
        'context': []
    },
    '自动驾驶事故': {
        'keywords': ['自动驾驶事故', '无人驾驶事故', '辅助驾驶事故',
                     '智驾事故', '自动驾驶撞', '无人驾驶撞', '智驾撞'],
        'context': []
    },
    'L3/L4交付/量产': {
        'keywords': ['l3级', 'l4级', 'l3自动驾驶', 'l4自动驾驶'],
        'context': ['交付', '量产', '上市', '开售', '推出', '落地']
    },
}

# 国外政策关键词
FOREIGN_POLICY_KEYWORDS = [
    '美国', '欧盟', '英国', '日本', '韩国', '德国', '法国',
    'usa', 'eu', 'uk', 'japan', 'korea', 'germany', 'france',
    'white house', 'congress', 'parliament', 'commission',
    '法案', '法案通过', '监管', 'executive order', 'regulation',
    'export control', '制裁', '禁令', 'ai act',
]

# ============ 研报过滤规则 ============

# 永久剔除的来源
BLACKLIST_SOURCES = [
    'cb insights', 'cbinsights',
]

# 研报主题关键词
RESEARCH_THEMES = [
    '大模型', 'llm', '多模态', 'agi', '模型训练', '推理', '开源模型',
    '自动驾驶', 'robotaxi', '端到端', '感知', '规控', '无图',
    'ai影响', 'ai就业', 'ai经济', 'ai治理', 'ai监管', 'ai伦理',
    '中美科技', '芯片制裁', '出口管制', '供应链',
    'ai漫剧', 'ai视频', 'ai生成', 'ai power', 'ai能耗',
]


def is_gov_domain(url: str) -> bool:
    """检查是否是政府域名"""
    if not url:
        return False
    try:
        domain = urlparse(url).netloc.lower()
        for gov_domain in GOV_DOMAIN_WHITELIST:
            if gov_domain in domain or domain.endswith('.gov.cn'):
                return True
        return False
    except:
        return False


def contains_blacklist_keywords(text: str) -> Tuple[bool, str]:
    """检查是否包含黑名单关键词"""
    text_lower = text.lower()
    for kw in POLICY_BLACKLIST:
        if kw in text_lower:
            return True, kw
    return False, ''


def is_authoritative_media(url: str) -> bool:
    """检查是否是权威媒体"""
    if not url:
        return False
    try:
        domain = urlparse(url).netloc.lower()
        for media_domain in AUTHORITATIVE_MEDIA:
            if media_domain in domain:
                return True
        return False
    except:
        return False


def is_government_policy_subject(title: str, summary: str, source: str = '') -> Tuple[bool, str]:
    """
    判断内容主体是否为政府政策（核心逻辑）
    
    规则：
    1. 必须有政府机构作为主体（在标题、摘要或来源中）
    2. 必须涉及AI/自动驾驶相关领域
    3. 必须有政策文件特征（办法、规定、通知等）
    4. 排除非政府主体（企业、协会、专家等）
    """
    full_text = (title + ' ' + summary[:300] + ' ' + source).lower()
    
    # 1. 排除非政府主体（仅检查标题，避免误判摘要中的引用）
    non_gov_keywords = ['专家称', '专家表示', '业内人士', '机构分析', '分析师',
                       '企业回应', '企业呼吁', '公司表示', '负责人称',
                       '协会发布', '学会倡议', '联盟声明']
    for kw in non_gov_keywords:
        if kw in title:
            return False, f'非政府主体({kw})'
    
    # 2. 检查是否有政府机构作为主体（检查标题、摘要前300字、来源）
    has_gov_agency = False
    matched_agency = ''
    for agency in GOV_AGENCIES:
        if agency in title or agency in summary[:300] or agency in source:
            has_gov_agency = True
            matched_agency = agency
            break
    
    if not has_gov_agency:
        return False, '无政府机构主体'
    
    # 3. 检查是否涉及AI/自动驾驶（放宽范围）
    has_ai = any(kw in full_text for kw in AI_AUTO_KEYWORDS)
    if not has_ai:
        return False, '不涉及AI/自动驾驶'
    
    # 4. 检查是否有政策文件特征（放宽到摘要）
    policy_patterns = ['办法', '规定', '条例', '意见', '通知', '方案', 
                      '规划', '决定', '令', '政策', '部署', '会议', '试点',
                      '印发', '发布', '出台', '批准', '批复', '监管', '规范',
                      '国标', '国家标准', '行业标准', '实施细则', '指导意见',
                      '实施方案', '行动计划', '工作要点', '管理办法']
    has_policy = any(pt in title or pt in summary[:300] for pt in policy_patterns)
    
    if not has_policy:
        return False, '无政策文件特征'
    
    return True, f'政府政策主体({matched_agency})'


def clean_policy_items(items: List[Dict], strict_domain: bool = False) -> List[Dict]:
    """
    清洗政策动向 - 内容主体优先策略
    
    策略：
    1. 内容主体判断优先：只要内容是政府政策，不限来源
    2. 来源分类：政府官网(.gov.cn) / 权威媒体 / 其他媒体
    3. 黑名单过滤：排除解读、评论、观点类文章
    
    Args:
        items: 政策条目列表
        strict_domain: 是否使用严格域名过滤（False=内容主体优先）
    """
    filtered = []
    stats = {'total': len(items), 'passed': 0, 'gov': 0, 'media': 0, 'other': 0, 'rejected': {}}
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    for item in items:
        title = item.get('title', '')
        summary = item.get('summary', '') or ''
        source = item.get('source', '')
        url = item.get('url', '')
        date_str = item.get('date', '')
        
        # 1. 黑名单过滤（解读、评论、观点类）
        blacklist_keywords = ['解读', '一图读懂', '答记者问', '权威解读', '图解', 
                            '评论', '观点', '分析', '展望', '观察', '深度',
                            '白皮书', '蓝皮书', '研究报告', '峰会', '论坛']
        if any(kw in title for kw in blacklist_keywords):
            stats['rejected']['黑名单标题'] = stats['rejected'].get('黑名单标题', 0) + 1
            continue
        
        # 2. 内容主体判断（核心）
        is_policy, reason = is_government_policy_subject(title, summary, source)
        if not is_policy:
            stats['rejected'][reason] = stats['rejected'].get(reason, 0) + 1
            continue
        
        # 3. 来源分类
        is_gov = is_gov_domain(url)
        is_media = is_authoritative_media(url)
        
        if is_gov:
            item['policy_source_type'] = '政府官网'
            stats['gov'] += 1
        elif is_media:
            item['policy_source_type'] = '权威媒体'
            stats['media'] += 1
        else:
            item['policy_source_type'] = '其他媒体'
            stats['other'] += 1
        
        # 4. 时间窗口校验（仅收录当天或前一天）
        if date_str:
            try:
                if 'T' in date_str:
                    item_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                else:
                    item_date = datetime.strptime(date_str[:10], '%Y-%m-%d').date()
                
                if item_date > today:
                    stats['rejected']['未来日期'] = stats['rejected'].get('未来日期', 0) + 1
                    continue
                
                # 仅保留当天或前一天的政策
                if item_date < yesterday:
                    stats['rejected']['过期政策'] = stats['rejected'].get('过期政策', 0) + 1
                    continue
            except:
                pass
        
        # 5. 摘要长度检查
        if len(summary) < 30:
            stats['rejected']['摘要不足'] = stats['rejected'].get('摘要不足', 0) + 1
            continue
        
        filtered.append(item)
        stats['passed'] += 1
    
    print(f"[政策动向清洗] 原始: {stats['total']} -> 保留: {stats['passed']}")
    print(f"  - 政府官网: {stats['gov']} 条")
    print(f"  - 权威媒体: {stats['media']} 条")
    print(f"  - 其他媒体: {stats['other']} 条")
    for reason, count in sorted(stats['rejected'].items(), key=lambda x: -x[1])[:5]:
        print(f"  - 过滤: {reason}: {count}")
    
    return filtered


def is_ai_autonomous_domain(title: str, summary: str) -> bool:
    """
    检查内容是否属于人工智能或自动驾驶领域
    
    至少匹配一个AI/自动驾驶领域关键词
    """
    full_text = (title + ' ' + summary[:300]).lower()
    return any(kw.lower() in full_text for kw in AI_AUTO_DOMAIN_KEYWORDS)


def is_major_company_news(title: str, summary: str) -> Tuple[bool, str]:
    """
    检查是否涉及重点公司
    
    返回: (是否匹配, 匹配到的公司名)
    """
    full_text = (title + ' ' + summary[:200]).lower()
    for company in KEY_COMPANIES:
        if company.lower() in full_text:
            return True, company
    return False, ''


def is_breakthrough_news(title: str, summary: str) -> bool:
    """
    检查是否是重大突破/要闻
    
    满足以下之一即认为是重大突破：
    1. 标题包含突破/里程碑/首次等关键词
    2. 涉及技术/产业/监管重大进展
    """
    title_lower = title.lower()
    summary_lower = summary[:300].lower()
    
    # 检查突破关键词
    for kw in BREAKTHROUGH_KEYWORDS:
        if kw.lower() in title_lower:
            return True
    
    # 检查是否涉及重大发布（仅限重点公司）
    has_company, company = is_major_company_news(title, summary)
    if has_company:
        release_keywords = ['发布', '推出', ' unveiling ', ' announce ', ' launching ']
        if any(kw in title_lower for kw in release_keywords):
            return True
    
    return False


def is_autonomous_driving_news(title: str, summary: str) -> bool:
    """检测是否为自动驾驶相关新闻"""
    full_text = (title + ' ' + summary[:300]).lower()
    return any(kw.lower() in full_text for kw in AD_CORE_KEYWORDS)


def is_major_ad_event(title: str, summary: str) -> Tuple[bool, str]:
    """
    检测是否为重大自动驾驶事件，必须强制保留

    类型：
    1. 政府许可证/牌照
    2. Robotaxi发布/上线/运营
    3. 自动驾驶事故
    4. L3/L4级别交付/量产
    """
    full_text = (title + ' ' + summary[:200]).lower()

    for event_type, patterns in AD_MAJOR_EVENT_PATTERNS.items():
        keywords = patterns['keywords']
        context = patterns['context']

        # 检查是否匹配关键词
        has_keyword = any(kw.lower() in full_text for kw in keywords)
        if not has_keyword:
            continue

        # 如果有上下文要求，检查上下文
        if context:
            has_context = any(c in full_text for c in context)
            if not has_context:
                continue

        return True, event_type

    return False, ''


def validate_news_item(item: Dict) -> Tuple[bool, str, bool]:
    """
    验证行业资讯条目（强化版，支持AD配额）

    返回: (是否通过, 原因, 是否是AD新闻)
    """
    title = item.get('title', '')
    summary = item.get('summary', '') or ''
    title_lower = title.lower()

    # 先检测是否是重大AD事件（强制保留）
    is_major_ad, ad_event_type = is_major_ad_event(title, summary)
    if is_major_ad:
        return True, f'重大AD事件({ad_event_type})', True

    # 1. 摘要长度检查
    if len(summary) < 40:
        return False, '摘要不足40字', False

    # 2. 过滤软文
    soft_keywords = ['软文', '推广', '广告', '赞助']
    if any(k in title or k in summary for k in soft_keywords):
        return False, '软文/推广', False

    # 3. 领域强制检查：必须属于AI/自动驾驶领域
    if not is_ai_autonomous_domain(title, summary):
        return False, '非AI/自动驾驶领域', False

    # 3.5 绝对排除词检查（即使是重点公司也过滤）
    title_lower = title.lower()
    for kw in NEWS_HARD_EXCLUDE_KEYWORDS:
        if kw in title_lower:
            return False, f'绝对排除: {kw}', False

    # 4. 排除词汇检查（中小公司日常融资、人事变动等）
    is_ad = is_autonomous_driving_news(title, summary)
    for kw in NEWS_EXCLUDE_KEYWORDS:
        if kw in title_lower:
            # AD新闻放宽：不过滤融资类（可能有重大AD融资）
            if is_ad and kw in ['融资', '轮融资']:
                break
            # 如果是重点公司的新闻，不过滤
            has_company, _ = is_major_company_news(title, summary)
            if not has_company:
                return False, f'排除: {kw}', False

    # 5. 重点公司检查（增加重要性门槛）
    has_company, matched_company = is_major_company_news(title, summary)
    if has_company:
        # 即使是重点公司，也必须满足以下至少一条才保留：
        # 1. 重大发布/更新（模型、产品、战略合作）
        # 2. 重大运营数据（收入、用户数、规模）
        # 3. 监管/许可相关
        # 4. 自动驾驶相关
        important_indicators = [
            '发布', '推出', '上线', '开源', '宣布', '达成', '合作',
            '收入', '用户', '订单', '规模', '车队', '里程',
            '许可', '牌照', '获批', '监管', '法规', '准入',
            '自动驾驶', 'robotaxi', 'fsd', '无人', '智驾',
            '解散', '重组', '合并', '收购',
        ]
        has_importance = any(kw in title.lower() for kw in important_indicators)

        if not has_importance:
            return False, f'重点公司但非重要动态({matched_company})', is_ad

        return True, f'重点公司重要动态({matched_company})', is_ad

    # 6. 重大突破/要闻检查（非重点公司但重大突破）
    if is_breakthrough_news(title, summary):
        return True, '重大突破/要闻', is_ad

    return False, '非重点公司且无重大突破', False


def verify_report_link(url: str, report_title: str = '', report_date: str = '') -> Tuple[bool, str, str]:
    """
    三级强制验证研报链接
    
    返回: (是否有效, 失败原因, 替代链接)
    """
    if not url or not url.startswith('http'):
        return False, 'URL无效', ''
    
    # 过滤已知的无效URL模式
    invalid_patterns = [
        '/ideas/insights/topics',
        '/insights/research-centers',
        '/insights/industry/retail',
        '/blogs/research/',
        '/tag/',
        '/category/',
        '/author/',
        '/search?',
        '/topics/',
        '/collections/',
        '/archive/',
        '/index.',
    ]
    for pattern in invalid_patterns:
        if pattern in url:
            return False, '非具体报告页面', ''

    # 过滤纯域名首页（路径过短）
    parsed = urlparse(url)
    if len(parsed.path) < 4 or parsed.path == '/':
        return False, 'URL为网站首页', ''
    
    # ========== 第三级：链接时效性检查 ==========
    today = datetime.now().date()
    if report_date:
        try:
            rd = datetime.strptime(report_date, '%Y-%m-%d').date()
            days_old = (today - rd).days
            if days_old > 30:
                # 30天以上的旧报告，直接标记为过期，后续结合HTTP状态码决定
                pass
        except:
            pass
    
    # ========== 第一级：HTTP 状态码检查 ==========
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)

    except requests.exceptions.SSLError:
        # SSL证书错误，尝试不验证（部分国内站点证书问题）
        try:
            response = requests.get(url, headers=headers, timeout=15, allow_redirects=True, verify=False)
        except Exception as e:
            return False, f'SSL错误且重试失败: {str(e)[:30]}', ''
    except requests.exceptions.Timeout:
        return False, '访问超时(15秒)', ''
    except requests.exceptions.ConnectionError:
        return False, '连接失败', ''
    except requests.exceptions.TooManyRedirects:
        return False, '重定向过多', ''
    except Exception as e:
        return False, f'请求异常: {str(e)[:30]}', ''

    if response.status_code == 404:
        # 链接失效，如果是30天以上的旧报告，直接丢弃
        if report_date:
            try:
                rd = datetime.strptime(report_date, '%Y-%m-%d').date()
                if (today - rd).days > 30:
                    return False, f'链接返回404，报告为{report_date}旧报告({(today-rd).days}天前)，已丢弃', ''
            except:
                pass
        return False, f'链接失效-状态码404', ''

    if response.status_code == 403:
        return False, f'链接失效-状态码403(禁止访问)', ''

    if response.status_code == 500:
        return False, f'链接失效-状态码500(服务器错误)', ''

    if response.status_code != 200:
        return False, f'链接失效-状态码{response.status_code}', ''

    # 检查重定向是否到首页或通用页面
    final_url = response.url
    if final_url.rstrip('/') != url.rstrip('/'):
        parsed_final = urlparse(final_url)
        parsed_orig = urlparse(url)
        # 如果重定向到明显更短的路径，可能是首页
        if len(parsed_final.path) < 5 and parsed_final.netloc == parsed_orig.netloc:
            return False, '重定向到首页', ''
        # 如果重定向到搜索页或tag页
        if any(p in parsed_final.path for p in ['/search', '/tag/', '/topic/']):
            return False, '重定向到搜索/标签页', ''
    
    # ========== 第二级：页面内容实质性检查 ==========
    try:
        content_type = response.headers.get('Content-Type', '').lower()
        content = response.text
        content_lower = content.lower()

        # 如果是PDF链接，直接放行（PDF无法做内容结构检查）
        if 'application/pdf' in content_type or url.lower().endswith('.pdf'):
            return True, '通过(PDF)', ''

        # 2.1 检查页面是否包含错误提示
        error_keywords = [
            'page not found', '404 not found', '404 error', '404 -',
            '不存在', '无法找到', '已删除', '已下架', '页面已失效',
            'oops', 'sorry', 'not available', 'unavailable',
            'content not found', 'document not found', 'article not found',
            'access denied', 'forbidden', '禁止访问', '无权限',
        ]
        for kw in error_keywords:
            if kw in content_lower:
                return False, f'页面包含错误提示: "{kw}"', ''

        # 2.2 检查页面可见文字长度（去除HTML标签后）
        text_only = re.sub(r'<[^>]+>', ' ', content)
        text_only = re.sub(r'\s+', ' ', text_only).strip()
        text_length = len(text_only)

        # 中文页面至少300字，英文页面至少150单词
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text_only))
        if has_chinese and text_length < 300:
            return False, f'页面内容过少(仅{text_length}字)，视为空壳', ''
        if not has_chinese:
            word_count = len(text_only.split())
            if word_count < 150:
                return False, f'页面内容过少(仅{word_count}单词)，视为空壳', ''

        # 2.3 检查页面主要结构
        has_h1 = bool(re.search(r'<h1[\s>]', content_lower))
        has_h2 = bool(re.search(r'<h2[\s>]', content_lower))
        has_paragraph = bool(re.search(r'<p[\s>]', content_lower))
        has_div = bool(re.search(r'<div[\s>]', content_lower))

        if not (has_h1 or has_h2):
            has_article = bool(re.search(r'<article[\s>]', content_lower))
            has_main = bool(re.search(r'<main[\s>]', content_lower))
            has_section = bool(re.search(r'<section[\s>]', content_lower))
            if not (has_article or has_main or has_section):
                return False, '页面结构缺失(无标题标签)', ''

        if not has_paragraph and not has_div:
            return False, '页面结构缺失(无段落/块内容)', ''

        # 2.4 检查是否有报告相关内容特征
        report_indicators = ['report', 'research', 'study', 'analysis', 'white paper',
                           '报告', '研究', '分析', '白皮书', '研报', '调研']
        has_report_content = any(ind in content_lower for ind in report_indicators)

        if not has_report_content:
            return False, '无报告内容特征', ''

        # 2.5 检查标题是否与报告标题匹配（防止页面被替换）
        if report_title:
            # 提取页面title标签内容
            title_match = re.search(r'<title[^>]*>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
            if title_match:
                page_title = re.sub(r'\s+', ' ', title_match.group(1)).strip().lower()
                report_title_lower = report_title.lower()
                # 检查页面title是否包含报告标题中的核心词
                title_words = [w for w in re.split(r'[\s\-\|:]+', report_title_lower) if len(w) >= 3]
                if title_words:
                    match_count = sum(1 for w in title_words if w in page_title)
                    # 如果核心词完全不在页面title中，可能页面已被替换
                    if match_count == 0 and len(title_words) >= 2:
                        # 但允许"page not found"等错误页面通过前面的过滤后仍被拦截
                        pass  # 这里仅做记录，不强制拦截（防止误杀）

        # 全部通过
        return True, '通过', ''

    except Exception as e:
        return False, f'内容检查异常: {str(e)[:30]}', ''


# 保留旧函数名以保持兼容性，内部调用新的验证函数
def check_report_accessibility(url: str) -> Tuple[bool, str]:
    """兼容旧接口，调用三级验证"""
    is_valid, reason, _ = verify_report_link(url)
    return is_valid, reason


def validate_report(report: Dict, check_url: bool = True) -> Tuple[bool, str]:
    """验证研报条目"""
    title = report.get('title', '')
    summary = report.get('summary', '') or ''
    url = report.get('url', '')
    date = report.get('date', '')
    source = report.get('source', '')
    
    # 检查标题
    if not title or len(title) < 10:
        return False, '标题无效'
    
    # 检查黑名单来源
    source_lower = source.lower()
    if any(bl in source_lower for bl in BLACKLIST_SOURCES):
        return False, f'黑名单来源: {source}'
    
    # 检查日期有效性
    today = datetime.now().date()
    if date:
        try:
            report_date = datetime.strptime(date, '%Y-%m-%d').date()
            if report_date > today:
                return False, f'未来日期: {date}'
        except:
            pass
    
    # 检查主题相关性
    title_lower = title.lower()
    summary_lower = summary.lower()
    theme_match = any(t in title_lower or t in summary_lower for t in RESEARCH_THEMES)
    
    if not theme_match:
        return False, '主题不相关'
    
    # 检查URL可访问性（三级强制验证）
    if check_url:
        is_valid, reason, alt_url = verify_report_link(url, title, date)
        if not is_valid:
            # 记录详细的丢弃原因
            if date:
                try:
                    rd = datetime.strptime(date, '%Y-%m-%d').date()
                    today = datetime.now().date()
                    days_old = (today - rd).days
                    if days_old > 30 and '404' in reason:
                        return False, f'{source}-{title[:20]}...: {reason}'
                except:
                    pass
            return False, reason
        # 如果有替代链接，更新
        if alt_url:
            report['url'] = alt_url
    
    return True, '通过'


def filter_news(items: List[Dict]) -> Tuple[List[Dict], List[Dict], Dict]:
    """
    过滤行业资讯，分离国外政策，支持AD配额与补充搜索
    v2: 新增严格日期过滤、重点公司重要性门槛

    返回: (行业资讯列表, 国外政策列表, 统计字典)
    """
    filtered_news = []
    foreign_policy = []
    rejected_ad_candidates = []  # 被拒绝但属于AD的候选（用于配额补充）
    stats = {
        'total': len(items),
        'passed': 0,
        'foreign_policy': 0,
        'ad_count': 0,
        'ai_count': 0,
        'ad_recovered': 0,
        'date_filtered': 0,
        'rejected': {}
    }

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    for item in items:
        title = item.get('title', '')
        summary = item.get('summary', '') or ''
        date_str = item.get('date', '')

        # ===== 新增：严格日期过滤（时效性红线）=====
        if date_str:
            try:
                if 'T' in date_str:
                    item_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                else:
                    item_date = datetime.strptime(date_str[:10], '%Y-%m-%d').date()

                # 只保留昨天和今天的文章
                if item_date < yesterday or item_date > today:
                    stats['date_filtered'] += 1
                    continue
            except:
                pass  # 日期解析失败时保留（避免误杀）
        # ==========================================

        # 检查是否是国外政策
        is_foreign_policy = any(kw in title.lower() or kw in summary.lower()
                               for kw in FOREIGN_POLICY_KEYWORDS)

        if is_foreign_policy:
            item['is_foreign_policy'] = True
            foreign_policy.append(item)
            stats['foreign_policy'] += 1
            continue

        passed, reason, is_ad = validate_news_item(item)
        if passed:
            filtered_news.append(item)
            stats['passed'] += 1
            if is_ad:
                stats['ad_count'] += 1
            else:
                stats['ai_count'] += 1
        else:
            # 如果是AD新闻但被拒绝，保存为候选
            if is_autonomous_driving_news(title, summary):
                rejected_ad_candidates.append((item, reason))
            stats['rejected'][reason] = stats['rejected'].get(reason, 0) + 1

    # ========== AD配额强制保障 ==========
    # 目标：AD内容至少3条，占比不低于40%
    total_valid = stats['passed']
    ad_count = stats['ad_count']

    # 第一步：如果AD < 3，从被拒绝的AD候选中找回
    if ad_count < 3 and rejected_ad_candidates:
        print(f"  [AD配额] AD不足({ad_count}<3)，尝试从被拒候选中找回...")
        for item, reason in rejected_ad_candidates:
            if ad_count >= 3:
                break
            filtered_news.append(item)
            ad_count += 1
            stats['passed'] += 1
            stats['ad_recovered'] += 1
            stats['rejected'][reason] -= 1
            if stats['rejected'][reason] == 0:
                del stats['rejected'][reason]
            print(f"    + 放宽保留AD: {item['title'][:40]}... (原原因: {reason})")

    stats['ad_count'] = ad_count
    total_valid = stats['passed']
    stats['ad_ratio'] = round(ad_count / total_valid * 100, 1) if total_valid > 0 else 0
    stats['need_supplement'] = ad_count < 3

    print(f"[行业资讯过滤] 原始: {stats['total']} -> 保留: {stats['passed']}, 国外政策: {stats['foreign_policy']}")
    print(f"  - 日期过滤: {stats['date_filtered']} 条（仅保留昨天/今天）")
    print(f"  - AD新闻: {stats['ad_count']} 条, AI新闻: {stats['ai_count']} 条 (AD占比: {stats['ad_ratio']}%)")
    if stats['ad_recovered'] > 0:
        print(f"  - 放宽找回AD: {stats['ad_recovered']} 条")
    if stats['need_supplement']:
        print(f"  [警告] AD内容严重不足({stats['ad_count']}条<3)，触发补充搜索")
    for reason, count in stats['rejected'].items():
        print(f"  - {reason}: {count}")

    return filtered_news, foreign_policy, stats


def filter_reports(reports: List[Dict], check_url: bool = True) -> List[Dict]:
    """过滤研报"""
    filtered = []
    stats = {'total': len(reports), 'passed': 0, 'rejected': {}}
    
    for report in reports:
        passed, reason = validate_report(report, check_url=check_url)
        if passed:
            filtered.append(report)
            stats['passed'] += 1
        else:
            stats['rejected'][reason] = stats['rejected'].get(reason, 0) + 1
    
    print(f"[研报过滤] 原始: {stats['total']} -> 保留: {stats['passed']}")
    for reason, count in stats['rejected'].items():
        print(f"  - {reason}: {count}")
    
    return filtered


if __name__ == '__main__':
    print('内容过滤器 v3 加载成功')
    print('规则:')
    print('  - 政策动向: 仅国内政府政策')
    print('  - 行业资讯: 头部公司+前沿技术+国外政策')
    print('  - 研报: 黑名单过滤+链接验证')