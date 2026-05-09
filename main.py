"""
日报 Agent 主程序
"""
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import List

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core import ConfigLoader, CacheManager, NewsItem, console
from scrapers import GovernmentScraper, CompanyScraper, NewsScraper, WechatScraper, GlobalResearchScraper, fetch_aihot_data
from processor import ContentOrganizer
from publisher import KnowledgePublisher, LocalPublisher
from utils.time_parser import parse_date_range_from_command, get_default_date_range
from fetch_ad_news import fetch_ad_industry_news

# 加载环境变量
load_dotenv()


class DailyAgent:
    """日报 Agent 主类"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        # 加载配置
        self.config = ConfigLoader(config_path)
        
        # 初始化缓存
        cache_path = self.config.get('cache.db_path', 'data/cache.db')
        self.cache = CacheManager(cache_path)
        
        # 初始化爬虫
        self.scrapers = {
            'government': GovernmentScraper(self.config, self.cache),
            'company': CompanyScraper(self.config, self.cache),
            'news': NewsScraper(self.config, self.cache),
            'wechat': WechatScraper(self.config, self.cache)
        }
        
        # 初始化处理器（带AI翻译支持）
        ai_config = self.config.config.get('ai', {})
        self.organizer = ContentOrganizer(
            api_key=os.environ.get('OPENAI_API_KEY'),
            api_base=ai_config.get('api_base'),
            model=ai_config.get('model')
        )
        
        # 初始化发布器
        self.ku_publisher = KnowledgePublisher(self.config)
        self.local_publisher = LocalPublisher()
        
        # 初始化全球研报搜索器
        self.research_scraper = GlobalResearchScraper()
    
    def run(self, sources: List[str] = None, publish: bool = True, start_date: str = None, end_date: str = None, include_research: bool = True) -> dict:
        """
        执行日报生成流程
        
        Args:
            sources: 指定要爬取的数据源，None 表示全部
            publish: 是否发布到知识库
            start_date: 开始日期，格式 "2026-04-30"
            end_date: 结束日期，格式 "2026-05-06"
            include_research: 是否包含研报搜索
        
        Returns:
            执行结果统计
        """
        console.print(Panel.fit(
            "[bold cyan]日报 Agent 启动[/bold cyan]\n"
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}" +
            (f"\n日期范围: {start_date} ~ {end_date}" if start_date and end_date else ""),
            title="Daily Report Agent"
        ))
        
        # 1. 爬取数据
        all_items = []
        stats = {}
        
        if sources is None:
            sources = ['government', 'company', 'news', 'wechat']
        
        for source in sources:
            if source in self.scrapers:
                console.print(f"\n[yellow]━━━ {source.upper()} ━━━[/yellow]")
                items = self.scrapers[source].scrape()
                all_items.extend(items)
                stats[source] = len(items)
        
        # 2. 从 AI HOT 拉取行业资讯和政策动向
        console.print(f"\n[yellow]━━━ AI HOT 资讯 ━━━[/yellow]")
        try:
            aihot_data = fetch_aihot_data(days=7)  # 最近7天

            # 行业资讯
            industry_items = aihot_data.get('industry', [])
            all_items.extend(industry_items)
            stats['aihot_industry'] = len(industry_items)

            # 政策动向
            policy_items = aihot_data.get('policy', [])
            all_items.extend(policy_items)
            stats['aihot_policy'] = len(policy_items)

            console.print(f"[green]AI HOT 行业资讯: {len(industry_items)} 条[/green]")
            console.print(f"[green]AI HOT 政策动向: {len(policy_items)} 条[/green]")
        except Exception as e:
            console.print(f"[yellow]AI HOT 数据拉取失败: {str(e)[:50]}[/yellow]")

        # 2.5 抓取自动驾驶行业资讯（官网优先 + Skill 补全）
        console.print(f"\n[yellow]━━━ 自动驾驶行业资讯（官网优先 + Skill补全） ━━━[/yellow]")
        try:
            ad_news, ad_stats = fetch_ad_industry_news()

            # 添加到行业资讯列表
            for item in ad_news:
                news_item = NewsItem(
                    title=item.get('title', ''),
                    content=item.get('summary', ''),
                    source=item.get('source', ''),
                    source_url=item.get('url', ''),
                    category='news'
                )
                all_items.append(news_item)

            stats['ad_official'] = ad_stats['official']['total_articles']
            stats['ad_skill'] = ad_stats['skill']['technology_search']
            stats['ad_merged'] = ad_stats['merged']['total_candidates']
            stats['ad_filtered'] = len(ad_news)

            console.print(f"[green]AD官网抓取: {ad_stats['official']['total_articles']} 条[/green]")
            console.print(f"[green]AD Skill补充: 技术搜索 {ad_stats['skill']['technology_search']} 条, "
                          f"百度 {ad_stats['skill']['baidu_search']} 条, "
                          f"Google {ad_stats['skill']['google_search']} 条[/green]")
            console.print(f"[green]AD行业资讯候选: {ad_stats['merged']['total_candidates']} 条, "
                          f"过滤后保留 {len(ad_news)} 条 (占比 {ad_stats['merged']['ad_ratio']}%)[/green]")
        except Exception as e:
            console.print(f"[yellow]自动驾驶资讯抓取失败: {str(e)[:50]}[/yellow]")
            stats['ad_official'] = 0
            stats['ad_skill'] = 0
            stats['ad_merged'] = 0
            stats['ad_filtered'] = 0
        
        # 3. 搜索全球研报
        if include_research:
            console.print(f"\n[yellow]━━━ 全球研报搜索 ━━━[/yellow]")
            research_reports = self.search_global_research()
            stats['research'] = len(research_reports)
        
        console.print(f"\n[bold]数据统计[/bold]")
        console.print(f"总计爬取: {len(all_items)} 条信息")
        for source, count in stats.items():
            console.print(f"  - {source}: {count} 条")
        
        if not all_items:
            console.print("[yellow]未获取到任何信息，请检查配置或网络连接[/yellow]")
            return {'total': 0, 'stats': stats, 'published': False}
        
        # 4. 过滤内容（只保留AI/自动驾驶相关）
        console.print("\n[yellow]正在过滤内容（AI/自动驾驶相关）...[/yellow]")
        original_count = len(all_items)
        all_items = self.organizer.filter_by_relevance(all_items, self.config.config)
        filtered_count = len(all_items)
        console.print(f"[cyan]过滤结果: {original_count} -> {filtered_count} 条[/cyan]")

        # 4.5 AD占比检查与补充
        ad_ratio_threshold = 40  # AD新闻占比目标
        from processor.content_filter import is_autonomous_driving_news
        ad_items = [item for item in all_items if hasattr(item, 'title') and is_autonomous_driving_news(item.title, item.content or '')]
        ad_count = len(ad_items)
        total_count = len(all_items) if all_items else 1
        ad_ratio = round(ad_count / total_count * 100, 1)
        console.print(f"[cyan]AD新闻占比: {ad_count}/{total_count} = {ad_ratio}% (目标 >= {ad_ratio_threshold}%)[/cyan]")

        # 如果AD占比不足，自动补充搜索
        if ad_ratio < ad_ratio_threshold and ad_ratio_threshold > 0:
            console.print(f"[yellow]AD新闻占比不足({ad_ratio}% < {ad_ratio_threshold}%)，触发补充搜索...[/yellow]")
            try:
                additional_ad_news, _ = fetch_ad_industry_news()
                for item in additional_ad_news:
                    news_item = NewsItem(
                        title=item.get('title', ''),
                        content=item.get('summary', ''),
                        source=item.get('source', ''),
                        source_url=item.get('url', ''),
                        category='news'
                    )
                    all_items.append(news_item)
                console.print(f"[green]补充获取 {len(additional_ad_news)} 条AD新闻[/green]")
            except Exception as e:
                console.print(f"[yellow]AD补充搜索失败: {str(e)[:50]}[/yellow])\n")
        
        # 5. 按日期过滤
        if start_date and end_date:
            console.print(f"\n[yellow]正在筛选日期范围 ({start_date} ~ {end_date})...[/yellow]")
            before_date_filter = len(all_items)
            all_items = self.organizer.filter_by_date_range(all_items, start_date, end_date)
            console.print(f"[cyan]日期筛选: {before_date_filter} -> {len(all_items)} 条[/cyan]")
        
        if not all_items:
            console.print("[yellow]过滤后无相关内容[/yellow]")
            return {'total': 0, 'stats': stats, 'published': False, 'filtered': 0}
        
        # 6. 去重
        all_items = self.organizer.deduplicate(all_items)
        console.print(f"[cyan]去重后: {len(all_items)} 条[/cyan]")
        
        # 7. 整理内容
        console.print("\n[yellow]正在整理内容...[/yellow]")
        report = self.organizer.organize(all_items)
        
        # 8. 保存/发布
        # 先保存到本地
        local_path = self.local_publisher.publish(report)
        
        # 发布到知识库
        published = False
        doc_id = None
        if publish and self.config.get('daily_report.auto_publish', True):
            doc_id = self.ku_publisher.publish(report)
            published = doc_id is not None
        
        # 9. 清理缓存
        expire_hours = self.config.get('cache.expire_hours', 24)
        self.cache.clean_old(expire_hours)
        
        # 输出结果
        console.print("\n" + "=" * 50)
        console.print(Panel.fit(
            f"[bold green]日报生成完成[/bold green]\n\n"
            f"本地文件: {local_path}\n" +
            (f"知识库: {self.ku_publisher.get_document_url(doc_id)}\n" if doc_id else "") +
            f"\n统计: 共 {report.total_count} 条信息",
            title="执行结果"
        ))
        
        return {
            'total': len(all_items),
            'stats': stats,
            'local_path': local_path,
            'doc_id': doc_id,
            'published': published
        }
    
    def test_source(self, source: str):
        """测试单个数据源"""
        if source not in self.scrapers:
            console.print(f"[red]未知的数据源: {source}[/red]")
            console.print(f"可用的数据源: {', '.join(self.scrapers.keys())}")
            return
        
        console.print(f"[cyan]测试数据源: {source}[/cyan]")
        items = self.scrapers[source].scrape()
        
        # 过滤相关内容
        original_count = len(items)
        items = self.organizer.filter_by_relevance(items, self.config.config)
        filtered_count = len(items)
        
        console.print(f"[yellow]过滤: {original_count} -> {filtered_count} 条相关内容[/yellow]")
        
        # 显示结果
        table = Table(title=f"{source} 测试结果")
        table.add_column("标题", style="cyan", max_width=50)
        table.add_column("来源", style="green")
        table.add_column("链接", style="blue")
        
        for item in items[:10]:
            table.add_row(
                item.title[:50] + ("..." if len(item.title) > 50 else ""),
                item.source,
                item.source_url[:40] + "..."
            )
        
        console.print(table)
        console.print(f"[bold]共 {filtered_count} 条相关结果[/bold]")
    
    def add_wechat_article(self, url: str):
        """添加微信公众号文章"""
        from scrapers.wechat import WechatArticleInput
        
        input_tool = WechatArticleInput()
        input_tool.add_article(url)
        console.print(f"[green]已添加文章链接: {url}[/green]")
        console.print("[cyan]提示: 运行 main.py --source wechat 来抓取已添加的文章[/cyan]")
    
    def search_global_research(self, days: int = 7) -> list:
        """
        搜索全球AI行业研报
        
        Args:
            days: 搜索最近几天的报告
            
        Returns:
            研报列表
        """
        from pathlib import Path
        import json
        
        console.print("[cyan]正在搜索全球研报来源...[/cyan]")
        
        # 执行搜索
        reports = self.research_scraper.search_all(days=days)
        
        # 显示摘要
        self.research_scraper.display_summary()
        
        # 保存研报数据
        if reports:
            data_dir = Path('data')
            data_dir.mkdir(exist_ok=True)
            
            # 保存为JSON
            from dataclasses import asdict
            data = [asdict(r) for r in reports]
            with open(data_dir / 'global_research_reports.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # 保存为Markdown
            md_content = self.research_scraper.to_markdown()
            with open(data_dir / 'global_research_reports.md', 'w', encoding='utf-8') as f:
                f.write(md_content)
            
            console.print(f"[green]研报数据已保存到 data/global_research_reports.json[/green]")
        
        return reports
    
    def build_website(self, date_str: str = None):
        """
        构建静态网站
        
        Args:
            date_str: 日期字符串，格式 YYYY-MM-DD，默认今天
        """
        from build_site import SiteBuilder, SiteConfig
        from pathlib import Path
        import json
        
        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")
        
        console.print(f"\n[bold cyan]━━━ 构建网站 ━━━[/bold cyan]")
        
        # 从环境变量获取网站URL
        import os
        site_url = os.environ.get('SITE_URL', '')
        
        # 配置网站
        site_config = SiteConfig(
            site_name="AI日报",
            site_description="每日政策动向、行业资讯与全球研报",
            base_url=site_url,
            timezone="UTC+8"
        )
        
        # 创建网站构建器
        builder = SiteBuilder(docs_dir="docs", config=site_config)
        
        # 准备网站数据
        daily_data = {
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
        
        # 加载政策动向数据（从government源）
        data_file = Path('data/site_data') / f"{date_str}.json"
        if data_file.exists():
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    daily_data = json.load(f)
            except:
                pass
        
        # 从日报输出文件加载完整数据
        report_file = Path('output') / f'日报_{date_str}.md'
        if report_file.exists():
            console.print(f"[cyan]从日报文件加载数据...[/cyan]")
            # 读取日报内容并解析
            with open(report_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 简单解析：按分类提取
            lines = content.split('\n')
            current_section = None
            
            for line in lines:
                if '**政策动向**' in line or '**政策**' in line:
                    current_section = 'policy'
                elif '**行业资讯**' in line or '**资讯**' in line:
                    current_section = 'news'
                elif '**研报**' in line or '**研究**' in line:
                    current_section = 'research'
        
        # 加载研报数据
        research_file = Path('data/global_research_reports.json')
        if research_file.exists():
            try:
                with open(research_file, 'r', encoding='utf-8') as f:
                    reports = json.load(f)
                    daily_data['research'] = reports
                    daily_data['stats']['research_count'] = len(reports)
            except:
                pass
        
        # 从缓存数据加载新闻和政策
        cache_files = list(Path('data').glob('*.json'))
        for cf in cache_files:
            if 'cache' in cf.name or 'research_candidates' in cf.name:
                continue
            
            try:
                with open(cf, 'r', encoding='utf-8') as f:
                    items = json.load(f)
                
                if not isinstance(items, list):
                    continue
                
                for item in items:
                    # 根据来源判断分类
                    title = item.get('title', '')
                    
                    # 创建统一格式的数据项
                    data_item = {
                        'title': title,
                        'summary': item.get('summary', '') or item.get('content', ''),
                        'source': item.get('source', ''),
                        'url': item.get('url', '') or item.get('source_url', ''),
                        'country': item.get('country', '中国'),
                        'date': item.get('date', '') or item.get('publishedAt', ''),
                        'keywords': item.get('keywords', [])
                    }
                    
                    # 判断分类
                    if '政策' in title or 'regulation' in title.lower() or item.get('category') == 'policy':
                        daily_data['policy'].append(data_item)
                    else:
                        daily_data['news'].append(data_item)
                        
            except:
                continue
        
        # 更新统计
        daily_data['stats']['policy_count'] = len(daily_data['policy'])
        daily_data['stats']['news_count'] = len(daily_data['news'])
        
        # 保存数据并构建网站
        builder.save_daily_data(date_str, daily_data)
        builder.build_all(date_str)
        
        console.print(f"[green]网站构建完成！[/green]")
        console.print(f"[cyan]政策动向: {daily_data['stats']['policy_count']} 条[/cyan]")
        console.print(f"[cyan]行业资讯: {daily_data['stats']['news_count']} 条[/cyan]")
        console.print(f"[cyan]每日研报: {daily_data['stats']['research_count']} 篇[/cyan]")
        console.print(f"[cyan]访问 docs/index.html 查看结果[/cyan]")
    
    def discover_research(self):
        """发现研报和专家访谈候选列表"""
        from scrapers.research import ResearchDiscovery
        
        finder = ResearchDiscovery()
        
        console.print("\n[bold cyan]===== 研究观点摘录 =====[/bold cyan]\n")
        
        # 搜索研报
        console.print("[yellow]1. 搜索相关研报...[/yellow]")
        reports = finder.discover_reports()
        finder.display_reports(reports)
        
        console.print("\n" + "="*60 + "\n")
        
        # 搜索专家访谈
        console.print("[yellow]2. 搜索专家访谈和观点...[/yellow]")
        opinions = finder.discover_expert_opinions()
        finder.display_expert_opinions(opinions)
        
        console.print("\n" + "="*60)
        console.print("\n[bold green]搜索完成！[/bold green]")
        console.print("[cyan]请根据上述列表：[/cyan]")
        console.print("  - 找到研报PDF文件，使用 --add-report <PDF路径> 输入")
        console.print("  - 找到专家访谈链接，使用 --add-interview <URL> 输入")
        
        # 保存候选列表到文件
        self._save_research_candidates(reports + opinions)
    
    def _save_research_candidates(self, candidates: list):
        """保存候选列表到文件"""
        import json
        from pathlib import Path
        from dataclasses import asdict
        
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)
        
        # 转换为可序列化的字典
        serializable = []
        for c in candidates:
            if hasattr(c, '__dataclass_fields__'):
                serializable.append(asdict(c))
            else:
                serializable.append(c)
        
        with open(data_dir / 'research_candidates.json', 'w', encoding='utf-8') as f:
            json.dump(serializable, f, ensure_ascii=False, indent=2)
        
        console.print(f"[dim]候选列表已保存到 data/research_candidates.json[/dim]")
    
    def add_research_report(self, pdf_path: str, source_name: str = ""):
        """添加研报PDF"""
        from scrapers.research import ContentExtractor, ResearchViewFormatter
        from pathlib import Path
        
        extractor = ContentExtractor()
        formatter = ResearchViewFormatter()
        
        # 提取内容
        result = extractor.extract_from_pdf(pdf_path)
        
        # 格式化输出
        md_content = formatter._format_report_view(1, result)
        
        # 保存到文件
        output_dir = Path('output/research')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        safe_title = result.get('title', 'report')[:20].replace(' ', '_').replace('/', '_')
        output_file = output_dir / f"report_{safe_title}.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        console.print(f"\n[green]研报观点已提取并保存到: {output_file}[/green]")
        console.print(f"\n{md_content}")
        
        # 保存到研究内容库
        result['source_type'] = 'report'
        self._save_research_insight(result)
    
    def add_expert_interview(self, url: str):
        """添加专家访谈URL"""
        from scrapers.research import ContentExtractor, ResearchViewFormatter
        from pathlib import Path
        
        extractor = ContentExtractor()
        formatter = ResearchViewFormatter()
        
        # 提取内容
        insight = extractor.extract_from_url(url)
        
        if insight is None:
            console.print("[red]提取失败，请检查URL是否正确[/red]")
            return
        
        # 格式化输出
        md_content = formatter._format_expert_view(1, insight)
        
        # 保存到文件
        output_dir = Path('output/research')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        safe_title = insight.title[:20].replace(' ', '_').replace('/', '_')
        output_file = output_dir / f"interview_{safe_title}.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        console.print(f"\n[green]专家观点已提取并保存到: {output_file}[/green]")
        console.print(f"\n{md_content}")
        
        # 保存到研究内容库
        self._save_research_insight({
            'title': insight.title,
            'source': insight.source,
            'source_type': 'interview',
            'source_url': insight.url,
            'insights': insight.key_quotes,
            'images': [],
            'date': insight.date,
            'author': insight.expert
        })
    
    def _save_research_insight(self, insight: dict):
        """保存研究观点到内容库"""
        import json
        from pathlib import Path
        
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)
        
        # 读取现有内容
        insights_file = data_dir / 'research_insights.json'
        insights = []
        if insights_file.exists():
            with open(insights_file, 'r', encoding='utf-8') as f:
                insights = json.load(f)
        
        # 添加新内容
        insights.append(insight)
        
        # 保存
        with open(insights_file, 'w', encoding='utf-8') as f:
            json.dump(insights, f, ensure_ascii=False, indent=2)
        
        console.print(f"[dim]研究观点已添加到内容库，当前共 {len(insights)} 条[/dim]")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='日报 Agent - 自动抓取整理政策与行业动态')
    parser.add_argument('--config', default='config/config.yaml', help='配置文件路径')
    parser.add_argument('--source', nargs='+', choices=['government', 'company', 'news', 'wechat'],
                        help='指定数据源（可多选）')
    parser.add_argument('--no-publish', action='store_true', help='不发布到知识库')
    parser.add_argument('--test', metavar='SOURCE', help='测试单个数据源')
    parser.add_argument('--add-wechat', metavar='URL', help='添加微信公众号文章链接')
    parser.add_argument('--schedule', action='store_true', help='启用定时任务模式')
    
    # 研报搜索参数
    parser.add_argument('--research', action='store_true', help='仅搜索全球研报')
    parser.add_argument('--research-days', type=int, default=7, metavar='DAYS', help='研报搜索天数范围（默认7天）')
    parser.add_argument('--no-research', action='store_true', help='不包含研报搜索')
    
    # 网站构建参数
    parser.add_argument('--build-site', action='store_true', help='构建静态网站')
    parser.add_argument('--date', metavar='DATE', help='指定日期，格式：2026-05-08')
    
    # 时间范围参数
    parser.add_argument('--start-date', metavar='DATE', help='开始日期，格式：2026-04-30')
    parser.add_argument('--end-date', metavar='DATE', help='结束日期，格式：2026-05-06')
    parser.add_argument('--time-command', metavar='COMMAND', help='自然语言时间指令，如"最近7天"或"2026-05-01 至 2026-05-08"')
    
    # 研究观点相关命令
    parser.add_argument('--discover-research', action='store_true', 
                       help='搜索研报和专家访谈候选列表')
    parser.add_argument('--add-report', metavar='PDF_PATH', 
                       help='添加研报PDF文件')
    parser.add_argument('--report-source', metavar='SOURCE', 
                       help='研报来源（如"麦肯锡"）')
    parser.add_argument('--add-interview', metavar='URL', 
                       help='添加专家访谈URL')
    
    args = parser.parse_args()
    
    # 创建 Agent
    agent = DailyAgent(args.config)
    
    # 根据参数执行不同操作
    if args.test:
        agent.test_source(args.test)
    elif args.add_wechat:
        agent.add_wechat_article(args.add_wechat)
    elif args.research:
        # 仅搜索研报
        reports = agent.search_global_research(days=args.research_days)
        console.print(f"\n[green]研报搜索完成，共 {len(reports)} 份研报[/green]")
    elif args.build_site:
        # 构建网站
        agent.build_website(args.date)
    elif args.discover_research:
        agent.discover_research()
    elif args.add_report:
        source_name = args.report_source or ""
        agent.add_research_report(args.add_report, source_name)
    elif args.add_interview:
        agent.add_expert_interview(args.add_interview)
    elif args.schedule:
        # 定时任务模式
        from scheduler import start_scheduler
        start_scheduler(agent)
    else:
        # 处理时间命令
        if args.time_command:
            date_range = parse_date_range_from_command(args.time_command)
            if date_range:
                args.start_date, args.end_date = date_range
                console.print(f"[green]解析时间范围: {args.start_date} 至 {args.end_date}[/green]")
            else:
                console.print("[red]无法解析时间指令，请使用正确的格式[/red]")
                console.print("[cyan]示例: '2026-05-01 至 2026-05-08' 或 '最近7天' 或 '昨天'[/cyan]")
                sys.exit(1)
        
        # 正常运行
        sources = args.source if args.source else None
        publish = not args.no_publish
        include_research = not args.no_research
        result = agent.run(
            sources=sources, 
            publish=publish,
            start_date=args.start_date,
            end_date=args.end_date,
            include_research=include_research
        )
        
        # 返回退出码
        sys.exit(0 if result['total'] > 0 else 1)


if __name__ == '__main__':
    main()