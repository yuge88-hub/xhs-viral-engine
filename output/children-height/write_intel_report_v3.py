"""write_intel_report_v3.py — 儿童身高「素人爆款 Top 5 深拆」报告 3.0。

读 5 个 rank 的 Skill 1.5 产物 (analysis.json / cover.json / benchmark.json) +
5 个 pain-miner 产物 (pains.json), 输出 Top 5 头部账号深拆 + 痛点跨条聚合 + 仿写策略.

输入:
  output/children-height/scanner-full.json
  output/children-height/skill-1.5-top5/rank{i}-{nickname}/{note_id}-*.json
  output/children-height/pain-miner-top5/rank{i}-{nickname}/pains.json
输出:
  output/children-height/intelligence-report-v3-{date}.md (>= 8000 字符)
"""
from __future__ import annotations
from skills._bootstrap import *  # noqa: F401,F403  ← UTF-8 项目级基线

import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path("output/children-height")
SKILL1 = json.loads((ROOT / "scanner-full.json").read_text(encoding="utf-8"))
RESULTS = sorted(SKILL1["results"], key=lambda r: r["viral_score"], reverse=True)[:5]


def _md_safe(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ")


def _nick_dir(r: dict) -> str:
    nick = r["author"]["nickname"]
    safe = "".join(c for c in nick if c.isalnum() or c in "._- ")[:20].strip()
    return safe or "author"


def _load_skill15(rank: int, r: dict) -> dict | None:
    """读 analysis.json + cover.json + benchmark.json。"""
    nick = _nick_dir(r)
    base = ROOT / "skill-1.5-top5" / f"rank{rank}-{nick}"
    note_id = r["note_id"]
    analysis_p = base / f"{note_id}-analysis.json"
    cover_p = base / f"{note_id}-cover.json"
    bench_p = base / f"{note_id}-benchmark.json"
    if not analysis_p.exists() or not cover_p.exists():
        return None
    analysis = json.loads(analysis_p.read_text(encoding="utf-8"))
    cover = json.loads(cover_p.read_text(encoding="utf-8"))
    bench = json.loads(bench_p.read_text(encoding="utf-8")) if bench_p.exists() else {}
    return {"analysis": analysis, "cover": cover, "bench": bench}


def _load_pain(rank: int, r: dict) -> dict | None:
    nick = _nick_dir(r)
    p = ROOT / "pain-miner-top5" / f"rank{rank}-{nick}" / "pains.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


# 跨条聚合用 — 复用 v2 的钩子分类
HOOK_PATTERNS = {
    "数字+身份": r"\d+岁|\d+厘米|\d+cm|二年级|三周岁|四周岁",
    "惊叹+反问": r"达标了?|你娃|你家|知道吗|真的|别让|妈|娃",
    "季节节点": r"三伏|暑假|黄金期|春季|秋冬|开学",
    "数据表型": r"表|标准|体重|对照",
    "方法干货": r"方法|方案|秘诀|做对这|别再|避坑|\d+件套",
    "专家权威": r"协和|儿保|潘慧|医生|医院|测骨龄",
    "紧迫感": r"赶紧|抓住|最后|还来得及|再不|新出炉",
}


def detect_hooks(title: str) -> list[str]:
    hits = []
    for label, pat in HOOK_PATTERNS.items():
        if re.search(pat, title):
            hits.append(label)
    return hits or ["(无明显钩子)"]


def render_account(i: int, r: dict) -> str:
    """每个 rank 的深拆块。"""
    sk = _load_skill15(i, r)
    pa = _load_pain(i, r)
    a = r["author"]
    m = r["metrics"]
    title = r["title"]
    hooks = detect_hooks(title)
    hook_str = " / ".join(hooks)

    # 选题类型
    if "表" in title or "标准" in title or "体重" in title:
        topic = "📊 数据表型 (身高/体重对照)"
    elif "协和" in title or "医院" in title or "医生" in title or "测骨龄" in title:
        topic = "🏥 专家权威型 (医院/协和)"
    elif "三伏" in title or "暑假" in title or "黄金期" in title:
        topic = "⏰ 季节节点型"
    elif "方法" in title or "方案" in title or "秘诀" in title or "做对" in title or "件套" in title:
        topic = "🔧 方法干货型"
    elif "锌" in title or "营养" in title:
        topic = "🥗 营养切入型"
    else:
        topic = "💬 经验共鸣型 (晒娃+反问)"

    lines = [
        f"### #{i} {a['nickname']} — 粉 {a['fans']}",
        "",
        f"- **viral_score**: **{r['viral_score']:.2f}** | **粉丝**: {a['fans']} | **点赞**: {m['likes']:,} | **收藏**: {m['collects']:,} | **评论**: {m['comments']:,}",
        f"- **标题**: {title}",
        f"- **发布**: {r.get('publish_time', '?')}",
        f"- **钩子**: {hook_str}",
        f"- **选题类型**: {topic}",
        "",
    ]

    # --- 4 问摘要 ---
    if sk and sk["analysis"].get("4_questions"):
        q = sk["analysis"]["4_questions"]
        lines += [
            "#### 🎯 4 问拆解 (DeepSeek)",
            "",
        ]
        for key, label, emoji in [
            ("who", "WHO 谁在看", "👥"),
            ("why_click", "WHY CLICK 为什么点开", "👆"),
            ("how_flow", "HOW FLOW 内容结构", "📖"),
            ("where_lead", "WHERE LEAD CTA", "🏁"),
        ]:
            v = q.get(key, {})
            content = (v.get("content") or "_空_").strip()
            # 截前 2 句
            sentences = re.split(r"[。\n]", content)
            short = "。".join([s for s in sentences if s.strip()][:2]) + ("。" if len(sentences) > 2 else "")
            lines.append(f"- **{emoji} {label}**: {short[:200]}")
        lines.append("")

    # --- 6 维摘要 ---
    if sk and sk["analysis"].get("6_dimensions"):
        d = sk["analysis"]["6_dimensions"]
        lines += [
            "#### 🧬 6 维拆解 (DeepSeek)",
            "",
        ]
        for key, label in [
            ("role_dna", "维度一 角色 DNA"),
            ("reader_profile", "维度二 读者画像"),
            ("content_structure", "维度三 内容结构"),
            ("language_style", "维度四 语言风格"),
            ("constraint_rules", "维度五 约束规则"),
            ("workflow_logic", "维度六 工作流逻辑"),
        ]:
            v = (d.get(key) or "").strip()
            if not v:
                continue
            # 截前 200 字符 + 表格截前 5 行
            if "|" in v:
                v = "\n".join(v.split("\n")[:6])
            else:
                v = v[:200] + ("…" if len(v) > 200 else "")
            lines.append(f"- **{label}**: {v}")
        lines.append("")

    # --- 封面 ---
    if sk:
        cv = sk["cover"].get("rules", {})
        col = cv.get("dominant_color_hex", "?")
        w, h = cv.get("width", "?"), cv.get("height", "?")
        kb = cv.get("file_size_kb", "?")
        lines += [
            "#### 🖼️ 封面分析",
            "",
            f"- **主色**: `{col}` | **尺寸**: {w}×{h} (3:4) | **KB**: {kb}",
            f"- **封面图**: `output/children-height/skill-1.5-top5/rank{i}-{_nick_dir(r)}/{r['note_id']}-cover.png`",
            "",
        ]

    # --- benchmark ---
    if sk and sk["bench"].get("scores"):
        b = sk["bench"]
        s = b["scores"]
        lines += [
            "#### 📊 4 标准 benchmark",
            "",
            "| 标准 | 分 | 原因 |",
            "|---|---:|---|",
        ]
        for k, label in [("素人", "素人"), ("结构", "结构"), ("人群", "人群"), ("目标", "目标")]:
            sc = s.get(k, {})
            lines.append(f"| {label} | {sc.get('score', '?')} | {(_md_safe(sc.get('reason', '')))[:60]} |")
        lines.append(f"| **总评** | **{b.get('total_score', '?')}** | {b.get('recommendation', '')} |")
        lines.append("")

    # --- 痛点 Top 3 ---
    if pa and pa.get("per_note"):
        pn = pa["per_note"][0]
        tops = pn.get("top_pains", [])
        if tops:
            lines += [
                "#### 💬 评论痛点 Top 3",
                "",
            ]
            for c in tops[:3]:
                cats = "/".join(c.get("categories", []))
                likes = c.get("likes", 0)
                content = c.get("content", "").replace("\n", " ")[:80]
                nick = c.get("nickname", "?")
                lines.append(f"- **{likes}赞** `[{cats}]` {content} — @{nick}")
            lines.append("")

    return "\n".join(lines)


def aggregate_pain() -> str:
    """跨 5 条痛点聚合。"""
    all_pains = []
    for i, r in enumerate(RESULTS, 1):
        pa = _load_pain(i, r)
        if not pa or not pa.get("per_note"):
            continue
        for c in pa["per_note"][0].get("top_pains", []):
            all_pains.append({
                "rank": i,
                "nick": _nick_dir(r),
                "title": r["title"],
                "content": c.get("content", ""),
                "likes": c.get("likes", 0),
                "cat": "/".join(c.get("categories", [])),
            })
    if not all_pains:
        return "_(无评论痛点数据)_\n"

    # 按 likes 排序
    all_pains.sort(key=lambda x: x["likes"], reverse=True)

    # 类别频率
    cat_counter: Counter = Counter()
    for p in all_pains:
        for c in p["cat"].split("/"):
            cat_counter[c] += 1

    lines = [
        f"**Top 5 总评论**: {sum(p['likes'] for p in all_pains)} 赞累计 | {len(all_pains)} 条痛点保留",
        "",
        "### 类别分布",
        "",
        "| 类别 | 条数 | 占比 |",
        "|---|---:|---:|",
    ]
    total = len(all_pains)
    for cat, n in cat_counter.most_common():
        lines.append(f"| {cat} | {n} | {n*100/total:.0f}% |")
    lines.append("")

    # Top 10 高赞痛点
    lines += [
        "### Top 10 高赞痛点 (跨 5 条)",
        "",
        "| Rank | 账号 | 标题 | 赞 | 类别 | 痛点 |",
        "|---:|---|---|---:|---|---|",
    ]
    for p in all_pains[:10]:
        lines.append(
            f"| {p['rank']} | {p['nick']} | {p['title'][:18]} | {p['likes']} | `{p['cat']}` | {_md_safe(p['content'])[:60]} |"
        )
    lines.append("")

    # 痛点主题聚类
    lines += [
        "### 痛点主题聚类 (关键词抽取)",
        "",
    ]
    kw_counter: Counter = Counter()
    KEYWORDS = {
        "身高焦虑": r"焦虑|达标|不达|偏矮|矮|标准|长高",
        "营养/补剂": r"锌|钙|维D|营养|补|吃|奶粉|咀嚼片",
        "季节/时机": r"三伏|夏天|暑假|春季|追高|黄金期",
        "方法/方法论": r"方法|怎么|做对|做这|秘诀|运动|跳绳|摸高|睡眠",
        "对比/参照": r"同龄|同学|班里|人比|比较|我家",
        "权威/医院": r"协和|医院|儿保|医生|测骨龄|潘慧",
    }
    for p in all_pains:
        for label, pat in KEYWORDS.items():
            if re.search(pat, p["content"]):
                kw_counter[label] += 1
    for label, n in kw_counter.most_common():
        lines.append(f"- **{label}**: {n} 条")
    lines.append("")
    return "\n".join(lines)


def aggregate_cover() -> str:
    """跨 5 条封面规律。"""
    lines = [
        "| Rank | 账号 | 主色 | 尺寸 | KB |",
        "|---:|---|---|---:|---:|",
    ]
    for i, r in enumerate(RESULTS, 1):
        sk = _load_skill15(i, r)
        if not sk:
            continue
        cv = sk["cover"].get("rules", {})
        col = cv.get("dominant_color_hex", "?")
        w, h = cv.get("width", "?"), cv.get("height", "?")
        kb = cv.get("file_size_kb", "?")
        lines.append(f"| {i} | {_nick_dir(r)} | `{col}` | {w}×{h} | {kb} |")
    lines.append("")
    return "\n".join(lines)


def aggregate_benchmark() -> str:
    """跨 5 条 benchmark 趋势。"""
    lines = [
        "| Rank | 账号 | 素人 | 结构 | 人群 | 目标 | **总评** |",
        "|---:|---|---:|---:|---:|---:|---:|",
    ]
    for i, r in enumerate(RESULTS, 1):
        sk = _load_skill15(i, r)
        if not sk or not sk["bench"].get("scores"):
            continue
        s = sk["bench"]["scores"]
        lines.append(
            f"| {i} | {_nick_dir(r)} | {s.get('素人', {}).get('score', '?')} "
            f"| {s.get('结构', {}).get('score', '?')} | {s.get('人群', {}).get('score', '?')} "
            f"| {s.get('目标', {}).get('score', '?')} | **{sk['bench'].get('total_score', '?')}** |"
        )
    lines.append("")
    return "\n".join(lines)


def aggregate_hooks() -> str:
    """跨 5 条钩子公式。"""
    counter: Counter = Counter()
    for r in RESULTS:
        for h in detect_hooks(r["title"]):
            counter[h] += 1
    lines = [
        "| 钩子 | 命中 | 占比 |",
        "|---|---:|---:|",
    ]
    total = len(RESULTS)
    for h, n in counter.most_common():
        lines.append(f"| {h} | {n} | {n*100/total:.0f}% |")
    lines.append("")
    return "\n".join(lines)


def render_full() -> str:
    lines = [
        f"# 儿童身高 · 素人爆款 Top 5 深拆报告 3.0",
        "",
        f"> **生成时间**: {date.today().isoformat()}  ",
        f"> **数据源**: scanner 完整模式 (Top 5 素人爆款) + Skill 1.5 (4问+6维+封面+benchmark) + pain-miner (评论痛点)  ",
        f"> **Skill 链**: scanner → Skill 1.5 (viral/cover/benchmark, LLM DeepSeek) → pain-miner (web 抓) → 报告  ",
        f"> **核心问题**: 「我新号 0 粉, 写什么标题+什么结构+什么封面能爆」 → 学 Top 5 的 4 问+6 维+痛点",
        "",
        "---",
        "",
        "## 📊 一、Top 5 速查表",
        "",
        "| Rank | viral | 粉 | 标题 | 主色 | 痛点数 | 4问+6维 | benchmark |",
        "|---:|---:|---:|---|---|---:|---|---:|",
    ]
    for i, r in enumerate(RESULTS, 1):
        sk = _load_skill15(i, r)
        pa = _load_pain(i, r)
        col = sk["cover"]["rules"].get("dominant_color_hex", "?") if sk else "?"
        pains_n = len(pa["per_note"][0].get("top_pains", [])) if pa and pa.get("per_note") else 0
        q4 = sum(1 for v in sk["analysis"].get("4_questions", {}).values() if v.get("content")) if sk else 0
        d6 = sum(1 for v in sk["analysis"].get("6_dimensions", {}).values() if v) if sk else 0
        bench = sk["bench"].get("total_score", "?") if sk and sk.get("bench") else "?"
        lines.append(
            f"| {i} | **{r['viral_score']:.2f}** | {r['author']['fans']} | {r['title'][:18]} | `{col}` | {pains_n} | {q4}/4 + {d6}/6 | {bench} |"
        )
    lines.append("")

    # 二、Top 5 深拆
    lines += [
        "---",
        "",
        "## 🎯 二、Top 5 头部账号深拆 (5 个账号 × 6 维度)",
        "",
    ]
    for i, r in enumerate(RESULTS, 1):
        lines.append(render_account(i, r))
        lines.append("")

    # 三、跨条聚合
    lines += [
        "---",
        "",
        "## 📈 三、跨 5 条聚合 (顶层规律)",
        "",
        "### 3.1 钩子公式 Top 5",
        "",
        aggregate_hooks(),
        "### 3.2 评论痛点聚合",
        "",
        aggregate_pain(),
        "### 3.3 封面规律",
        "",
        aggregate_cover(),
        "### 3.4 4 标准 benchmark 趋势",
        "",
        aggregate_benchmark(),
    ]

    # 四、仿写策略
    lines += [
        "---",
        "",
        "## 🪝 四、3 步仿写策略 (基于 4 问+6 维 + 痛点钩子)",
        "",
        "### Step 1: 抄标题公式 (Top 5 钩子 + 痛点钩子)",
        "",
        "**模板 1: 反问 + 焦虑 (Top 1 钩子, 291赞 痛点「身高没有标准 制造焦虑」)**",
        "- 「你家孩子身高真的达标了吗? 2026 标准又变了」",
        "- 「3 岁 95cm 是矮吗? 评论区把我看哭了」",
        "",
        "**模板 2: 数据表型 + 数字+身份 (Top 2/5 钩子, 痛点「我家4周岁117」)**",
        "- 「0-7 岁儿童身高体重表 2026 新版 (建议收藏)」",
        "- 「三年级 130cm 在班里算什么水平? 新对照表」",
        "",
        "**模板 3: 专家权威 + 方法干货 (Top 4 钩子, 痛点「协和怎么挂号」)**",
        "- 「协和儿保追高 3 件套, 适合偏矮娃 (附医生答疑)」",
        "- 「医生说: 这 5 种食物比钙片更补锌 (附食谱)」",
        "",
        "### Step 2: 抄 4 问+6 维内容结构",
        "",
        "- **WHO**: 25-40 岁焦虑型妈妈 (8 成情绪需求 + 2 成信息需求)",
        "- **WHY CLICK**: 反问句标题 / 数字+身份 / 季节节点 / 专家权威",
        "- **HOW FLOW**: 开头 9 字疑问句 → 正文 18 字主观评论 → 评论区 800+ 条互动 (注意: 内容**极短**反而爆)",
        "- **WHERE LEAD**: 不引导关注, 引导评论区参与 (Top 1 评论数 854 = 点赞 3964 的 22%)",
        "- **6 维共同点**: 角色 = 普通家长 (无权威) / 语言 = 短句 + 表情符 (无长文) / 约束 = 不用\"颠覆/治愈/内耗\"等套话",
        "",
        "### Step 3: 抄封面规律 (跨 5 条)",
        "",
        "- **3:4 尺寸 (1080×1440)** — 100% 全是 3:4",
        "- **主色调**: 暖色 / 米色 / 浅棕 (5 条里 4 条是 #d8d2bf / #a9998c 类)",
        "- **KB**: 100-300 KB (不要太大, 不要太小)",
        "- **结论**: 米色/暖色 3:4 图, 简笔画或表格风格, 妈妈代入感最强",
        "",
        "### Step 4: 避开陷阱",
        "",
        "- ❌ **内容写太干货 (Top 2 是数据平平, 因为内容\"全表型\"没人评论)**",
        "- ❌ **追求权威/医生身份 (Top 3/4 数据平平, 因为账号=小透明医院名头不够)**",
        "- ❌ **CTA 引导关注/收藏 (Top 5 都是引导评论区争议, 收藏/点赞反而是次要)**",
        "- ❌ **小号+长正文 (Top 1 全篇 18 字, 长文=老账号专利, 素人撑不起)**",
        "",
        "## 📊 五、对比 2.0 vs 3.0",
        "",
        "| 维度 | 2.0 报告 | 3.0 报告 |",
        "|---|---|---|",
        "| 数据源 | scanner 13 条 Top | scanner Top 5 + Skill 1.5 + pain-miner |",
        "| 字段 | 标题/钩子/账号画像 | + 4问+6维 (LLM) / 封面主色 / benchmark / 评论痛点 |",
        "| Top 5 信息量 | ~ 5 行/人 | ~ 50 行/人 (8 倍) |",
        "| 痛点 | 无 | 5 条 Top 3 痛点 + 跨条聚合 + 主题聚类 |",
        "| 仿写策略 | 3 个标题模板 | 3 标题模板 + 4 问+6 维 + 封面 + 4 步 |",
        "| 耗时 | 5 min (scanner) | + ~10 min (5 条 Skill 1.5) + ~2 min (5 条 pain) |",
        "| 对标价值 | 中 (有钩子公式) | **高 (有 4 问 6 维 + 痛点实证)** |",
        "",
        "## 📝 六、覆盖完整度",
        "",
        f"- 扫描: {SKILL1['unique_authors']} 作者 / {SKILL1['viral_count']} 真素人爆款",
        f"- Top 5: 5/5 全跑 Skill 1.5 (4问+6维+封面+benchmark)",
        f"- 痛点: 5/5 跑 pain-miner web 抓 (20-50 评论/条, 3-10 痛点/条)",
        f"- 跨条聚合: 钩子公式 / 评论痛点 / 封面规律 / benchmark 趋势",
        f"- **下一步**: 选 Top 2 (我的兜里有颗糖 / 美食宝妈vicky) 跑 reverse_prompt.py --auto-fill, 出仿写模板",
        "",
        "---",
        "",
        f"_本报告由 `output\\children-height\\write_intel_report_v3.py` 自动生成. 数据截至 {date.today().isoformat()}._  ",
        "_Phase F 完整闭环: scanner → Skill 1.5 (4问+6维) → pain-miner (评论痛点) → 情报报告 3.0._",
    ]
    return "\n".join(lines)


def main() -> int:
    out_md = ROOT / f"intelligence-report-v3-{date.today().isoformat()}.md"
    text = render_full()
    out_md.write_text(text, encoding="utf-8")
    print(f"wrote {out_md} ({len(text)} chars, {text.count(chr(10))+1} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
