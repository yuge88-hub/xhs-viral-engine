# 🚀 xhs-viral-engine

> 小红书全栈爆款笔记自动化引擎 — **抓 → 拆 → 仿 → 写 → 发**

[![Status](https://img.shields.io/badge/status-private--alpha-orange.svg)]()
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)]()
[![LLM](https://img.shields.io/badge/LLM-DeepSeek-purple.svg)]()

---

## 💡 这是什么

一套 **5 个 Skill 串联**的小红书爆款笔记自动化引擎:

```
关键词 → ① 抓爆款 → ② 拆解原理 → ③ 挖评论痛点 → ④ 仿写 prompt → ⑤ 同步 Obsidian
```

**核心价值**:
- 🎯 **真素人爆款定位** — 自动过滤 35w+ 大号,只留 < 3000 粉的低粉爆款(新号能学的)
- 🔬 **4 问 + 6 维 LLM 深拆** — 不是表面"标题模板",是逆推爆款的角色 DNA / 读者画像 / 内容结构
- 💬 **评论区痛点反向选题** — 绕过 xhs API captcha 走 web 路径,0 触发抓 100+ 痛点/关键词
- 📝 **一键仿写 prompt** — Top 5 爆款一条命令出 5 段式 prompt,直接发 LLM 仿写
- 🗂 **Obsidian 双向链接** — 自动 YAML frontmatter + `[[wikilinks]]`,知识库化

**实测产出** (AI 知识库赛道, 1 关键词):
- 9 条真素人爆款 (< 3000 粉)
- 24 评论痛点 (累计 1190 赞)
- 5 条 Top viral notes 完整 4问+6维 拆解 + 封面 + benchmark
- 17,520 字符 / 423 行情报报告(`output/ai-knowledge-base/intelligence-report-v3-*.md`)
- 2 条「一键复制版」仿写 prompt (Top 1/2)

---

## 🎯 5 个 Skill 全景

```
┌─────────── Skill 1: xhs-trending-scanner ───────────┐
│ scanner.py           按关键词抓爆款 (含 xsec_token)  │
│ quality_scorer.py    互动率+时间衰减打分            │
│ account_analyzer.py  按账号聚合 (Step ④)            │
└──────────────────────────────────────────────────────┘
                  ↓ viral.json
┌─────────── Skill 1.5: viral-analyzer ────────────────┐
│ viral_analyzer.py    4 问 + 6 维 LLM 拆解            │
│ cover_analyzer.py    封面截图 + 主色 + 视觉规则      │
│ benchmark_check.py   4 标准对标评分                  │
│ run_all.py           端到端封装                      │
└──────────────────────────────────────────────────────┘
                  ↓ analysis.json + cover + benchmark
┌─────────── Skill 2: xhs-comment-pain-miner ──────────┐
│ pain_miner.py        DrissionPage 抓评论 (绕 captcha) │
│ topic_generator.py   反向聚合 → 选题库 (Step ⑥)     │
└──────────────────────────────────────────────────────┘
                  ↓ pains.json
┌─────────── Skill 3: batch-keyword-pipeline ──────────┐
│ run.py               多关键词编排器 (Skill 1+2 串联) │
└──────────────────────────────────────────────────────┘
                  ↓ batch-*.json
┌─────────── Skill 4: viral-rewriter ──────────────────┐
│ reverse_prompt.py    4问6维 → 5段式仿写 prompt ⭐    │
│ writer.py            reverse-prompt → LLM 写笔记     │
│ rewriter.py          v0.3 公式版 (老路, 保留参考)    │
│ auto_fill.py         v0.4 骨架填空 (老路, 保留参考)  │
└──────────────────────────────────────────────────────┘
                  ↓ {note_id}-imitate.md
┌─────────── Skill 5: obsidian-sync ───────────────────┐
│ sync.py              全部产物 → Obsidian vault       │
└──────────────────────────────────────────────────────┘
```

---

## 🚀 30 秒开始

```powershell
# 1. clone + 进目录
git clone https://github.com/yuge88-hub/xhs-viral-engine.git
cd xhs-viral-engine

# 2. 装依赖 (Python 3.11+)
pip install -r requirements.txt

# 3. 装 xhs-cli (抓小红书数据)
uv tool install xhs-cli-headless==0.8.9 --force

# 4. 登录小红书 (扫码, 一次性)
xhs login
xhs whoami  # 验证: 应返回你的 nickname

# 5. 配 DeepSeek API key
copy .env.example .env
# 编辑 .env, 把 sk-xxxxxxxx 替换成你的真 key
# 申请: https://platform.deepseek.com/api_keys

# 6. 跑一个关键词的全流程 (~5 min, ~¥0.02)
python skills\batch-keyword-pipeline\run.py --keywords "AI 副业" --pages 1
```

输出在 `output/batch-YYYYMMDD-HHMMSS/`,包含:
- `*-summary.md` — 跨关键词概览
- `*-viral.md` — Top N 爆款列表
- `*-pains.md` — 评论痛点按关键词分组
- `*-raw.json` — 完整原始数据

---

## 📖 完整文档

| 文档 | 干啥 |
|---|---|
| [SETUP.md](SETUP.md) | **首次安装** — 从零到第一份报告 |
| [TOOLS.md](TOOLS.md) | **所有工具清单** — xhs-cli / DrissionPage / scrapling / DeepSeek 各干啥 |
| [STATUS.md](STATUS.md) | **当前进度** — Phase A-I 全记录 + 待办 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | **架构决策** — 为啥这么选 |
| [CONVENTIONS.md](CONVENTIONS.md) | **代码规范** — 命名/目录/依赖 |
| [POSTMORTEM.md](POSTMORTEM.md) | **30+ 踩过的坑** — captcha / 编码 / 解析 / SDK |
| `skills/<name>/README.md` | **每个 Skill 的详细 API + 示例** |

---

## 🎨 Phase 进度

- ✅ **Phase A-C**: 5 Skill MVP 闭环
- ✅ **Phase D**: 编码基线重构 (`_bootstrap/console_utf8.py`)
- ✅ **Phase E-F**: 细分市场实战 (儿童身高 / AI 知识库)
- ✅ **Phase G-I**: 关键词全链路 + Top 5 真拆 + 仿写 prompt
- 🔵 **Phase J**: 项目发布到 GitHub (本次)
- 🔜 **Phase K**: Step ⑩ 生图 3:4 卡片 / 架构 P0 重构

---

## ⚖️ License

本仓库以 [MIT License](LICENSE) 发布 — 欢迎自由使用、修改、再分发。

第三方代码归属:
- `skills/skill-1.5-viral-analyzer/cover_analyzer.py` 用 [scrapling](https://github.com/D4Vinci/Scrapling) (BSD)
- `skills/xhs-trending-scanner/scanner.py` 用 [xhs-cli](https://github.com/REA1R/xhs-cli) 间接
- LLM 调用 [DeepSeek API](https://platform.deepseek.com/)

---

**📌 重要**: 这个项目用 **Claude Code** 协作开发, 所有 Phase / 决策 / 踩坑 / 修复记录在 `STATUS.md` / `POSTMORTEM.md` 三件套里, **下次重启对话第一句话**:

> "请读 STATUS.md 继续 Phase X"
