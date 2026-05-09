"""
工具脚本集合
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core import console


def show_config():
    """显示当前配置"""
    from core import ConfigLoader
    import yaml
    
    config = ConfigLoader()
    console.print("\n[bold cyan]当前配置:[/bold cyan]\n")
    console.print(yaml.dump(config.config, allow_unicode=True, default_flow_style=False))


def test_knowledge_base():
    """测试知识库连接"""
    from publisher import KnowledgePublisher
    from core import ConfigLoader
    
    config = ConfigLoader()
    publisher = KnowledgePublisher(config)
    
    console.print("\n[bold cyan]知识库配置:[/bold cyan]")
    console.print(f"  Repo GUID: {publisher.repo_guid}")
    console.print(f"  Parent Doc GUID: {publisher.parent_doc_guid}")
    console.print(f"  Creator: {publisher.creator}")
    
    # 尝试访问脚本
    if publisher.ku_script.exists():
        console.print(f"\n[green]✓ ku-operator 脚本存在: {publisher.ku_script}[/green]")
    else:
        console.print(f"\n[red]✗ ku-operator 脚本不存在: {publisher.ku_script}[/red]")


def clean_cache():
    """清理缓存"""
    from core import CacheManager, ConfigLoader
    
    config = ConfigLoader()
    cache_path = config.get('cache.db_path', 'data/cache.db')
    
    if Path(cache_path).exists():
        Path(cache_path).unlink()
        console.print(f"[green]✓ 缓存已清理: {cache_path}[/green]")
    else:
        console.print("[yellow]缓存文件不存在[/yellow]")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='工具脚本')
    parser.add_argument('command', choices=['config', 'test-ku', 'clean-cache'],
                        help='要执行的命令')
    
    args = parser.parse_args()
    
    if args.command == 'config':
        show_config()
    elif args.command == 'test-ku':
        test_knowledge_base()
    elif args.command == 'clean-cache':
        clean_cache()