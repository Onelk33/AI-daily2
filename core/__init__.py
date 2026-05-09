"""
日报 Agent 核心模块
"""
import os
import hashlib
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod
import yaml
import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


@dataclass
class NewsItem:
    """新闻条目数据结构"""
    title: str
    content: str
    source: str
    source_url: str
    publish_time: Optional[str] = None
    category: str = "general"
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def get_hash(self) -> str:
        """生成唯一标识，用于去重"""
        content = f"{self.title}{self.source_url}"
        return hashlib.md5(content.encode()).hexdigest()


class CacheManager:
    """缓存管理器，避免重复抓取"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news_cache (
                hash TEXT PRIMARY KEY,
                title TEXT,
                source TEXT,
                source_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def exists(self, item: NewsItem) -> bool:
        """检查新闻是否已存在"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM news_cache WHERE hash = ?",
            (item.get_hash(),)
        )
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    
    def save(self, item: NewsItem):
        """保存新闻到缓存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO news_cache (hash, title, source, source_url, data) VALUES (?, ?, ?, ?, ?)",
            (item.get_hash(), item.title, item.source, item.source_url, json.dumps(item.to_dict()))
        )
        conn.commit()
        conn.close()
    
    def clean_old(self, hours: int = 24):
        """清理过期缓存"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM news_cache WHERE created_at < ?",
            (datetime.now() - timedelta(hours=hours),)
        )
        conn.commit()
        conn.close()


class BaseScraper(ABC):
    """爬虫基类"""
    
    def __init__(self, config: Dict, cache: CacheManager):
        self.config = config
        self.cache = cache
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    @abstractmethod
    def scrape(self) -> List[NewsItem]:
        """执行爬取，返回新闻列表"""
        pass
    
    def fetch_page(self, url: str, encoding: str = 'utf-8') -> Optional[str]:
        """获取页面内容"""
        try:
            response = self.session.get(url, timeout=30)
            response.encoding = encoding
            return response.text
        except Exception as e:
            console.print(f"[red]获取页面失败: {url}, 错误: {e}[/red]")
            return None
    
    def parse_html(self, html: str) -> BeautifulSoup:
        """解析 HTML"""
        return BeautifulSoup(html, 'lxml')


class ConfigLoader:
    """配置加载器"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项（支持点号分隔的嵌套路径）"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value


def load_config() -> ConfigLoader:
    """加载配置"""
    return ConfigLoader()


def format_date(date: datetime = None, fmt: str = "%Y-%m-%d") -> str:
    """格式化日期"""
    if date is None:
        date = datetime.now()
    return date.strftime(fmt)