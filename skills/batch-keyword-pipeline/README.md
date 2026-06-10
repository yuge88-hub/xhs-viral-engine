# Skill 3: batch-keyword-pipeline (v0.2.0)

**微技能编排器**：把 Skill 1 + Skill 2 串成一条"批量关键词 → 爆款 → 痛点"流水线。

> **🆕 v0.2.0 关键变化**：pain-miner (Skill 2) 升级为默认走 DrissionPage web 抓取，**per-keyword 隔离 + xhs web 限流宽松** = 5 关键词 87 viral notes → 159 痛点，**0 captcha 触发**，2024 秒。

## 角色定位

中央调度器（LLM/手工）调用它，一次跑多个关键词，输出**赛道全景图**（跨关键词的爆款 + 痛点 + 痛点云）。

## Pipeline

```
keywords (CLI / 文件)
  ↓ per keyword:
      scanner.py (Skill 1) → viral notes JSON (含 xsec_token)
  ↓
合并所有 viral notes (with source_keyword tag)
  ↓ per keyword (captcha 隔离):
      pain_miner.py --use-web  (Skill 2 v0.2.0, DrissionPage 抓 .comment-item)
  ↓
输出:
  <prefix>-summary.md  ← Per-keyword 概览 + 痛点云
  <prefix>-viral.md    ← Top N 爆款跨关键词
  <prefix>-pains.md    ← 全部痛点按关键词分组
  <prefix>-raw.json    ← 全部原始数据
```

## 输入

| 参数 | 默认 | 说明 |
|---|---|---|
| `--keywords` | 必填* | 逗号分隔关键词 |
| `--keywords-file` | 必填* | 关键词文件 (一行一个, `#` 开头是注释) |
| `--min-likes` | 500 | 笔记最小点赞 |
| `--pages` | 1 | 每关键词搜索页数 |
| `--full` | False | 完整模式 (取粉丝, 慢, 可能 captcha) |
| `--with-pains` / `--no-pains` | True / False | 是否同时跑 Skill 2 (默认开) |
| `--pain-min-likes` | 5 | 痛点最小点赞 (推荐 3-5) |
| `--pain-top` | 5 | 每笔记 Top N 痛点 |
| `--sleep` | 10 | 每关键词间隔 (秒), 推荐 8-15s 防 captcha |
| `--out-prefix` | `batch-YYYYMMDD-HHMMSS` | 输出文件前缀 |

* 互斥二选一

## 输出位置

```
output/
├── batch-20260609-120000/
│   ├── batch-20260609-120000-summary.md     ← 概览 + 痛点云
│   ├── batch-20260609-120000-viral.md       ← 跨关键词 Top N 爆款
│   ├── batch-20260609-120000-pains.md       ← 全部痛点按关键词分组
│   ├── batch-20260609-120000-raw.json       ← 完整原始数据
│   ├── viral-{keyword}.json × N             ← Skill 1 中间产物 (per-keyword)
│   ├── pain-miner-{keyword}.json × N        ← Skill 2 中间产物 (per-keyword)
│   ├── combined-viral.json                   ← 合并的 viral notes
│   ├── scanner-{keyword}.json × N
│   └── scanner-AI 副业.json 等
└── batch-20260609-120000-summary.md        ← 顶层快捷入口
```

## 调用示例

```powershell
cd "C:\Users\张哥\Downloads\web-clipper-master\skills\batch-keyword-pipeline"

# 5 个关键词 MVP + pain-miner (约 35 分钟, 0 captcha)
python run.py --keywords-file "C:\Users\张哥\Downloads\web-clipper-master\output\keywords-5.txt" --min-likes 500

# 3 个关键词快速试 (~15 分钟)
python run.py --keywords "AI 副业,营养食疗,副业赚钱" --min-likes 1000 --pain-min-likes 3

# 关闭 pain-miner (只要 viral notes, ~70 秒)
python run.py --keywords-file keywords.txt --no-pains

# 完整模式 (取粉丝, 慢, 可能 captcha, 慎用)
python run.py --keywords "AI 副业,副业赚钱" --full --min-likes 5000
```

## 已知限制

| 局限 | 缓解 |
|---|---|
| 顺序跑, 慢 (~30min/5关键词) | 后续可加多进程/多 xhs-cli 实例并行 (但 captcha 风险) |
| 完整模式 captcha 风险 | 默认 MVP 模式, `--full` 慎用 |
| 跨关键词痛点去重 | 痛点云基于词频, 不去重 (同一痛点可能在多个关键词笔记下出现) |
| 子进程调用, 不能共享内存 | 重用已测好的 CLI 接口, 隔离性更好 |
| **xhs captcha 限流** | **v0.2.0 起**: per-keyword 隔离 + pain-miner 走 web 路径, **实测 0 captcha 触发** |

## 后续 Skill 接口契约

输出是 Skill 4 (LLM 重构) 的**完整上下文**：
- 跨关键词的爆款 (找赛道共性)
- 跨关键词的痛点 (找赛道空白)
- 痛点云 (看用户语言习惯)

## 实测结果 (2026-06-09)

| 关键词 | viral notes | 痛点数 |
|---|---|---|
| AI 副业 | 18 | 32 |
| 营养食疗 | 17 | 30 |
| 副业赚钱 | 18 | 23 |
| 减肥 | 16 | 43 |
| 自媒体 | 18 | 31 |
| **合计** | **87** | **159** |

**耗时**: 2024 秒 (~34 分钟) · **captcha 触发**: 0

Top 痛点样本：
- 770 赞 "不是你想象的那么简单" (教程来了)
- 535 赞 "切记，真能赚钱的不会和你说的" (副业)
- 95 赞 "摆摊也有..." (副业实战)
- 66 赞 "做出来的前端确实可以...后端就是假的数据"
- 40 赞 "怎么做，求带"
