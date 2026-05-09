"""
百度知识库写入模块
将日报内容发布到知识库
"""
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime
from core import console
from processor import DailyReport


class KnowledgePublisher:
    """知识库发布器"""
    
    def __init__(self, config):
        self.config = config
        self.repo_guid = config.get('knowledge.repo_guid')
        self.parent_doc_guid = config.get('knowledge.parent_doc_guid')
        self.creator = config.get('knowledge.creator', os.environ.get('COMATE_USERNAME'))
        
        # ku-operator 脚本路径
        self.ku_script = Path(__file__).parent.parent.parent / ".comate" / "skills" / "ku-operator-comate" / "scripts" / "ku_operator.py"
    
    def publish(self, report: DailyReport, draft: bool = False) -> Optional[str]:
        """
        发布日报到知识库
        
        Args:
            report: 日报对象
            draft: 是否保存为草稿
        
        Returns:
            成功返回文档 ID，失败返回 None
        """
        console.print("[cyan]正在发布日报到知识库...[/cyan]")
        
        # 生成 Markdown 内容
        content = report.to_markdown()
        
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_file = f.name
        
        try:
            # 调用 ku-operator 创建文档
            result = self._create_document(
                title=report.title,
                content_file=temp_file,
                parent_guid=self.parent_doc_guid
            )
            
            if result:
                console.print(f"[green]日报已发布到知识库[/green]")
                console.print(f"[green]文档 ID: {result}[/green]")
                return result
            else:
                console.print("[red]✗ 发布失败[/red]")
                return None
                
        finally:
            # 清理临时文件
            Path(temp_file).unlink(missing_ok=True)
    
    def _create_document(self, title: str, content_file: str, parent_guid: str = None) -> Optional[str]:
        """调用 ku-operator 创建文档"""
        try:
            # 设置环境变量
            env = os.environ.copy()
            env['COMATE_USERNAME'] = self.creator
            
            # 构建命令
            cmd = [
                'python',
                str(self.ku_script),
                'create-doc',
                '--repo-guid', self.repo_guid,
                '--title', title,
                '--content-file', content_file
            ]
            
            if parent_guid:
                cmd.extend(['--parent-doc-guid', parent_guid])
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env
            )
            
            if result.returncode == 0:
                # 从输出中提取文档 ID
                output = result.stdout.strip()
                if output:
                    return output
                return "success"
            else:
                console.print(f"[red]创建文档失败: {result.stderr}[/red]")
                return None
                
        except Exception as e:
            console.print(f"[red]调用知识库 API 失败: {e}[/red]")
            return None
    
    def update_document(self, doc_id: str, content: str) -> bool:
        """更新已有文档"""
        # 保存到临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_file = f.name
        
        try:
            env = os.environ.copy()
            env['COMATE_USERNAME'] = self.creator
            
            cmd = [
                'python',
                str(self.ku_script),
                'edit-content',
                '--doc-id', doc_id,
                '--content-file', temp_file
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                env=env
            )
            
            return result.returncode == 0
            
        except Exception as e:
            console.print(f"[red]更新文档失败: {e}[/red]")
            return False
        finally:
            Path(temp_file).unlink(missing_ok=True)
    
    def get_document_url(self, doc_id: str) -> str:
        """生成文档访问链接"""
        return f"https://ku.baidu-int.com/knowledge/{self.repo_guid}/{doc_id}"


class LocalPublisher:
    """
    本地文件发布器
    将日报保存为本地 Markdown 文件（用于测试或备份）
    """
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def publish(self, report: DailyReport) -> str:
        """
        保存日报到本地
        
        Returns:
            文件路径
        """
        # 生成文件名
        filename = f"日报_{report.date}.md"
        filepath = self.output_dir / filename
        
        # 写入内容
        content = report.to_markdown()
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        console.print(f"[green]日报已保存到: {filepath}[/green]")
        return str(filepath)
    
    def list_reports(self) -> list:
        """列出所有已保存的日报"""
        reports = []
        for file in self.output_dir.glob("日报_*.md"):
            reports.append({
                'filename': file.name,
                'path': str(file),
                'date': file.stem.replace('日报_', '')
            })
        return sorted(reports, key=lambda x: x['date'], reverse=True)