# Skill 1-5 关联图与重复审计 (2026-06-09)

> **作者**: Claude (Phase G 架构审计)  
> **数据源**: 6 个 Skill 的 README + 实跑经验 + 30+ POSTMORTEM 坑  
> **目标**: 找重复 + 提迭代建议 (避免后续每个 Skill 重复造轮子)

---

## 📊 一、Skill 全景速查

| Skill | 名字 | 输入 | 输出 | 耗时 | 触发率 |
|---|---|---|---|---|---|
| **Skill 1** | xhs-trending-scanner | keyword | `viral notes JSON` (含 fans+viral_score+xsec_token) | MVP 1.5s/20条 / 完整 5-8s/作者 | 100% |
| **Skill 1.5** | viral-analyzer | 1 viral note (note_id+xsec_token) | `4问+6维.md` + `analysis.json` + `cover.{png,json}` + `benchmark.json` | ~30s/条 (LLM) + 5s 抓 | 按需 |
| **Skill 2** | xhs-comment-pain-miner | viral notes JSON | `pains.json` (per_note.top_pains[]) | 17s/note (web) | 100% |
| **Skill 3** | batch-keyword-pipeline | keywords[] | 1+2 编排产物 (`combined-viral.json` + `pains*.json` ×N) | 5 关键词 ~34 min | 100% |
| **Skill 4** | viral-rewriter | 1 pain + keyword | `rewrite.md` (含标题公式+骨架) | 5s/条 (含 LLM 30s) | 按需 |
| **Skill 4.5** | reverse-prompt (Skill 1.5 内) | 1 viral note + pain | `reverse-prompt.md` (5 段 prompt 模板) | 30s/条 (LLM) | 复用 |
| **Skill 5** | obsidian-sync | 全产物 | Obsidian vault (YAML+wikilinks) | 10-30s 增量 | 100% |

**辅助脚本**:
- `quality_scorer.py` (Skill 1 输出加分层 💎/🔥/⚡/📊)
- `account_analyzer.py` (聚合 viral_score 做账号画像)
- `topic_generator.py` (聚合 pain 跨关键词做选题库)

---

## 🔄 二、数据流图 (核心链路)

```
                [用户输入: keyword]
                        ↓
        ┌───────────────────────────────────┐
        │ Skill 1: xhs-trending-scanner     │
        │  xhs search → note_id+title+likes │
        │  DrissionPage 抓 user profile     │
        │  → fans + viral_score             │
        └───────────────────────────────────┘
                        ↓
              scanner-full.json (results[] 按 viral_score 排序)
                        ↓
        ┌──────────────┴──────────────┐
        ↓                             ↓
┌────────────────────┐   ┌────────────────────────┐
│ Skill 3: batch     │   │ Skill 1.5: viral-      │
│ (per-keyword 编排)  │   │ analyzer (per-note 4问  │
│                    │   │ +6维+cover+benchmark)   │
└────────────────────┘   └────────────────────────┘
        ↓                             ↓
combined-viral.json            {note_id}-4问+6维.md
pains-{kw}.json × N            {note_id}-cover.png
                               {note_id}-benchmark.json
        ↓                             ↓
        └──────────────┬──────────────┘
                       ↓
        ┌──────────────────────────────────┐
        │ Skill 2: xhs-comment-pain-miner  │
        │  DrissionPage 抓 .comment-item   │
        │  分类 pain/question/criticism... │
        └──────────────────────────────────┘
                       ↓
              pains.json (per_note[].top_pains[])
                       ↓
        ┌──────────────┴──────────────┐
        ↓                             ↓
┌────────────────────┐   ┌────────────────────────┐
│ Skill 4: rewriter  │   │ 用户/手工选题           │
│ (input: pain +     │   │ (看 v2/v3 报告)        │
│  Skill 1.5 4问+6维)│   │                        │
└────────────────────┘   └────────────────────────┘
        ↓                             ↓
{keyword}-rewrite.md          跳 v2/v3 报告
{note_id}-reverse-prompt.md   (决策: 写哪条)
                       ↓
        ┌──────────────────────────────────┐
        │ Skill 5: obsidian-sync            │
        │  扫 1+2+3+4 产物 → vault          │
        │  YAML + wikilinks + 增量同步      │
        └──────────────────────────────────┘
                       ↓
              Obsidian vault
        (00-index + 01-raw + 02-formula + 03-rewrites)
```

---

## 🔁 三、重复点审计 (15 处)

### P0 (高优先级, 立即做)

| # | 重复点 | 现状 | 影响 | 建议 |
|---|---|---|---|---|
| **1** | **LLM 调用分散** | 4 处 DeepSeek 调用,各自读 env+retry+错误处理 (`viral_analyzer` / `cover_analyzer` / `benchmark_check` / `reverse_prompt`) | 改 LLM 客户端要改 4 处 / 错误处理不一致 | **抽 `skills/_bootstrap/llm_client.py`** 统一 retry+错误+env |
| **2** | **cookies 加载分散** | 3 处读 `~/.xiaohongshu-cli/cookies.json`, 3 种格式解析 (Chrome / xhs-cli 扁平 / xhs-cli 嵌套) | 改 cookies 格式要改 3 处 / 字段名不统一 | **抽 `skills/_bootstrap/cookies_loader.py`** 统一 |
| **3** | **fans 字段缺失** | Skill 1.5 `viral_analyzer` 抓 note 时 `meta.fans=null`, benchmark 评分 "粉丝数未抓到" | 4 条 Top 5 benchmark 总评锁 0.5, 必须重跑 | **Skill 1.5 接 Skill 1 完整模式输出** (带 fans), 或 scanner 给 viral_analyzer 传 author.fans |

### P1 (中优先级, 下次迭代做)

| # | 重复点 | 现状 | 影响 | 建议 |
|---|---|---|---|---|
| **4** | **viral_score 公式重复** | `scanner.py` + `account_analyzer.py` 各自算 `likes/(fans+1)` | 改公式要改 2 处 | 抽 `skills/_common/viral_score.py` |
| **5** | **报告模板重复** | `write_intel_report.py` v1 / v2 / v3 三套 header+table 函数 | 加新维度要改 3 处 | 抽 `_bootstrap/report_template.py` (header/footer/章节函数) |
| **6** | **同一 note 抓多次** | 1 条 note 被抓 3 次: profile (Skill 1) / note HTML (Skill 1.5) / comments (Skill 2) | 慢 + captcha 风险 3x | 加缓存 `_bootstrap/cache.py` key=note_id+type, TTL=24h |
| **7** | **多种 rewriter 入口** | `rewriter.py` (v0.3) + `reverse_prompt.py` (Skill 4) + `auto_fill.py` (Skill 4) | 3 个入口 + 用户搞不清区别 | 合并到 Skill 4 单一入口, subcommand 区分 |
| **8** | **多种 mode flag** | MVP/完整/auto-fill/--use-web/--skip-llm 多套 | 用户记不清 flag | 统一 `--mode {fast,default,full}` |

### P2 (低优先级, 有空做)

| # | 重复点 | 现状 | 影响 | 建议 |
|---|---|---|---|---|
| **9** | **JSON 序列化不统一** | `ensure_ascii=False` / `True` / `indent=2` 散落 | 偶尔中文乱码 | 抽 `_bootstrap/json_io.py` |
| **10** | **schema 不统一** | 多种 `results[]` / `per_note[]` / `4_questions` 数组 | 跨 Skill 解析容易出错 | 抽 `_bootstrap/schemas.py` (pydantic) |
| **11** | **错误处理分散** | try/except 不一, captcha 处理只在 Skill 2 | 重试逻辑散落 | 抽 `_bootstrap/errors.py` |
| **12** | **报告产物路径混乱** | `output/ai-children-illustration/` / `output/children-height/` / `output/ai-knowledge-base/` 各起一名 | 用户找产物要记 3 套路径 | 统一 `output/{kw}-{date}-{report-type}.md` 或 `output/{kw}/v{1,2,3}-{date}.md` |

### P3 (可选, 长期优化)

| # | 重复点 | 现状 | 影响 | 建议 |
|---|---|---|---|---|
| **13** | **分类标签分散** | 7 套 (4问+6维/痛点/trigger/...) | 标签命名不一致 | 抽 `_bootstrap/labels.py` enum |
| **14** | **时间字段命名不一** | `publish_time` / `age_days` / `date` / `create_time` | 跨 Skill 难聚合 | 抽 `_bootstrap/time_utils.py` |
| **15** | **三方依赖版本号** | xhs-cli/DrissionPage/scrapling 各自 version 字段 | 升级要逐个查 | 抽 `_bootstrap/deps.py` 集中检查 |

---

## 🔗 四、关键链路实跑验证 (Phase F 完整闭环)

**链路**: Skill 1 (完整) → Skill 1.5 (LLM 4问+6维) → Skill 2 (web pain) → 3.0 报告

**实跑产物 (儿童身高 13 条 Top 5)**:
- Skill 1: `scanner-full.json` 30 作者 / 13 真素人爆款 (5 min)
- Skill 1.5 × 5: `4问+6维.md` + `analysis.json` + `cover.png/json` + `benchmark.json` (3 min)
- Skill 2 × 5: `pains.json` 每条 1-3 痛点 (1.5 min)
- 3.0 报告: 15,758 字符 / 412 行 (1 sec)

**端到端耗时**: ~10 min (5 条)  
**总成本**: ~¥0.02 (DeepSeek 4问+6维 + reverse_prompt)

**链路问题** (本审计发现):
- 3 处需要 "fans" 字段, 但 Skill 1.5 不带 — **P0-3 必须修**
- 报告模板 3 套共存 — **P1-5 必须迭代**

---

## 📋 五、迭代路线图

### 阶段 A: 抽 _bootstrap (本周末)
1. **llm_client.py** — 4 处 LLM 统一 (P0-1)
2. **cookies_loader.py** — 3 处 cookies 统一 (P0-2)
3. **fans 注入** — Skill 1.5 接 Skill 1 输出 (P0-3)

### 阶段 B: 抽 _common (下周)
4. **viral_score.py** — 公式统一 (P1-4)
5. **report_template.py** — 报告模板 (P1-5)
6. **cache.py** — 抓取缓存 (P1-6)
7. **合并 rewriter 入口** (P1-7)

### 阶段 C: 优化 (有空)
8. 统一 mode flag (P1-8)
9. json_io / schemas / errors (P2-9/10/11)
10. 报告路径统一 (P2-12)

### 阶段 D: 长期 (看需求)
11. labels enum (P3-13)
12. time_utils (P3-14)
13. deps.py (P3-15)

---

## 🎯 六、对外接口契约 (下游脚本要遵守)

### Skill 1 输出契约 (下游 2/3 必读)
```json
{
  "results": [
    {
      "note_id": "24hex",  // 必填
      "xsec_token": "AB...",  // 必填 (POSTMORTEM #8)
      "title": "...",
      "url": "https://www.xiaohongshu.com/explore/{note_id}?xsec_token=...",
      "author": {"user_id": "24hex", "nickname": "...", "fans": 50},
      "metrics": {"likes": 3964, "collects": 469, "comments": 854, "shares": 461},
      "publish_time": "04-20",
      "viral_score": 77.73
    }
  ]
}
```

### Skill 2 输出契约 (下游 4 必读)
```json
{
  "per_note": [
    {
      "note_id": "24hex",
      "title": "...",
      "url": "...",
      "total_comments": 20,
      "kept_comments": 3,
      "top_pains": [
        {"id": "comment-...", "content": "...", "likes": 291, "is_sub": false, "is_author": false, "nickname": "...", "ip_location": "...", "categories": ["pain"]}
      ]
    }
  ]
}
```

### Skill 1.5 输出契约 (下游 4 + 报告必读)
```json
{
  "meta": {"note_id": "24hex", "title": "...", "author": "...", "fans": null, "likes": 3964, "collects": 469, "comments": 854, "publish_date": "2026-04-20", "body": "..."},
  "4_questions": {"who": {"label": "...", "content": "..."}, "why_click": {...}, "how_flow": {...}, "where_lead": {...}},
  "6_dimensions": {"role_dna": "...", "reader_profile": "...", "content_structure": "...", "language_style": "...", "constraint_rules": "...", "workflow_logic": "..."},
  "summary": "...",
  "raw_llm_output": "..."
}
```

---

## 🚦 七、风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| **抽 _bootstrap 改了 import 链, 6 个 Skill 全坏** | 中 | 高 | 每次抽一个 + 跑一遍实跑 (Skill 1+1.5+2+4 smoke test) |
| **统一 schema 改了字段, 旧产物不兼容** | 中 | 中 | 留 `legacy_v1` 兼容层, 新 schema 用 `_v2` 后缀 |
| **缓存层 captcha 误判** | 低 | 高 | TTL 24h, 用户可 `--no-cache` 强制重抓 |
| **报告路径统一改了, Obsidian 同步断链** | 中 | 中 | Skill 5 加 `--legacy-path` 兼容 |
| **抽 3 个 bootstrap 后 4 个 LLM 调用有 race condition** | 低 | 中 | 单例 + threading.Lock |

---

## 📝 八、覆盖完整度

- ✅ 6 个 Skill README 全部读完
- ✅ 数据流图 1 张 (核心链路)
- ✅ 重复点 15 条 (按 P0/P1/P2/P3 分级)
- ✅ 迭代路线图 4 阶段
- ✅ 输出契约 3 套 (下游必读)
- ✅ 风险表 5 条

**建议下一步**: 
- A: 立即开干 P0 (3 项, ~1-2 天, 解决 Skill 1.5 fans 缺失 + LLM/cookies 统一)
- B: 先观望 (本审计留作 v3 报告附录, 等下次批量跑再迭代)
- C: 用户决策后再做

---

_本报告由 Claude 写于 2026-06-09 22:30. 数据截至 Phase F 完整闭环完成._
_触发: 用户问 "Skill 1-5 怎么关联, 有没有重复需要迭代的"._
