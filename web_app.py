"""
微信文章录入 Web 服务
简单的网页界面，用于手动添加微信文章链接
"""
from flask import Flask, render_template, request, jsonify
from datetime import datetime
from pathlib import Path
import json
import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core import console

app = Flask(__name__)

# 数据文件路径
DATA_DIR = Path('data')
DATA_DIR.mkdir(exist_ok=True)
ARTICLES_FILE = DATA_DIR / 'wechat_articles.json'


def load_articles():
    """加载已保存的文章"""
    if ARTICLES_FILE.exists():
        with open(ARTICLES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_article(url, title='', note=''):
    """保存文章链接"""
    articles = load_articles()
    
    # 检查是否已存在
    for article in articles:
        if article['url'] == url:
            return False, '该链接已存在'
    
    # 添加新文章
    article = {
        'url': url,
        'title': title,
        'note': note,
        'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'pending'  # pending, processed
    }
    articles.append(article)
    
    with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    return True, '添加成功'


def delete_article(url):
    """删除文章"""
    articles = load_articles()
    articles = [a for a in articles if a['url'] != url]
    
    with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    return True


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/articles', methods=['GET'])
def get_articles():
    """获取所有文章"""
    articles = load_articles()
    return jsonify({
        'success': True,
        'data': articles,
        'total': len(articles)
    })


@app.route('/api/articles', methods=['POST'])
def add_article():
    """添加文章"""
    data = request.get_json()
    url = data.get('url', '').strip()
    title = data.get('title', '').strip()
    note = data.get('note', '').strip()
    
    if not url:
        return jsonify({'success': False, 'message': '请输入文章链接'})
    
    # 验证是否为微信文章链接
    if 'mp.weixin.qq.com' not in url:
        return jsonify({'success': False, 'message': '请输入微信公众号文章链接'})
    
    success, message = save_article(url, title, note)
    return jsonify({'success': success, 'message': message})


@app.route('/api/articles/<path:url>', methods=['DELETE'])
def remove_article(url):
    """删除文章"""
    delete_article(url)
    return jsonify({'success': True, 'message': '删除成功'})


@app.route('/api/articles/clear', methods=['POST'])
def clear_processed():
    """清除已处理的文章"""
    articles = load_articles()
    articles = [a for a in articles if a['status'] == 'pending']
    
    with open(ARTICLES_FILE, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    
    return jsonify({'success': True, 'message': '已清除处理过的文章'})


if __name__ == '__main__':
    print("=" * 50)
    print("微信文章录入系统")
    print("=" * 50)
    print(f"访问地址: http://localhost:5000")
    print(f"数据文件: {ARTICLES_FILE}")
    print("=" * 50)
    app.run(debug=True, host='0.0.0.0', port=5000)