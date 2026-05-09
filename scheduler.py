"""
定时任务调度器
支持每日定时执行日报生成
"""
import schedule
import time
import threading
from datetime import datetime
from typing import Optional
from rich.console import Console

console = Console()


class DailyScheduler:
    """日报定时调度器"""
    
    def __init__(self, agent):
        self.agent = agent
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def run_daily(self):
        """执行一次日报生成"""
        console.print(f"\n[bold cyan]{'='*50}[/bold cyan]")
        console.print(f"[bold cyan]⏰ 定时任务触发 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/bold cyan]")
        console.print(f"[bold cyan]{'='*50}[/bold cyan]\n")
        
        try:
            self.agent.run()
        except Exception as e:
            console.print(f"[red]定时任务执行失败: {e}[/red]")
    
    def start(self, time_str: str = "18:00"):
        """
        启动定时任务
        
        Args:
            time_str: 每天执行的时间，格式为 "HH:MM"
        """
        console.print(Panel.fit(
            f"[bold green]🕐 定时任务已启动[/bold green]\n\n"
            f"执行时间: 每天 {time_str}\n"
            f"按 Ctrl+C 停止",
            title="Scheduler"
        ))
        
        # 设置定时任务
        schedule.every().day.at(time_str).do(self.run_daily)
        
        self.running = True
        
        # 立即执行一次（可选）
        console.print("\n[yellow]是否立即执行一次？(y/n): [/yellow]", end="")
        choice = input().strip().lower()
        if choice == 'y':
            self.run_daily()
        
        # 开始循环
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            console.print("\n[yellow]定时任务已停止[/yellow]")
            self.running = False
    
    def stop(self):
        """停止定时任务"""
        self.running = False
        schedule.clear()


def start_scheduler(agent, time_str: str = None):
    """
    启动定时任务
    
    Args:
        agent: DailyAgent 实例
        time_str: 执行时间，None 则从配置读取
    """
    # 从配置读取时间
    if time_str is None:
        time_str = agent.config.get('daily_report.generate_time', '18:00')
    
    scheduler = DailyScheduler(agent)
    scheduler.start(time_str)


if __name__ == '__main__':
    # 测试调度器
    print("定时任务调度器测试")
    print("提示: 这个模块需要配合 main.py --schedule 使用")