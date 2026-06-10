# Skill 2: xhs-comment-pain-miner (v0.2.0)

**微技能**：挖小红书爆款笔记的评论区痛点，输出结构化 JSON / Markdown。

> **🆕 v0.2.0 关键变化**：默认走 **DrissionPage web 抓取**（`.comment-item` DOM），**完全绕开 xhs-cli `comments` API 的 captcha 限流**。xhs web 限流比 API 宽松 10x+，实测 87 viral notes 0 captcha 触发，159 痛点/2024 秒。

## 角色定位

Skill 1 找到"低粉爆款"笔记后，**Skill 2 拉这些笔记的评论区**，识别**真实痛点**（不是表面夸赞），用于：
- 选题（评论里没解决的问题 = 新内容蓝海）
- 内容改进（评论里"看不懂/想要但没拿到" = 内容缺口）
- 产品灵感（评论里"求资源/求链接" = 现成需求）
- LLM 重构（Skill 4 的输入：标题/开头/结构从痛点反推）

## Pipeline

```
Skill 1 results JSON (note_id + title + xsec_token)
  ↓
per note:
  ┌─ 默认 (--use-web=True) ─────────────────────────────────┐
  │  DrissionPage 加载 note URL (带 xsec_token)             │
  │  → DOM 抓 .comment-item / .parent-comment              │
  │  → 提取 content / likes / nickname / ip / is_author    │
  │  → 0 captcha 风险                                      │
  └─────────────────────────────────────────────────────────┘
  ┌─ 兜底 (--use-web=False 或 web 失败) ──────────────────┐
  │  xhs comments <url> --all --json                       │
  │  → 仍可能触发 captcha (xhs-cli 0.8.9 限流严)            │
  └─────────────────────────────────────────────────────────┘
  ↓
规则分类 (pain / question / criticism / request / suggestion / praise / neutral / noise)
  ↓
过滤: 太短 / 作者自己 / 类别白名单
  ↓
按 likes 降序 → Top N per note
  ↓
JSON / Markdown 输出
```

## 输入

| 参数 | 默认 | 说明 |
|---|---|---|
| `--input` | 必填* | Skill 1 输出 JSON / Markdown 路径（**必须含 xsec_token 字段**） |
| `--note-ids` | 必填* | 逗号分隔的 note_id 列表（手动指定, 需配合 xsec 字段） |
| `--min-likes` | 0 | 评论最小点赞（过滤水军） |
| `--min-content-len` | 6 | 评论最小字符数（过滤"沙发" "1" "nb"等） |
| `--top-per-note` | 10 | 每条笔记保留前 N 痛点 |
| `--sleep` | 4.0 | 每条 note 间基础延迟 (秒), web 路径推荐 2-5s |
| `--jitter` | 0.5 | 延迟随机抖动 (±秒) |
| `--max-consecutive-captcha` | 2 | 连续 captcha 多少次自动熔断（避免被封号） |
| `--use-web` | **True** | 🆕 默认走 DrissionPage web 抓取（限流宽松, 推荐） |
| `--no-web` | - | 强制走 xhs-cli API（会触发 captcha, 仅 debug 用） |
| `--categories` | `pain,question,criticism,request,suggestion` | 保留的类别白名单 |
| `--output` | `json` | `json` / `markdown` |
| `--out` | stdout | 落盘路径 |

* 互斥二选一

## 类别标签

| 标签 | 含义 | 例子 |
|---|---|---|
| `pain` | 痛点（没效果/做不来/好难） | "试了3次都失败" "小白求教" |
| `question` | 提问（怎么/如何/是什么） | "怎么把字幕copy下来" "对吗" |
| `criticism` | 质疑/批评 | "纯广告" "割韭菜" "假的" |
| `request` | 求资源/求链接 | "求教程" "在哪买" "链接发一下" |
| `suggestion` | 改进建议 | "BGM 太大" "希望加字幕" |
| `praise` | 赞美/感谢 | "nb" "学习了" "谢谢分享" |
| `neutral` | 不属于上述任何类 | 一般陈述 |
| `noise` | 太短/太长/无意义 | "1" "沙发" 或超长科普摘抄 |

## 输出 Schema

```json
{
  "skill": "xhs-comment-pain-miner",
  "version": "0.2.0",
  "input_notes": 7,
  "filters": {"min_likes": 0, "use_web": true, ...},
  "stats": {"total_comments": 240, "total_kept_pain": 47, "elapsed_sec": 18.3},
  "per_note": [
    {
      "note_id": "69f4c2df000000002301d719",
      "title": "AI拆解副业...",
      "url": "https://...",
      "total_comments": 32,
      "kept_comments": 18,
      "top_pains": [
        {
          "id": "comment-69f72fce000000002803a807",
          "content": "产品需求文档哪来的？外行人怎么搞定？",
          "likes": 11,
          "is_sub": false,
          "is_author": false,
          "nickname": "西元前",
          "ip_location": "江苏",
          "categories": ["pain", "question"]
        }
      ]
    }
  ]
}
```

## 调用示例

```powershell
# 接 Skill 1 输出 (自动用 web 路径)
cd "C:\Users\张哥\Downloads\web-clipper-master\skills\xhs-comment-pain-miner"
python pain_miner.py --input "..\..\output\ai-fuyue-full-v4.json" --output markdown --out "..\..\output\ai-fuyue-pains.md"

# 高赞痛点 (≥5 赞)
python pain_miner.py --input "..\..\output\ai-fuyue-full-v4.json" --min-likes 5 --output json

# 手动指定 (注意: --note-ids 模式没 xsec_token, 自动 fallback 到 API)
python pain_miner.py --note-ids "69f4c2df000000002301d719,6a168b8a000000003501caf4" --output markdown

# 强制走 API (会 captcha, 慎用)
python pain_miner.py --input "..\..\output\ai-fuyue-full-v4.json" --no-web --output json
```

## 已知限制

| 局限 | 缓解 |
|---|---|
| 规则分类不准确（关键词匹配, LLM 更准） | 加 `--categories` 收紧白名单 + Skill 4 让 LLM 二次清洗 |
| 评论区中"作者自己"回复污染信号 | `--exclude-author` 默认开, web 路径识别 `.labels` 含"作者"字样 |
| 部分 note 暂不可访问 (404 "页面不见") | 自动跳过, 不计入结果 |
| 排序仅按点赞 | 后续可加: 账号权重 / IP 地理位置 / 时间衰减 |
| 规则分类 70% 准确率 | Skill 4 LLM 跑一遍可提升到 95% |

## 后续 Skill 接口契约

输出 `top_pains[].content` 是 Skill 4 (LLM 重构) 的**核心输入**：
- 标题重构：从 `pain/criticism` 反馈里抽用户语言习惯
- 开头 hook：从 `question/request` 里提炼"观众最想知道的"
- 内容结构：从 `praise` 关键词反推爆款公式

## 🆕 v0.2.0 关键发现 (Web 路径)

### xhs-cli vs xhs-web 限流差异

| 端点 | 限流严度 | 行为 |
|---|---|---|
| `xhs search` | 宽松 | 87 viral 0 captcha |
| `xhs comments` API | **极严** | 1 次就 captcha, 5-30 min 解 |
| `xhs-cli` `Captcha triggered` WARNING | **误报多** | 实际 JSON `ok:true` 时也别信 |
| `https://www.xiaohongshu.com/explore/<id>` (web) | 宽松 | 87 notes 0 captcha |

### Web 抓取必要条件

- **xsec_token 必传**: URL 必须带 `?xsec_token=...&xsec_source=pc_search`, 否则 404
- **Cookie 必须有效**: web 路径会读 session 校验, expired 的 cookies 直接跳 login
- **DrissionPage 4.1.1.2 `as_expr=True`**: 走 `Runtime.evaluate`, 默认 `Runtime.callFunctionOn` 静默返回 None

### Web 抓取 DOM 选择器

| 元素 | 用途 |
|---|---|
| `.comment-item` | 主评论 (含 `.comment-item-sub` 类标子评论) |
| `.note-text` | 评论内容 |
| `.author a.name` | 用户昵称 |
| `.like` | 点赞数 (textContent 形如 "40\n回复") |
| `.info .date` | 日期 + IP (形如 "2024-06-27重庆") |
| `.labels` (含"作者") | 作者自己评论的标识 |
| `.parent-comment` | 子评论 / 追问 |

## 历史版本

### v0.1.0 (2026-06-09) — 首发

- 走 `xhs-cli comments --all --json` API
- 规则分类 7 类
- 实测 8 笔记 1426 评论 → 40 痛点 (180s)
- **重大缺陷**: xhs-cli 限流严, 完整 batch 跑 1 个关键词就 captcha

### v0.2.0 (2026-06-09) — Web 路径优先 ⭐

- **新加 `run_xhs_web_comments()`**: DrissionPage 抓 `.comment-item` DOM
- **默认走 web** (xhs-cli API 作 fallback)
- 实测 87 viral notes 0 captcha → 159 痛点 (2024s, 5 关键词)
- `--use-web` / `--no-web` flag 控制路径
- 修正: 必须传 xsec_token (从 scanner 的 results[xsec_token] 拿)
