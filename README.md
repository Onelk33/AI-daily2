# AI日报 Agent

🤖 每日自动抓取政策动向、行业资讯与全球研报，生成全中文展示、按日归档的静态网站。

## ✨ 功能特性

### 三大板块自动抓取

1. **政策动向** - 国内外政府政策发布
   - 发改委、国务院、科技部、工信部等
   - **NEW**: 通过 AI HOT 搜索政策相关动态（关键词：政策、regulation、立法、标准等）
   
2. **行业资讯** - 人工智能/自动驾驶领域动态
   - 科技媒体：财新、36氪、第一财经、虎嗅、钛媒体、机器之心、量子位等
   - 国际媒体：TechCrunch、Reuters、VentureBeat、The Verge等
   - 公司官网：Waymo、Tesla、Pony.ai、WeRide、百度、腾讯、华为等
   - **NEW**: 集成 AI HOT (aihot.virxact.com) 实时资讯
     - 自动拉取 AI 模型发布、产品发布、行业动态
     - 支持关键词搜索（自动驾驶、robotaxi、人工智能等）
     - 与原有来源去重合并
   
3. **全球研报** - AI行业研究报告全网搜索
   - 国际券商：Goldman Sachs、Morgan Stanley、J.P. Morgan、UBS等
   - 国内券商：东方财富、同花顺、万得等
   - 咨询公司：McKinsey、BCG、Bain、Deloitte、艾瑞、易观等
   - 分析机构：Gartner、IDC、Forrester、CB Insights等
   - 学术社区：arXiv、SSRN、NBER、PaperWeekly等

### 核心特性

- ✅ **全中文展示** - 自动翻译所有外文内容，保留专业术语英文原名
- ✅ **按日归档** - 每日生成独立页面，历史日报永久保存
- ✅ **国别标记** - 每条信息标注来源国别（🇨🇳中国、🇺🇸美国等）
- ✅ **自动翻译** - 使用AI翻译确保专业性和准确性
- ✅ **网站生成** - 自动生成响应式静态网站
- ✅ **自动部署** - GitHub Actions每日18:00自动运行

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/your-repo.git
cd your-repo
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium  # 可选，用于动态网页抓取
```

### 3. 配置环境变量

创建 `.env` 文件：

```env
# OpenAI API（用于翻译和内容增强）
OPENAI_API_KEY=your_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1  # 或其他API地址
```

### 4. 运行日报生成

```bash
# 生成今日日报
python main.py

# 指定日期范围
python main.py --start-date 2026-05-01 --end-date 2026-05-08

# 使用自然语言时间指令
python main.py --time-command "最近7天"
python main.py --time-command "2026-05-01 至 2026-05-08"

# 仅搜索研报
python main.py --research --research-days 7

# 生成网站
python main.py --build-site
```

## 📖 使用指南

### 命令行参数

```bash
python main.py [选项]

主要选项：
  --source SOURCE [SOURCE ...]  指定数据源（government/company/news/wechat）
  --start-date DATE             开始日期（格式：2026-05-01）
  --end-date DATE               结束日期（格式：2026-05-08）
  --time-command COMMAND        自然语言时间指令
  --research                    仅搜索全球研报
  --research-days DAYS          研报搜索天数（默认7天）
  --build-site                  构建静态网站
  --no-publish                  不发布到知识库
  --schedule                    启用定时任务模式

其他选项：
  --test SOURCE                 测试单个数据源
  --add-wechat URL              添加微信公众号文章
  --discover-research           发现研报和专家访谈
  --config PATH                 指定配置文件路径
```

### 自然语言时间指令

支持多种中文时间表达：

```bash
# 日期范围
python main.py --time-command "2026-05-01 至 2026-05-08"
python main.py --time-command "2026年5月1日 至 2026年5月8日"

# 相对时间
python main.py --time-command "昨天"
python main.py --time-command "最近7天"
python main.py --time-command "本周"
python main.py --time-command "上周"
```

## 🌐 获取网站网址（新手必看）

### 前提条件

假设你已经：
1. 在GitHub创建了一个仓库（比如叫 `ai-daily`）
2. 把代码推送到了这个仓库

### 第一步：开启 GitHub Pages

1. 打开你的GitHub仓库页面
   - 网址格式：`https://github.com/你的用户名/ai-daily`
   
2. 点击仓库顶部的 **Settings（设置）** 标签

3. 在左侧菜单找到 **Pages**（在"Code and automation"分类下）

4. 在 "Build and deployment" 部分：
   - **Source** 选择：`Deploy from a branch`
   - **Branch** 选择：`gh-pages` 分支（如果没有这个分支，先等第一次Actions运行完）
   - **Folder** 选择：`/ (root)`
   
5. 点击 **Save**

### 第二步：获取你的网站网址

网站网址格式为：
```
https://你的GitHub用户名.github.io/你的仓库名/
```

例如：
- 用户名是 `zhangyuqi`
- 仓库名是 `ai-daily`
- 那么网址就是：`https://zhangyuqi.github.io/ai-daily/`

### 第三步：验证网站是否成功

1. 等待 1-3 分钟（GitHub Pages需要时间部署）

2. 访问你的网址，应该能看到日报网站

3. 如果看到 404 错误，请检查：
   - Settings → Pages 页面是否显示绿色提示框
   - 是否选择了正确的分支（gh-pages）和目录（root）

### 常见问题

**Q: 为什么访问网址显示 404？**

A: 可能的原因：
1. GitHub Actions 还没运行过 → 去 Actions 页面手动触发一次
2. `gh-pages` 分支不存在 → 检查 Actions 是否运行成功
3. Pages 设置错误 → 确保 Source 是 `gh-pages` 分支的 root 目录
4. 网址写错了 → 注意结尾要有 `/`，且用户名和仓库名要匹配

**Q: 网站显示空白或样式丢失？**

A: 检查 `docs/index.html` 中的路径是否正确，确保是相对路径（如 `../css/style.css`）

**Q: 如何查看部署状态？**

A: 
1. 进入仓库的 **Actions** 标签页
2. 查看最新的工作流运行记录
3. 绿色勾号表示成功，红色叉号表示失败

### 配置自动部署（可选）

如果你想让网站每天自动更新，需要配置 GitHub Secrets：

1. 进入仓库 Settings → Secrets and variables → Actions
2. 点击 **New repository secret**
3. 添加以下secrets：
   - Name: `OPENAI_API_KEY`，Value: 你的OpenAI API密钥
   - Name: `OPENAI_API_BASE`，Value: `https://api.openai.com/v1`（或你的API地址）

配置完成后，网站会在每天北京时间18:00自动更新。

## 🌐 GitHub Pages 部署（详细版）

### 方法一：自动部署（推荐）

**前提条件**：已完成上面的"获取网站网址"步骤

1. **配置 GitHub Secrets**
   
   进入仓库 Settings → Secrets and variables → Actions，添加：
   - `OPENAI_API_KEY`: 你的OpenAI API密钥（用于翻译功能）
   - `OPENAI_API_BASE`: API地址（可选，默认OpenAI）

2. **等待自动运行**
   
   - 每日北京时间18:00（UTC 10:00）自动运行
   - 或在 Actions 页面点击 "Run workflow" 手动触发

3. **查看部署结果**
   
   网址格式：
   ```bash
   # 替换下面的变量
   https://${你的GitHub用户名}.github.io/${你的仓库名}/
   
   # 例如：
   # 用户名: zhangyuqi
   # 仓库名: ai-daily
   # 网址: https://zhangyuqi.github.io/ai-daily/
   ```

### 方法二：手动部署

如果不想用GitHub Actions，也可以手动部署：

```bash
# 1. 本地生成网站
python main.py --build-site

# 2. 创建gh-pages分支
git checkout -b gh-pages

# 3. 添加docs目录
git add docs/
git commit -m "部署日报网站"

# 4. 推送分支
git push origin gh-pages

# 5. 回到主分支
git checkout main

# 6. 在GitHub Pages设置中选择gh-pages分支
```

## 🌐 GitHub Pages 部署

### 方法一：自动部署（推荐）

1. **配置 GitHub Secrets**
   
   进入仓库 Settings → Secrets and variables → Actions，添加：
   - `OPENAI_API_KEY`: 你的OpenAI API密钥
   - `OPENAI_API_BASE`: API地址（可选）

2. **启用 GitHub Pages**
   
   进入仓库 Settings → Pages：
   - Source: 选择 `gh-pages` 分支
   - Folder: 选择 `/ (root)`

3. **等待自动运行**
   
   - 每日北京时间18:00自动运行
   - 或在 Actions 页面手动触发

4. **访问网站**
   
   ```
   https://yourusername.github.io/your-repo/
   ```

### 方法二：手动部署

```bash
# 本地生成网站
python main.py --build-site

# 推送到GitHub
git add docs/
git commit -m "更新日报网站"
git push origin main

# 在GitHub Pages设置中选择docs目录
```

## 📁 项目结构

```
.
├── main.py                 # 主程序入口
├── build_site.py          # 网站构建脚本
├── config/
│   └── config.yaml        # 配置文件
├── core/                  # 核心模块
│   └── __init__.py
├── scrapers/              # 爬虫模块
│   ├── __init__.py
│   ├── government.py      # 政策爬虫
│   ├── company.py         # 公司动态爬虫
│   ├── news.py            # 新闻爬虫
│   ├── wechat.py          # 微信公众号爬虫
│   ├── global_research.py # 全球研报爬虫
│   └── research.py        # 研报处理
├── processor/             # 处理器模块
│   ├── __init__.py
│   ├── organizer.py       # 内容整理
│   └── enhancer.py        # 内容增强
├── utils/                 # 工具模块
│   ├── __init__.py
│   ├── translator.py      # 翻译工具
│   └── time_parser.py     # 时间解析
├── publisher/             # 发布器模块
│   ├── __init__.py
│   ├── knowledge.py       # 知识库发布
│   └── local.py           # 本地发布
├── docs/                  # 生成的网站文件
│   ├── index.html         # 首页（跳转到最新日报）
│   ├── history.html       # 历史日报列表
│   ├── daily/             # 每日日报
│   │   ├── 2026-05-01.html
│   │   ├── 2026-05-02.html
│   │   └── ...
│   └── css/               # 样式文件
│       └── style.css
├── data/                  # 数据文件
│   ├── cache.db           # 缓存数据库
│   ├── global_research_reports.json  # 研报数据
│   └── site_data/         # 网站数据
├── output/                # 输出文件
│   └── reports/           # 本地日报
├── .github/
│   └── workflows/
│       └── deploy.yml     # GitHub Actions工作流
├── requirements.txt       # Python依赖
├── .env                   # 环境变量（不提交）
└── README.md
```

## ⚙️ 配置说明

### config/config.yaml

```yaml
# AI配置
ai:
  api_base: "https://api.openai.com/v1"
  model: "gpt-4"

# 数据源配置
sources:
  wechat:
    enabled: true
    accounts: ["央视新闻", "人民日报"]
  government:
    enabled: true
  companies:
    enabled: true
  news:
    enabled: true

# 日报配置
daily_report:
  title_format: "【日报】{date} 政策与行业动态"
  auto_publish: true
  filter_keywords:
    - "AI"
    - "人工智能"
    - "自动驾驶"
    - "Robotaxi"
    - "大模型"
    # ...更多关键词

# 缓存配置
cache:
  enabled: true
  db_path: "data/cache.db"
  expire_hours: 24
```

## 🔧 高级功能

### 添加微信公众号文章

```bash
# 方式1：命令行
python main.py --add-wechat "https://mp.weixin.qq.com/s/xxxxx"

# 方式2：Web界面
python web_app.py
# 访问 http://localhost:5000
```

### 添加研报PDF

```bash
python main.py --add-report /path/to/report.pdf --report-source "麦肯锡"
```

### 测试数据源

```bash
# 测试单个数据源
python main.py --test government
python main.py --test news

# 测试研报搜索
python main.py --research --research-days 3
```

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- 感谢所有提供公开数据的网站和机构
- 本项目仅用于学习和研究目的，请遵守相关网站的robots协议

## ⚠️ 免责声明

本项目仅供学习交流使用，请勿用于商业用途。使用本工具抓取数据时请遵守相关网站的robots协议和服务条款。作者不对因使用本工具而产生的任何问题负责。

---

**Made with ❤️ by AI日报 Agent**