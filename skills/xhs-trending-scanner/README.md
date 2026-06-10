# Skill 1: xhs-trending-scanner

**微技能**：找出"低粉爆款"笔记——作者粉丝 < 3000 且笔记点赞 > 1000。

## 角色定位

属于"小红书全栈爆款笔记自动化引擎"的 **Skill 1**（爆款筛选引擎）。下游 Skill 会基于它的输出做评论痛点挖掘 / Obsidian 同步 / LLM 内容重构。

## 输入

| 参数 | 默认 | 说明 |
|---|---|---|
| `keyword` (positional) | 必填 | 行业关键词，如 `"AI 副业"`、`"营养食疗"` |
| `--max-followers` | 3000 | 作者粉丝上限（仅完整模式） |
| `--min-likes` | 1000 | 笔记点赞下限（硬过滤） |
| `--sort` | `popular` | `general / popular / latest` |
| `--pages` | 1 | 拉取多少页搜索结果（每页 ~20 条） |
| `--require-fans` | False | True=完整模式(取粉丝卡硬过滤), False=MVP(按 likes 排序) |
| `--fan-source` | `auto` | `auto / api / playwright / drissionpage` (仅完整模式有效) |
| `--output` | `json` | `json` / `markdown` |
| `--out` | stdout | 落盘路径 |

## 输出 Schema

```json
{
  "skill": "xhs-trending-scanner",
  "version": "0.1.0",
  "keyword": "AI 副业",
  "filter": {"max_followers": 3000, "min_likes": 1000},
  "scanned_notes": 23,
  "unique_authors": 18,
  "fetched_fans": 17,
  "viral_count": 4,
  "results": [
    {
      "note_id": "6a103783000000003502b5d1",
      "title": "全网首发！AI动态漫制作全流程！",
      "url": "https://www.xiaohongshu.com/explore/6a103783000000003502b5d1",
      "author": {
        "user_id": "684f7776000000001e03fbdc",
        "nickname": "素愫敲腻害",
        "fans": 287,
        "red_id": "xhs-pc-web"
      },
      "metrics": {
        "likes": 32612,
        "collects": 38633,
        "comments": 5708,
        "shares": 3781
      },
      "publish_time": "05-25",
      "viral_score": 113.7
    }
  ]
}
```

`viral_score = likes / (fans + 1)`，越高越"低粉爆款"。

## Pipeline

```
[1] xhs search <kw> --json --sort popular --page 1..N
        ↓
    note_id, title, user_id, nickname, likes, collects, comments, xsec_token
        ↓
[2] pre-filter: likes >= min_likes
        ↓
[3] dedupe by user_id → unique_authors[]
        ↓
[4] fetch fans(user_id):
        try: GET /api/sns/web/v1/user/otherinfo?target_user_id=…
        except: playwright → https://www.xiaohongshu.com/user/profile/{uid}
        on failure: skip (mark fans=null)
        ↓
[5] final filter: fans < max_followers
        ↓
[6] emit results sorted by viral_score desc
```

## 依赖

- `xhs-cli-headless >= 0.8.9`（`xhs search --json`）
- `python >= 3.10`（用 `dict | dict`, type hints）
- `playwright` + chromium（仅 fans 取不到时启用）
- Cookie 来自 xhs-cli-headless 的 `~/.xiaohongshu-cli/cookies.json`

## 调用示例

```bash
# MVP 模式（默认，推荐起步用，~1.6s 跑 20 条）
python scanner.py "AI 副业" --min-likes 500 --output json

# 完整模式（取粉丝卡硬过滤，~5-8s/作者，敏感时触发 xhs 验证码）
python scanner.py "AI 副业" --require-fans --max-followers 3000 --min-likes 1000 --fan-source drissionpage

# markdown 落盘（给 Obsidian 用）
python scanner.py "AI 副业" --output markdown --out ./obsidian/inbox/xhs-viral-$(date +%F).md
```

## 已知限制 & 关键坑

| 坑 | 缓解 |
|---|---|
| xhs **session 级 captcha**（verifyType=216）会在高频抓取时触发 | MVP 模式只查搜索 API，**不会**触发；完整模式用浏览器才能过 |
| xhs-cli-headless `search-user.fans_total` 总是返回 0 | xhs 反爬，搜索路径不返回真值。**别用** |
| xhs web `user/otherinfo` API 直接调用 → 500 (`jarvis-gateway-default`) | 必须走浏览器（DrissionPage/Playwright），带 cookie + xsec_token |
| xhs 直访 user profile URL 会被反爬重定向到 search/explore | 必须先 warmup xhs 首页，再搜昵称→点链接进入 profile |
| 大量 Chrome 僵尸进程会占端口 9222 | 跑前先 `Get-Process chrome \| Stop-Process -Force` |

## 模式对比

| 维度 | MVP (默认) | 完整 (--require-fans) |
|---|---|---|
| 数据源 | `xhs search --json` | + DrissionPage/Playwright 抓 user profile |
| 字段 | likes, collects, comments, shares, title, url, author_id, nickname | + fans, fan_source, profile_url |
| 过滤 | likes >= min_likes | likes >= min_likes **且** fans < max_followers |
| 排序 | likes desc | viral_score = likes/(fans+1) desc |
| 速度 | ~1.5s / 20 条 | ~5-8s / 作者 |
| 触发 captcha | ❌ 否 | ⚠ 可能 (共享 session) |
| 推荐场景 | 日常扫描、批量分析 | 精挑"低粉爆款" |

## 后续 Skill 接口契约（本 skill 提供）

- 输出一份 `viral_count >= 1` 的 JSON / markdown，可直接喂给 Skill 2（评论区痛点挖掘）
- 每条 result 含 `note_id + url + author.user_id`，下游可直接用 `xhs comments <note_id> --json` 拉评论
