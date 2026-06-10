# CONVENTIONS.md — 代码规范与约定

> **目的**：让所有 Skill 写出来一个味儿——新人（或新窗口的我）看到不用猜。
> **何时更新**：风格变更 / 新增约定时。

---

## 📁 目录结构

```
web-clipper-master/
├── STATUS.md                ← 任务连续性（必读）
├── ARCHITECTURE.md          ← 架构决策（必读）
├── CONVENTIONS.md           ← 本文件
├── POSTMORTEM.md            ← 踩坑记录（实跑前必读）
│
├── skills/                  ← 所有微技能
│   ├── xhs-trending-scanner/    ← Skill 1
│   ├── skill-1.5-viral-analyzer/  ← Skill 1.5 (Phase A)
│   ├── xhs-comment-pain-miner/  ← Skill 2
│   ├── batch-keyword-pipeline/  ← Skill 3
│   ├── skill-4-viral-rewriter/  ← Skill 4
│   └── skill-5-obsidian-sync/   ← Skill 5
│
├── output/                  ← 一切中间产物（git ignored）
│   ├── batch-{mvp,full}-5kw/   ← Skill 1+2+3 输出
│   ├── skill-4-formula-rewrites-v{N}/  ← Skill 4 输出
│   └── skill-1.5-viral-analyzer-v{N}/  ← Skill 1.5 输出
│
└── bin/, chrome/, webpack/, src/  ← Web Clipper 原项目（不动）
```

---

## 🏷️ Skill 命名

| 类别 | 命名格式 | 例子 |
|---|---|---|
| 微技能目录 | `{number-or-name}-{purpose}` | `xhs-trending-scanner` / `skill-1.5-viral-analyzer` |
| 主脚本 | `{purpose}.py` | `scanner.py` / `pain_miner.py` / `viral_analyzer.py` |
| 测试脚本 | `test_{purpose}.py` | `test_xhs_mcp.py` |
| 配置 | `config.json` / `.env` | |
| 文档 | `README.md` | |

**Skill 1.5 例外**：用 `skill-1.5-` 前缀而不是 `xhs-`，因为它跨 Skill 1（数据）+ Skill 4（应用）的中转。

---

## 🐍 Python 风格

### 通用
- Python 3.10+，用 `from __future__ import annotations`
- 函数签名 type hints 必填
- 中文注释 OK（用户母语），但**标识符英文**
- 单文件 ≤ 500 行（拆模块）

### 导入顺序
```python
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests  # 第三方
from DrissionPage import ChromiumPage  # 第三方
```

### 错误处理
```python
# 不要吞错
try:
    result = fetch(url)
except Exception as e:
    logger.error(f"fetch {url} 失败: {e}")
    raise  # 让上层 try/except 决定
```

### 输出
- 用户消息用 `print()`
- 日志用 `logger.info/warn/error`
- 不要 `print()` + 写文件混用——选一种

### 编码 — ⚠️ 项目级基线 (POSTMORTEM #17/#25/#26/#33)

**2026-06-09 升级**: 之前每个脚本开头手写 `sys.stdout.reconfigure(encoding="utf-8")` (3 行)
反复在 #17/#25/#26 出问题。**新基线**: 任何 xhs skill 脚本**第一行** 必加：

```python
from __future__ import annotations
from skills._bootstrap import *  # noqa: F401,F403  ← UTF-8 基线
import argparse
...
```

`skills/_bootstrap/console_utf8.py` 会**自动**：
1. `sys.stdout / sys.stderr.reconfigure(encoding="utf-8")`
2. 幂等 (重复 import 不报错)
3. 设 `PYTHONIOENCODING=utf-8` (子 subprocess 也走 UTF-8)
4. Windows 下 `SetConsoleOutputCP(65001)` (PowerShell 终端)

**部署到子进程（subprocess.run 启 Python）**:
- `skills/sitecustomize.py` 已写，**PYTHONPATH 加 `skills/`** 即可全局生效：
  ```powershell
  setx PYTHONPATH "C:\Users\张哥\Downloads\web-clipper-master\skills;%PYTHONPATH%"
  ```
- 没设 PYTHONPATH 也行 — 任何 xhs skill 脚本里都有 `from skills._bootstrap import *`

**反模式**:
- ❌ 每个脚本手写 3 行 `sys.stdout.reconfigure(encoding="utf-8")` (会漏, 已多次出 bug)
- ❌ 用 `sys.stdout = io.TextIOWrapper(...)` 重写 (会丢 buffered 状态, 复杂)
- ❌ 不写 `errors="replace"` (emoji 撞 GBK 抛 UnicodeEncodeError)

**验证基线生效**:
```powershell
python -c "from skills._bootstrap import *; print('OK ✅', sys.stdout.encoding)"
# 应输出: OK ✅ utf-8
```

---

## 📊 JSON / Markdown 输出

### JSON
```json
{
  "skill": "xhs-comment-pain-miner",
  "version": "0.2.0",
  "input_notes": 7,
  "stats": {...},
  "per_note": [...]
}
```
- 顶层必有 `skill` + `version`
- 时间戳 ISO 8601
- 空值用 `null`（不要 `""`）

### Markdown
- 标题用 `##` / `###`（不要 `#` 当主标题，正文用 H2 起）
- 表格必带表头分隔线
- 引用证据用 `> 原文引用`（不是斜体）
- 代码块注明语言

---

## 🔐 安全（POSTMORTEM #21）

- **API key 必走 `.env`** + `.gitignore`
- **Cookie 文件** 单独目录，git ignored
- **不写盘 / 不硬编码** 任何凭证
- **不打印** 完整 token / cookie

---

## 🛠️ 命令约定

| 场景 | 约定 |
|---|---|
| PowerShell 跑 Python | `python script.py --arg value`（不用 `python3`） |
| 后台跑 | `run_in_background=True`（不用 `Start-Process`） |
| 中文文件名 | 用 ` `（空格）不用 `_`（下划线）——可读性 |
| 路径引号 | 双引号包路径（PowerShell 不吃 `\`） |
| 编码 | PowerShell 不重定向（POSTMORTEM #5） |

---

## 📝 文档约定

### README.md 必含
1. **TL;DR**（一句话干啥）
2. **角色定位**（在哪个 Skill 流里）
3. **Pipeline 图**（ASCII 框图）
4. **输入 / 输出**（表格）
5. **调用示例**（PowerShell 3 个）
6. **已知限制**
7. **版本演进**

### STATUS.md 必含
- **当前阶段**（✅/🚧/❌）
- **进行中**（TodoWrite 同步）
- **已完成**（最近一波）
- **阻塞点**

---

## 🚦 状态符号

| 符号 | 含义 |
|---|---|
| ✅ | 已完成 |
| 🚧 | 进行中 |
| ❌ | 失败 / 阻塞 |
| ⚠️ | 已知风险 |
| 🆕 | 本版新增 |
| 📌 | 重要必读 |

---

## 🧪 测试约定

- 不写单元测试（项目是数据管道不是库）
- 端到端 smoke test 跑一遍 + 记录耗时/captcha 次数
- 重大 Skill 写 `test_{purpose}.py` 留作回归

---

## 🗃️ 数据文件命名

```
output/
├── batch-{mvp|full}-{N}kw/        ← Skill 3 批量结果
│   ├── scanner-{keyword}.json     ← Skill 1 输出
│   ├── pain-miner-{keyword}.json  ← Skill 2 输出
│   ├── viral-{keyword}.json       ← 合并
│   └── batch-{date}-{time}-summary.md
├── skill-1.5-viral-analyzer-v{N}/  ← Skill 1.5 输出
│   ├── {note_id}-4问+6维.md
│   ├── {note_id}-cover.png
│   └── {note_id}-benchmark.json
├── skill-4-formula-rewrites-v{N}/  ← Skill 4 输出
│   ├── rewrites/{keyword}.md
│   └── {keyword}-v{N}.md
└── skill-5-obsidian-sync/          ← Skill 5 实际同步日志
```

---

## 🔁 增量更新原则

- **不重写未变更文件**（Skill 5 已有 mtime 对比）
- **不重新跑已跑过的关键词**（pain-miner 缓存 note_id 维度）
- **不重复抓同一网页**（一次落盘，后续引用路径）

---

## 💡 反模式（不要做）

- ❌ 大段输出贴对话（→ 写文件）
- ❌ 反复检查同样状态（→ 用 TodoWrite）
- ❌ Read 验证 Edit 结果（→ Edit 自动报错）
- ❌ 一个对话做完整个大项目（→ 每 Phase 一个对话）
- ❌ 重要决策只讲一遍（→ 写 STATUS/ARCHITECTURE/CONVENTIONS）
- ❌ 把 token 写进 prompt（→ 走 .env）
- ❌ scrapling 不带 cookies 抓 xhs（→ 会重定向到 login）
