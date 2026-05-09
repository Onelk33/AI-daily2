"""
时间解析工具
支持自然语言时间指令，兼容常见中文表达
"""
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
from rich.console import Console

console = Console()


def parse_date_range_from_command(command: str) -> Optional[Tuple[str, str]]:
    """
    从自然语言指令中解析日期范围
    
    Args:
        command: 用户输入的指令，如"请帮我生成时间范围是 2026-05-01 至 2026-05-08 之间的日报"
        
    Returns:
        (start_date, end_date) 或 None
    """
    if not command:
        return None
    
    # 模式1: YYYY-MM-DD 至 YYYY-MM-DD
    pattern1 = r'(\d{4}-\d{2}-\d{2})\s*[至到~]\s*(\d{4}-\d{2}-\d{2})'
    match = re.search(pattern1, command)
    if match:
        start_date = match.group(1)
        end_date = match.group(2)
        if _validate_date(start_date) and _validate_date(end_date):
            return (start_date, end_date)
    
    # 模式2: YYYY年MM月DD日 至 YYYY年MM月DD日
    pattern2 = r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*[至到~]\s*(\d{4})年(\d{1,2})月(\d{1,2})日'
    match = re.search(pattern2, command)
    if match:
        start_date = f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
        end_date = f"{match.group(4)}-{match.group(5).zfill(2)}-{match.group(6).zfill(2)}"
        if _validate_date(start_date) and _validate_date(end_date):
            return (start_date, end_date)
    
    # 模式3: MM月DD日 至 MM月DD日（当年）
    pattern3 = r'(\d{1,2})月(\d{1,2})日\s*[至到~]\s*(\d{1,2})月(\d{1,2})日'
    match = re.search(pattern3, command)
    if match:
        year = datetime.now().year
        start_date = f"{year}-{match.group(1).zfill(2)}-{match.group(2).zfill(2)}"
        end_date = f"{year}-{match.group(3).zfill(2)}-{match.group(4).zfill(2)}"
        if _validate_date(start_date) and _validate_date(end_date):
            return (start_date, end_date)
    
    # 模式4: 昨天
    if '昨天' in command or '昨日' in command:
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        return (yesterday, yesterday)
    
    # 模式5: 最近N天
    pattern5 = r'最近(\d+)天'
    match = re.search(pattern5, command)
    if match:
        days = int(match.group(1))
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days-1)).strftime('%Y-%m-%d')
        return (start_date, end_date)
    
    # 模式6: 本周
    if '本周' in command or '这周' in command:
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        start_date = start_of_week.strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
        return (start_date, end_date)
    
    # 模式7: 上周
    if '上周' in command or '上周' in command:
        today = datetime.now()
        start_of_this_week = today - timedelta(days=today.weekday())
        start_of_last_week = start_of_this_week - timedelta(days=7)
        end_of_last_week = start_of_this_week - timedelta(days=1)
        return (start_of_last_week.strftime('%Y-%m-%d'), end_of_last_week.strftime('%Y-%m-%d'))
    
    return None


def _validate_date(date_str: str) -> bool:
    """验证日期字符串是否有效"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except:
        return False


def get_default_date_range() -> Tuple[str, str]:
    """
    获取默认日期范围：昨天 00:00 到今天 18:00（北京时间）
    
    用于每日自动运行时的时间窗口
    """
    from datetime import datetime, timedelta
    
    # 获取当前UTC时间
    now_utc = datetime.utcnow()
    
    # 转换为北京时间（UTC+8）
    now_beijing = now_utc + timedelta(hours=8)
    
    # 如果北京时间在18:00之前，搜索范围是前天00:00到今天18:00
    # 如果北京时间在18:00之后，搜索范围是昨天00:00到今天18:00
    if now_beijing.hour < 18:
        start_date = (now_beijing - timedelta(days=2)).strftime('%Y-%m-%d')
    else:
        start_date = (now_beijing - timedelta(days=1)).strftime('%Y-%m-%d')
    
    end_date = now_beijing.strftime('%Y-%m-%d')
    
    return (start_date, end_date)


def format_date_display(date_str: str) -> str:
    """格式化日期显示"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        weekdays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        return f"{date_obj.strftime('%Y年%m月%d日')} {weekdays[date_obj.weekday()]}"
    except:
        return date_str


def parse_time_command_test():
    """测试时间解析功能"""
    test_cases = [
        "请帮我生成时间范围是 2026-05-01 至 2026-05-08 之间的日报",
        "2026年5月1日 至 2026年5月8日",
        "5月1日 至 5月8日",
        "昨天",
        "最近7天",
        "本周",
        "上周",
    ]
    
    print("\n时间解析测试:")
    for cmd in test_cases:
        result = parse_date_range_from_command(cmd)
        if result:
            print(f"[OK] '{cmd}' -> {result[0]} 至 {result[1]}")
        else:
            print(f"[FAIL] '{cmd}' -> 解析失败")


if __name__ == '__main__':
    parse_time_command_test()