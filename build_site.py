"""
网站构建脚本
生成按日归档的静态HTML网站
支持政策动向、行业资讯、每日研报三大板块
"""
import os
import json
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from rich.console import Console

console = Console()


@dataclass
class SiteConfig:
    """网站配置"""
    site_name: str = "AI日报"
    site_description: str = "每日政策动向、行业资讯与全球研报"
    base_url: str = ""  # 网站访问地址，如 https://username.github.io/repo/
    author: str = "日报Agent"
    timezone: str = "UTC+8"


class SiteBuilder:
    """静态网站构建器"""
    
    def __init__(self, docs_dir: str = "docs", config: SiteConfig = None):
        self.docs_dir = Path(docs_dir)
        self.config = config or SiteConfig()
        self.data_dir = Path("data/site_data")
        
    def build_all(self, date_str: str = None):
        """
        构建完整网站
        
        Args:
            date_str: 日期字符串，格式 YYYY-MM-DD，默认今天
        """
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        console.print(f"\n[bold cyan]开始构建网站: {date_str}[/bold cyan]")
        
        # 创建目录
        self._create_directories()
        
        # 加载数据
        daily_data = self._load_daily_data(date_str)
        
        # 生成当日页面
        self._generate_daily_page(date_str, daily_data)
        
        # 更新首页（最新日报）
        self._generate_index_page(date_str, daily_data)
        
        # 更新历史列表
        self._generate_history_page()
        
        # 复制静态资源
        self._copy_static_assets()
        
        console.print(f"[green]网站构建完成！[/green]")
        console.print(f"[cyan]文件保存在: {self.docs_dir}[/cyan]")
    
    def _create_directories(self):
        """创建必要的目录"""
        dirs = [
            self.docs_dir,
            self.docs_dir / "daily",
            self.docs_dir / "css",
            self.docs_dir / "js",
            self.data_dir
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
    
    def _load_daily_data(self, date_str: str) -> Dict:
        """
        加载当日数据
        
        Returns:
            {
                'policy': [...],    # 政策动向
                'news': [...],      # 行业资讯
                'research': [...],  # 每日研报
                'stats': {...}      # 统计数据
            }
        """
        data = {
            'policy': [],
            'news': [],
            'research': [],
            'stats': {
                'policy_count': 0,
                'news_count': 0,
                'research_count': 0,
                'paywall_skipped': 0
            }
        }
        
        # 尝试加载已保存的日报数据
        data_file = self.data_dir / f"{date_str}.json"
        if data_file.exists():
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                    data = saved_data
                    console.print(f"[green]从 {data_file} 加载数据成功[/green]")
            except Exception as e:
                console.print(f"[yellow]加载数据失败: {e}[/yellow]")
        
        # 只有当 site_data 中没有研报数据时，才从 global_research_reports.json 加载
        if not data.get('research'):
            research_file = Path("data/global_research_reports.json")
            if research_file.exists():
                try:
                    with open(research_file, 'r', encoding='utf-8') as f:
                        reports = json.load(f)
                        data['research'] = reports
                        data['stats']['research_count'] = len(reports)
                except:
                    pass
        
        return data
    
    def save_daily_data(self, date_str: str, data: Dict):
        """保存当日数据"""
        data_file = self.data_dir / f"{date_str}.json"
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        console.print(f"[dim]数据已保存: {data_file}[/dim]")
    
    def _generate_daily_page(self, date_str: str, data: Dict):
        """生成当日页面"""
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        date_display = date_obj.strftime("%Y年%m月%d日")
        
        html = self._get_html_template()
        
        # 替换变量
        html = html.replace("{{SITE_NAME}}", self.config.site_name)
        html = html.replace("{{DATE}}", date_str)
        html = html.replace("{{DATE_DISPLAY}}", date_display)
        html = html.replace("{{TITLE}}", f"{date_display} - {self.config.site_name}")
        
        # 网站访问地址
        import os
        site_url = self.config.base_url or os.environ.get('SITE_URL', '')
        if site_url:
            site_url_display = f'<p class="site-url">🌐 <a href="{site_url}">{site_url}</a></p>'
        else:
            site_url_display = '<p class="site-url" style="color: #888;">💡 配置 SITE_URL 环境变量以显示网址</p>'
        html = html.replace("{{SITE_URL_DISPLAY}}", site_url_display)
        
        # 生成各板块内容
        policy_html = self._render_section("政策动向", data.get('policy', []), "policy")
        news_html = self._render_section("行业资讯", data.get('news', []), "news")
        research_html = self._render_section("每日研报", data.get('research', []), "research")
        
        # 统计信息
        stats = data.get('stats', {})
        stats_html = f"""
        <div class="stats">
            <div class="stat-item">
                <span class="stat-label">政策动向</span>
                <span class="stat-value">{stats.get('policy_count', 0)} 条</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">行业资讯</span>
                <span class="stat-value">{stats.get('news_count', 0)} 条</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">每日研报</span>
                <span class="stat-value">{stats.get('research_count', 0)} 篇</span>
            </div>
            {f'<div class="stat-item paywall"><span class="stat-label">付费墙跳过</span><span class="stat-value">{stats.get("paywall_skipped", 0)} 篇</span></div>' if stats.get('paywall_skipped', 0) > 0 else ''}
        </div>
        """
        
        # 更新时间
        update_time = datetime.now().strftime("%Y-%m-%d %H:%M") + f" {self.config.timezone}"
        
        # 网站URL显示
        if self.config.base_url:
            site_url_display = f'<p class="site-url">网站地址: <a href="{self.config.base_url}" target="_blank">{self.config.base_url}</a></p>'
        else:
            site_url_display = '<p class="site-url">网站地址: 请在GitHub Pages中查看</p>'
        
        html = html.replace("{{POLICY_SECTION}}", policy_html)
        html = html.replace("{{NEWS_SECTION}}", news_html)
        html = html.replace("{{RESEARCH_SECTION}}", research_html)
        html = html.replace("{{STATS}}", stats_html)
        html = html.replace("{{UPDATE_TIME}}", update_time)
        html = html.replace("{{SITE_URL_DISPLAY}}", site_url_display)
        
        # 生成历史日期列表
        history_html = self._generate_history_list()
        html = html.replace("{{HISTORY_LIST}}", history_html)
        
        # 保存文件
        output_file = self.docs_dir / "daily" / f"{date_str}.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        console.print(f"[green]生成日报页面: {output_file}[/green]")
    
    def _generate_index_page(self, date_str: str, data: Dict):
        """生成首页（自动跳转到最新日报）"""
        # 创建跳转页面
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.config.site_name}</title>
    <meta http-equiv="refresh" content="0; url=daily/{date_str}.html">
    <link rel="canonical" href="daily/{date_str}.html">
</head>
<body>
    <p>正在跳转到最新日报...</p>
    <p>如果没有自动跳转，<a href="daily/{date_str}.html">请点击这里</a></p>
</body>
</html>"""
        
        output_file = self.docs_dir / "index.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        console.print(f"[green]更新首页: {output_file}[/green]")
    
    def _generate_history_page(self):
        """生成历史日报列表页面"""
        daily_dir = self.docs_dir / "daily"
        
        # 获取所有历史日报
        history_files = sorted(daily_dir.glob("*.html"), reverse=True)
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>历史日报 - {self.config.site_name}</title>
    <link rel="stylesheet" href="css/style.css">
</head>
<body>
    <header>
        <h1><a href="index.html">{self.config.site_name}</a></h1>
        <p>{self.config.site_description}</p>
    </header>
    
    <main>
        <h2>历史日报</h2>
        <div class="history-list">
"""
        
        for file in history_files:
            date_str = file.stem
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                date_display = date_obj.strftime("%Y年%m月%d日")
                weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][date_obj.weekday()]
                
                html += f"""
            <div class="history-item">
                <a href="daily/{date_str}.html">
                    <span class="date">{date_display}</span>
                    <span class="weekday">{weekday}</span>
                </a>
            </div>
"""
            except:
                continue
        
        html += """
        </div>
    </main>
    
    <footer>
        <p>由 日报Agent 自动生成</p>
    </footer>
</body>
</html>"""
        
        output_file = self.docs_dir / "history.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html)
        
        console.print(f"[green]更新历史列表页面[/green]")
    
    def _generate_history_list(self) -> str:
        """生成历史日期列表HTML片段"""
        daily_dir = self.docs_dir / "daily"
        history_files = sorted(daily_dir.glob("*.html"), reverse=True)[:30]  # 最近30天
        
        html = '<div class="history-sidebar">\n<h3>历史日报</h3>\n<ul>\n'
        
        for file in history_files:
            date_str = file.stem
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                date_display = date_obj.strftime("%m-%d")
                html += f'<li><a href="../daily/{date_str}.html">{date_display}</a></li>\n'
            except:
                continue
        
        html += '</ul>\n<a href="../history.html">查看全部</a>\n</div>'
        return html
    
    def _render_section(self, title: str, items: List[Dict], section_type: str) -> str:
        """渲染板块内容"""
        if not items:
            return f"""
        <section class="section {section_type}">
            <h2 class="section-title">{title}</h2>
            <div class="empty-state">
                <p>暂无数据</p>
            </div>
        </section>
"""
        
        items_html = ""
        for i, item in enumerate(items, 1):
            items_html += self._render_item(item, i, section_type)
        
        return f"""
        <section class="section {section_type}">
            <h2 class="section-title">{title}</h2>
            <div class="items">
                {items_html}
            </div>
        </section>
"""
    
    def _render_item(self, item: Dict, index: int, section_type: str) -> str:
        """渲染单个条目"""
        # 获取国别标记
        country = item.get('country', '')
        country_flag = self._get_country_flag(country)
        
        title = item.get('title', '') or item.get('title_translated', '无标题')
        summary = item.get('summary', '') or item.get('summary_translated', '') or item.get('content', '')
        source = item.get('source', '未知来源')
        url = item.get('url', '') or item.get('source_url', '#')
        date = item.get('date', '')
        
        # 截断摘要
        if len(summary) > 300:
            summary = summary[:300] + "..."
        
        return f"""
            <article class="item">
                <div class="item-header">
                    <span class="item-index">{index}</span>
                    <h3 class="item-title">{title}</h3>
                    <span class="country">{country_flag} {country}</span>
                </div>
                <div class="item-body">
                    <p class="item-summary">{summary}</p>
                </div>
                <div class="item-footer">
                    <span class="item-source">来源: {source}</span>
                    {f'<span class="item-date">{date}</span>' if date else ''}
                    <a class="item-link" href="{url}" target="_blank" rel="noopener">查看原文</a>
                </div>
            </article>
"""
    
    def _get_country_flag(self, country: str) -> str:
        """获取国别emoji"""
        flags = {
            '中国': '🇨🇳',
            '美国': '🇺🇸',
            '英国': '🇬🇧',
            '日本': '🇯🇵',
            '德国': '🇩🇪',
            '法国': '🇫🇷',
            '瑞士': '🇨🇭',
            '新加坡': '🇸🇬',
            '韩国': '🇰🇷',
            '国际': '🌍',
            '未知': '🌐'
        }
        return flags.get(country, '🌐')
    
    def _copy_static_assets(self):
        """复制静态资源"""
        # CSS
        css_dir = self.docs_dir / "css"
        css_dir.mkdir(exist_ok=True)
        
        css_content = self._get_css()
        with open(css_dir / "style.css", 'w', encoding='utf-8') as f:
            f.write(css_content)
        
        console.print(f"[green]生成CSS样式[/green]")
    
    def _get_html_template(self) -> str:
        """获取HTML模板"""
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{TITLE}}</title>
    <meta name="description" content="{{SITE_NAME}} - {{DATE_DISPLAY}}">
    <link rel="stylesheet" href="../css/style.css">
</head>
<body>
    <header>
        <div class="header-content">
            <h1><a href="../index.html">{{SITE_NAME}}</a></h1>
            <p class="date">{{DATE_DISPLAY}}</p>
            {{SITE_URL_DISPLAY}}
        </div>
    </header>
    
    <div class="container">
        <main>
            {{STATS}}
            
            {{POLICY_SECTION}}
            {{NEWS_SECTION}}
            {{RESEARCH_SECTION}}
            
            <footer class="page-footer">
                <p>数据更新时间: {{UPDATE_TIME}}</p>
                <p>由日报Agent自动生成 | <a href="../history.html">历史日报</a></p>
            </footer>
        </main>
        
        <aside>
            {{HISTORY_LIST}}
        </aside>
    </div>
</body>
</html>"""
    
    def _get_css(self) -> str:
        """获取CSS样式"""
        return """/* 基础样式 */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    line-height: 1.6;
    color: #333;
    background: #f5f5f5;
}

/* 头部 */
header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 2rem;
    text-align: center;
}

header h1 {
    font-size: 2rem;
    margin-bottom: 0.5rem;
}

header h1 a {
    color: white;
    text-decoration: none;
}

header .date {
    font-size: 1.2rem;
    opacity: 0.9;
}

header .site-url {
    font-size: 0.9rem;
    opacity: 0.8;
    margin-top: 0.5rem;
}

header .site-url a {
    color: #fff;
    text-decoration: underline;
}

/* 容器 */
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
    display: grid;
    grid-template-columns: 1fr 250px;
    gap: 2rem;
}

@media (max-width: 768px) {
    .container {
        grid-template-columns: 1fr;
    }
}

/* 统计信息 */
.stats {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
    flex-wrap: wrap;
}

.stat-item {
    background: white;
    padding: 1rem 1.5rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stat-item.paywall {
    background: #fff3cd;
}

.stat-label {
    display: block;
    font-size: 0.9rem;
    color: #666;
}

.stat-value {
    display: block;
    font-size: 1.5rem;
    font-weight: bold;
    color: #333;
}

/* 板块 */
.section {
    background: white;
    border-radius: 8px;
    padding: 1.5rem;
    margin-bottom: 2rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.section-title {
    font-size: 1.5rem;
    color: #667eea;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #667eea;
}

.section.policy .section-title {
    color: #2c5282;
    border-color: #2c5282;
}

.section.news .section-title {
    color: #2d3748;
    border-color: #2d3748;
}

.section.research .section-title {
    color: #744210;
    border-color: #744210;
}

/* 条目 */
.item {
    border-left: 3px solid #667eea;
    padding-left: 1rem;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #eee;
}

.item:last-child {
    border-bottom: none;
    margin-bottom: 0;
}

.item-header {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
}

.item-index {
    background: #667eea;
    color: white;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
    font-weight: bold;
    flex-shrink: 0;
}

.item-title {
    font-size: 1.1rem;
    color: #333;
    flex: 1;
}

.country {
    font-size: 0.85rem;
    color: #666;
    white-space: nowrap;
}

.item-body {
    margin-bottom: 0.5rem;
}

.item-summary {
    color: #555;
    line-height: 1.7;
}

.item-footer {
    display: flex;
    align-items: center;
    gap: 1rem;
    font-size: 0.85rem;
    color: #888;
}

.item-link {
    margin-left: auto;
    color: #667eea;
    text-decoration: none;
}

.item-link:hover {
    text-decoration: underline;
}

/* 空状态 */
.empty-state {
    text-align: center;
    padding: 2rem;
    color: #999;
}

/* 历史侧边栏 */
.history-sidebar {
    background: white;
    padding: 1rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.history-sidebar h3 {
    font-size: 1rem;
    margin-bottom: 1rem;
    color: #333;
}

.history-sidebar ul {
    list-style: none;
}

.history-sidebar li {
    margin-bottom: 0.5rem;
}

.history-sidebar a {
    color: #667eea;
    text-decoration: none;
    display: block;
    padding: 0.3rem 0;
}

.history-sidebar a:hover {
    text-decoration: underline;
}

/* 历史列表页面 */
.history-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 1rem;
}

.history-item {
    background: white;
    border-radius: 8px;
    padding: 1rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.history-item a {
    text-decoration: none;
    color: inherit;
    display: block;
}

.history-item:hover {
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

.history-item .date {
    font-size: 1.1rem;
    color: #667eea;
    font-weight: bold;
}

.history-item .weekday {
    display: block;
    font-size: 0.85rem;
    color: #888;
    margin-top: 0.3rem;
}

/* 页脚 */
.page-footer {
    text-align: center;
    color: #888;
    padding: 2rem 0;
    font-size: 0.9rem;
}

.page-footer a {
    color: #667eea;
}

/* 响应式 */
@media (max-width: 768px) {
    header {
        padding: 1rem;
    }
    
    header h1 {
        font-size: 1.5rem;
    }
    
    .stats {
        flex-direction: column;
    }
    
    .item-footer {
        flex-wrap: wrap;
    }
}
"""


def build_website(date_str: str = None, site_url: str = None):
    """
    构建网站的便捷函数
    
    Args:
        date_str: 日期字符串，格式 YYYY-MM-DD
        site_url: 网站访问地址，如 https://username.github.io/repo/
    """
    import os
    
    # 从环境变量或参数获取网站URL
    if site_url is None:
        site_url = os.environ.get('SITE_URL', '')
    
    config = SiteConfig(base_url=site_url)
    builder = SiteBuilder(config=config)
    builder.build_all(date_str)


if __name__ == '__main__':
    import sys
    
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    build_website(date_arg)
