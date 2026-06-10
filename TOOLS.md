# 🧰 TOOLS.md — 所有工具清单

> **每个工具干啥 / 为啥选它 / 怎么装 / 踩过啥坑**

---

## 🎭 工具地图

```
┌────────────────────────────────────────────────────────────────┐
│                       数据抓取层                                │
│  ┌──────────────┐ ┌────────────────┐ ┌─────────────────────┐  │
│  │ xhs-cli      │ │ DrissionPage   │ │ scrapling           │  │
│  │ (REST API)   │ │ (Playwright)   │ │ (StealthyFetcher)   │  │
│  │  搜索/whoami │ │  评论/列表    │ │  单条详情/截图       │  │
│  └──────────────┘ └────────────────┘ └─────────────────────┘  │
├────────────────────────────────────────────────────────────────┤
│                      计算 / LLM 层                              │
│  ┌──────────────┐ ┌────────────────┐ ┌─────────────────────┐  │
│  │ DeepSeek API │ │ Pillow         │ │ Python stdlib       │  │
│  │ (LLM 拆/仿)  │ │ (封面主色)     │ │ (json/re/Counter)   │  │
│  └──────────────┘ └────────────────┘ └─────────────────────┘  │
├────────────────────────────────────────────────────────────────┤
│                        输出层                                   │
│  ┌──────────────┐ ┌────────────────┐                          │
│  │ Markdown     │ │ Obsidian       │                          │
│  │ (报告)       │ │ (vault 同步)   │                          │
│  └──────────────┘ └────────────────┘                          │
└────────────────────────────────────────────────────────────────┘
```

---

## 🌐 Python 依赖 (requirements.txt)

### 抓取层

#### 1. **xhs-cli-headless** ⭐ 核心
- **干啥**: 小红书 CLI 工具, 提供 `xhs search / read / comments / whoami / login`
- **为啥选**: 比直接写 xhs API 包稳定, 内置 cookies 管理
- **装**: `uv tool install xhs-cli-headless==0.8.9 --force`
- **用在哪**: `skills/xhs-trending-scanner/scanner.py` (MVP 模式搜索) / `skills/xhs-comment-pain-miner/pain_miner.py` (兜底)
- **坑**:
  - 0.6.x 版本 captcha 误报严重 → 升 0.8.9 修
  - `comments` API 限流极严 → Skill 2 v0.2 改走 web 路径 (DrissionPage)
- **重要 flag**: `--json` (结构化输出) / `--sort popular` (按热度) / `--all` (拉全部评论)

#### 2. **DrissionPage** ⭐ 抓评论/列表
- **干啥**: Python 浏览器自动化 (像 Selenium 但更轻量, 中文友好)
- **为啥选**: xhs SPA 评论区只能 JS 渲染后抓 DOM, 限流比 API 宽松 10x
- **版本**: `DrissionPage==4.1.1.2`
- **装**: `pip install DrissionPage==4.1.1.2` (会自动拉 Chromium)
- **用在哪**: `skills/xhs-comment-pain-miner/pain_miner.py` (默认走 web) / `skills/xhs-trending-scanner/scanner.py` (完整模式取粉丝)
- **坑**:
  - 4.1.1.2 的 `run_js` 默认走 `Runtime.callFunctionOn` 是坏的 → 必须 `as_expr=True`
  - `page.text` 返 SPA 0 字节 → 改 `page.html_content`
  - `disable_resources=True` 死循环 → 改 False

#### 3. **scrapling** ⭐ 抓单条详情 + 截图
- **干啥**: 反检测爬虫库, `StealthyFetcher` 模拟真实浏览器指纹
- **为啥选**: 单条 xhs 笔记详情 0 captcha 通过率高, 支持自动截图
- **版本**: `scrapling>=0.2.0`
- **装**: `pip install scrapling` + `scrapling install` (装 Chromium)
- **用在哪**: `skills/skill-1.5-viral-analyzer/viral_analyzer.py` (拆 4问6维) / `cover_analyzer.py` (封面截图)

#### 4. **requests** — DeepSeek API 调用
- **干啥**: 标准 HTTP 库
- **装**: `pip install requests`
- **用在哪**: 6 处 (`viral_analyzer / cover_analyzer / benchmark_check / reverse_prompt / auto_fill / writer` 各自调 DeepSeek)
- **TODO**: 抽成 `_bootstrap/llm_client.py` 减重复 (架构债 STATUS#19)

### 计算/视觉层

#### 5. **Pillow (PIL)** — 封面主色提取
- **干啥**: 读 PNG / JPG, 算主色调
- **装**: `pip install Pillow`
- **用在哪**: `skills/skill-1.5-viral-analyzer/cover_analyzer.py`

#### 6. **python-dotenv** — 读 .env
- **装**: `pip install python-dotenv`
- **用在哪**: 当前没强依赖(代码用 `os.environ.get`), 但 SETUP.md 推荐用它简化 .env 载入

---

## 🤖 LLM 服务: DeepSeek

- **官网**: https://platform.deepseek.com/
- **申请 key**: https://platform.deepseek.com/api_keys
- **充值**: ¥10 起 (能跑 1000+ 条爆款拆解)
- **模型选**:
  - `deepseek-chat` (默认) — 直答不思考, ¥0.001/1k input tokens, 极便宜, 适合 4问6维 / 仿写 prompt
  - `deepseek-v4-flash` — reasoning 模式, 拆解质量更高, ~3x 价
- **API base**: `https://api.deepseek.com/v1/chat/completions`
- **OpenAI 兼容**: 是, 直接用 OpenAI SDK 也可
- **环境变量**:
  ```
  DEEPSEEK_API_KEY=sk-...
  DEEPSEEK_MODEL=deepseek-chat
  ```

### 实测成本 (Phase A-I 累计)
- 全栈跑 1 关键词 (Skill 1+2+1.5×5+4×2) ≈ **¥0.02**
- 21k tokens (Phase A v0.4.0 实测) = ¥0.01
- 全项目至今总花费 < ¥1

---

## 🗂 Obsidian (可选)

- **官网**: https://obsidian.md/
- **干啥**: 本地 markdown 笔记 + 双向链接 + graph view
- **用在哪**: `skills/skill-5-obsidian-sync/sync.py` 把所有产物同步成 YAML frontmatter + `[[wikilinks]]`
- **vault 结构** (sync 后):
  ```
  <vault>/小红书爆款引擎/
  ├── 00-index.md          ← 首页索引
  ├── 01-raw/              ← Skill 1+2 数据
  ├── 02-formula/          ← Skill 4 公式
  └── 03-rewrites/         ← Skill 4 仿写
  ```

---

## 🛡 Claude Code (开发协作工具)

- **官网**: https://claude.com/claude-code
- **干啥**: AI 编码助手, 本项目 100% Claude Code 协作开发
- **配置**: `.claude/` 目录 (已 `.gitignore` 排除, 不发 GitHub)
- **关键习惯** (`CLAUDE.md` 强制):
  - 任何长任务必须用 `STATUS.md` + `ARCHITECTURE.md` + `CONVENTIONS.md` 三件套防丢
  - PostToolUse hook 自动提醒更新 STATUS
  - codegraph MCP 提供结构化代码查询

---

## 📦 完整依赖速览

见 [requirements.txt](requirements.txt). 一行装完:
```powershell
pip install -r requirements.txt
```

| 包 | 版本 | 用途 |
|---|---|---|
| `requests` | >=2.31.0 | DeepSeek API |
| `DrissionPage` | ==4.1.1.2 | 抓评论/列表 |
| `scrapling` | >=0.2.0 | 抓单条/截图 |
| `Pillow` | >=10.0.0 | 封面主色 |
| `python-dotenv` | >=1.0.0 | (可选) 读 .env |

`xhs-cli-headless` 单独装(via `uv tool install`), 不在 requirements.txt.

---

## 🐛 工具相关坑速查

| 坑 | 修 | POSTMORTEM 编号 |
|---|---|---|
| xhs `comments` API captcha | Skill 2 改 DrissionPage web 路径 | #2 |
| DrissionPage `run_js` 失效 | 加 `as_expr=True` | #5 |
| DrissionPage `page.text` 空 | 改 `page.html_content` | #25 |
| scrapling 编码乱码 | `utf-8-sig` 读 BOM | #26 |
| xhs `likedCount":"2万"` 解析 | `parse_xhs_count("2万") → 20000` | #27 |
| `cover_path.relative_to` 错 | try/except fallback 绝对路径 | #30 |
| 中文双引号 SyntaxError | 改用「」 | #31 #32 |
| Windows GBK 终端乱码 | `from skills._bootstrap import *` | #33 |

---

## 🔮 未集成工具 (考察过没用)

| 工具 | 为啥不用 |
|---|---|
| **MediaCrawler** | 设计偏大型工程, 我们 5 Skill 已闭环 |
| **browser-use** | LLM 驱动浏览器, token 成本太高 |
| **page-agent** (阿里) | 客户端 GUI agent, 服务器爬虫场景不适用 |
| **playwright (直接用)** | DrissionPage 已封装好, 不必降级 |
