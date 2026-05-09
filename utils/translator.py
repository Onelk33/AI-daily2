"""
翻译模块
将所有非中文内容翻译成专业、地道的中文
支持多种翻译后端
"""
import os
import re
from typing import Optional, List
from abc import ABC, abstractmethod
from rich.console import Console

console = Console()


class TranslationError(Exception):
    """翻译错误"""
    pass


class BaseTranslator(ABC):
    """翻译器基类"""
    
    @abstractmethod
    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "zh") -> str:
        """
        翻译文本
        
        Args:
            text: 待翻译文本
            source_lang: 源语言（auto表示自动检测）
            target_lang: 目标语言
            
        Returns:
            翻译后的文本
        """
        pass
    
    def batch_translate(self, texts: List[str], source_lang: str = "auto", target_lang: str = "zh") -> List[str]:
        """批量翻译"""
        return [self.translate(t, source_lang, target_lang) for t in texts]


class OpenAITranslator(BaseTranslator):
    """使用OpenAI API进行翻译"""
    
    def __init__(self, api_key: str = None, api_base: str = None, model: str = "gpt-4"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.api_base = api_base or os.environ.get("OPENAI_API_BASE", "https://api.openai.com/v1")
        self.model = model
        self.enabled = bool(self.api_key)
    
    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "zh") -> str:
        if not self.enabled:
            return text
        
        if not text or len(text.strip()) < 2:
            return text
        
        # 检测是否已经是中文
        if self._is_chinese(text):
            return text
        
        try:
            import openai
            
            prompt = f"""请将以下文本翻译成专业、地道的中文。

要求：
1. 专业术语可保留英文原名（如"Robotaxi"、"LLM"、"LoRA"），首次出现时用括号标注中文含义
2. 保持原文的专业性和准确性
3. 摘要类内容要包含具体数据或案例
4. 如果原文已经是中文，直接返回原文

原文：
{text}

翻译结果："""

            client = openai.OpenAI(api_key=self.api_key, base_url=self.api_base)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位专业的科技和金融领域翻译专家，擅长将英文研究报告和新闻翻译成准确、专业的中文。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            console.print(f"[yellow]翻译失败: {str(e)[:50]}[/yellow]")
            return text + " [翻译未完成]"
    
    def _is_chinese(self, text: str) -> bool:
        """检测文本是否主要是中文"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(re.sub(r'\s', '', text))
        if total_chars == 0:
            return True
        return chinese_chars / total_chars > 0.5


class MockTranslator(BaseTranslator):
    """模拟翻译器（用于测试或无API时）"""
    
    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "zh") -> str:
        # 检测是否是中文
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(re.sub(r'\s', '', text))
        
        if total_chars > 0 and chinese_chars / total_chars > 0.5:
            return text
        
        # 对于英文，添加翻译标记
        return text + " [需翻译]"


class Translator:
    """
    主翻译器类
    自动选择可用的翻译后端
    """
    
    def __init__(self, api_key: str = None, api_base: str = None, model: str = "gpt-4"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.api_base = api_base or os.environ.get("OPENAI_API_BASE")
        self.model = model
        
        # 初始化翻译后端
        if self.api_key:
            self.backend = OpenAITranslator(self.api_key, self.api_base, self.model)
            console.print("[green]翻译模块: 使用 OpenAI API[/green]")
        else:
            self.backend = MockTranslator()
            console.print("[yellow]翻译模块: 未配置API，使用模拟模式[/yellow]")
    
    def translate(self, text: str, source_lang: str = "auto", target_lang: str = "zh") -> str:
        """翻译单个文本"""
        if not text:
            return text
        return self.backend.translate(text, source_lang, target_lang)
    
    def translate_report(self, report: dict) -> dict:
        """
        翻译研报信息
        
        Args:
            report: 研报字典，包含 title, summary 等字段
            
        Returns:
            翻译后的研报字典
        """
        result = report.copy()
        
        # 翻译标题
        if result.get('title') and result.get('language') != '中文':
            result['title_translated'] = self.translate(result['title'])
        
        # 翻译摘要
        if result.get('summary') and result.get('language') != '中文':
            result['summary_translated'] = self.translate(result['summary'])
        
        return result
    
    def translate_news(self, news_item: dict) -> dict:
        """
        翻译新闻条目
        
        Args:
            news_item: 新闻字典
            
        Returns:
            翻译后的新闻字典
        """
        result = news_item.copy()
        
        # 翻译标题
        if result.get('title'):
            result['title'] = self.translate(result['title'])
        
        # 翻译摘要
        if result.get('summary') or result.get('content'):
            text = result.get('summary') or result.get('content')
            result['summary'] = self.translate(text)
        
        return result
    
    def detect_language(self, text: str) -> str:
        """检测文本语言"""
        if not text:
            return 'unknown'
        
        # 统计中文字符
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        # 统计英文字符
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        # 统计日文字符
        japanese_chars = len(re.findall(r'[\u3040-\u309f\u30a0-\u30ff]', text))
        
        total = chinese_chars + english_chars + japanese_chars
        if total == 0:
            return 'unknown'
        
        if chinese_chars / total > 0.3:
            return '中文'
        elif english_chars / total > 0.3:
            return '英文'
        elif japanese_chars / total > 0.3:
            return '日文'
        else:
            return '其他'


# 全局翻译器实例
_translator = None


def get_translator(api_key: str = None, api_base: str = None, model: str = "gpt-4") -> Translator:
    """获取全局翻译器实例"""
    global _translator
    if _translator is None:
        _translator = Translator(api_key, api_base, model)
    return _translator


def translate_text(text: str, api_key: str = None) -> str:
    """便捷函数：翻译单个文本"""
    translator = get_translator(api_key)
    return translator.translate(text)