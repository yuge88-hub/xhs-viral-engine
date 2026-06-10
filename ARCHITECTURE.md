# ARCHITECTURE.md — 小红书爆款引擎架构与决策

> **目的**：记录"为什么这么选"——下次有人（或新窗口的我）问"为啥不用 X 库"时，看这里就懂。
> **何时更新**：选型变更 / 新增 Skill / 重大重构时。

---

## 🎯 系统目标

**输入**：行业关键词
**输出**：可发布的高胜率小红书爆款笔记（标题 + 正文 + 9 tag + 封面建议）

**核心循环**：
```
找爆款 → 拆爆款（WHY 爆）→ 挖痛点 → 逆推 prompt → 仿写 → 发布
```

---

## 🏗️ 6 个 Skill 分层

```
Layer 0: 工具链（DrissionPage / xhs-cli / scrapling / DeepSeek）
   ↓
Layer 1: 数据采集
   ├─ Skill 1  scanner           (找爆款 note_id)
   ├─ Skill 1.5 viral-analyzer   (拆爆款 — Phase A 新加)
   └─ Skill 2  pain-miner        (挖评论)
   ↓
Layer 2: 编排
   └─ Skill 3  batch-pipeline    (串 1+2, per-keyword 隔离)
   ↓
Layer 3: 智能生成
   ├─ Skill 4  rewriter v0.3     (套骨架 — 公式组合)
   └─ Skill 4  reverse_prompt    (逆推 prompt — Phase B 新加)
   ↓
Layer 4: 知识沉淀
   └─ Skill 5  obsidian-sync     (落 Obsidian vault)
```

---

## 🧠 关键设计决策

### D1：为什么用 DrissionPage 而不是 Playwright？

| 维度 | DrissionPage | Playwright |
|---|---|---|
| 启动速度 | 快（直连系统 Chrome） | 慢（要下 Chromium 130MB） |
| 中文文档 | 好 | 一般 |
| `as_expr=True` 坑 | 有（POSTMORTEM #17） | 没 |
| 系统 Chrome 复用 | `set_browser_path()` | `executable_path=` |
| 反检测 stealth | ❌ 没 | ✅ patchright 加持 |

**结论**：当前用 DrissionPage（启动快、文档好），**未来 Phase X 升级到 patchright**（stealth 更强）。

### D2：为什么用 scrapling 而不是裸 playwright？

scrapling 内部用 patchright（playwright 反检测 fork），**API 比 patchright 简单**：

| 能力 | scrapling | 裸 patchright |
|---|---|---|
| `bulk_stealthy_fetch(urls)` | ✅ 一行 | ❌ 手写循环 |
| `open_session` 复用 | ✅ | ❌ 每次新建 |
| `solve_cloudflare=True` | ✅ | ❌ 手动加 stealth |
| `screenshot` 原生 | ✅ | ✅ 但要 session_id |
| `block_webrtc=True` | ✅ 默认 | ❌ 默认开（要关） |

**结论**：scrapling 是 Phase A 抓 xhs 的首选。

### D3：为什么用 DeepSeek 而不是 Claude / GPT？

| 维度 | DeepSeek-flash | Claude Haiku | GPT-4o-mini |
|---|---|---|---|
| 价格 (input ¥/M) | 0.5 | 4 | 1.5 |
| 价格 (output ¥/M) | 1 | 20 | 6 |
| 中文 | 优 | 良 | 良 |
| 速度 | 快 | 中 | 中 |

**结论**：DeepSeek-flash 适合 Skill 4 / reverse_prompt 这种大批量 LLM 任务（159 痛点 + 5 仿写都用它）。**Claude 只用在需要深度推理的"逆推 prompt"环节**（v0.5 候选）。

### D4：为什么用 Obsidian 而不是 Notion / Logseq？

| 维度 | Obsidian | Notion | Logseq |
|---|---|---|---|
| 本地优先 | ✅ | ❌ | ✅ |
| 双向链接 | ✅ | ✅ | ✅ |
| Dataview 查询 | ✅ | ❌ | ✅ |
| 中文支持 | 优 | 良 | 优 |
| Vault 同步 | Git | 云 | Git |

**结论**：Obsidian 是本地 + Git 双重保险，符合"防丢机制"哲学。

### D5：为什么 Pain-miner 默认走 web（DrissionPage）而不是 xhs-cli API？

POSTMORTEM #1：xhs comments API 永远 captcha 限流。
- API: 1 次 captcha, 5-30 min 解封
- Web: 87 notes 0 captcha

**结论**：Web 路径是默认；API 仅作 fallback debug 用。

### D6：为什么 per-keyword 隔离？（Skill 3 编排器）

POSTMORTEM #10：batch 跑 captcha 串全场——一个关键词触发 captcha 会污染整个 batch。

**结论**：每个关键词独立 try/except + 独立 session，1 个 captcha 不影响其他。

---

## 🔁 数据流（端到端）

```
关键词 "AI 副业"
   ↓
Skill 3 batch-pipeline
   ├─ Skill 1 scanner → viral.json (87 notes, 0 captcha)
   │     ↓
   ├─ Skill 2 pain-miner (web 路径) → pain-miner.json (159 痛点)
   │     ↓
   └─ 输出: output/batch-full-5kw/{viral,pain-miner}-AI_副业.json

具体一条爆款 note_id (e.g. 666c0258000000001c0207a2)
   ↓
Skill 1.5 viral-analyzer (Phase A)  ← 新加
   ├─ viral_analyzer.py  → 4问+6维
   ├─ cover_analyzer.py  → 封面截图 + 视觉元素
   └─ benchmark_check.py → 4 标准评估
   ↓
Skill 4 v0.5 reverse_prompt (Phase B)  ← 新加
   ↓
Skill 4 v0.3 rewriter (套骨架)
   ↓
Skill 5 v0.2 obsidian-sync (落 vault: 04-benchmarks/ + 05-reverse-prompts/ + 03-rewrites/)
```

---

## 📦 工具链版本

| 工具 | 版本 | 装法 |
|---|---|---|
| xhs-cli-headless | 0.8.9 | `uv tool install --force git+https://github.com/kyalpha313/xhs-cli-headless` |
| DrissionPage | 4.1.1.2 | `pip install DrissionPage` |
| scrapling | latest | `pip install scrapling` |
| patchright (scrapling 内部) | bundled | `patchright install chromium` |
| DeepSeek API | deepseek-flash | env `DEEPSEEK_API_KEY` |
| Playwright Chromium | 1217 | `python -m playwright install chromium` |
| 系统 Chrome | 任意 | `C:\Program Files\Google\Chrome\Application\chrome.exe` |

---

## 🚧 未来候选架构

| 候选 | 何时 | 价值 |
|---|---|---|
| patchright 全面替换 DrissionPage | Phase X（captcha 顶不住时） | stealth + 反检测 |
| Obsidian Local REST API | Skill 5 v0.3 | 不用手动 sync |
| Claude API 用于 reverse_prompt | Phase B | 深度推理 |
| 真实账号 A/B 测试 | 持续 | 拿胜率表 |
