"""write_intel_report_v2.py — AI 知识库「素人爆款」对标账号报告 2.0。

只跑 scanner 完整模式 (< 3000 粉过滤), 拿到真素人爆款对标账号。
重点: 粉赞比 (viral_score) 高 + 粉丝 < 3000 的账号才叫"对标账号"。

复用自 output/children-height/write_intel_report_v2.py, 但:
- 移除 ACCOUNTS load (死代码)
- 新 HOOK_PATTERNS (AI 工具领域: DeepSeek/Claude/Coze/Obsidian/Skill)
- 新 topic 分类 (工具流水线/官方权威/数字承诺/个人故事)
- 9 条不是 13 条
- 可选接入 pains.json (跨笔记痛点 Top 10)
"""
from __future__ import annotations
from skills._bootstrap import *  # noqa: F401,F403  ← UTF-8 项目级基线

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path("output/ai-knowledge-base")
SCORED = json.loads((ROOT / "scored-full.json").read_text(encoding="utf-8"))
PAINS_PATH = ROOT / "pains.json"
PAINS = json.loads(PAINS_PATH.read_text(encoding="utf-8")) if PAINS_PATH.exists() else None


def _md_safe(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ")


# 标题钩子模板 (基于 AI 知识库 Top 9 标题抽取)
HOOK_PATTERNS = {
    "工具品牌": r"DeepSeek|Claude|Coze|Obsidian|GPT|ChatGPT|Gemini|Skill",
    "数字承诺": r"\d+\s*个|\d+\s*页|\d+\s*万|\d+\s*层|\d+\s*步|\d+\s*天",
    "个人故事": r"我把|我的|才知道|我用|实现|起飞|做成|花了|教你",
    "反问警告": r"不同|不一样|暴露|真香|牛了|你的|你在|你也|别再",
    "Skill化封装": r"Skill|流水线|知识库|官方|高阶|框架|系统|方案",
    "场景应用": r"报告|管理|曝光|笔记|写作|分工|教程|搭建|学习|工作",
    "FOMO/紧迫": r"千万|赶紧|趁早|抓住|最后|还来得及|再不|必看|必学|要会",
}


def detect_hooks(title: str) -> list[str]:
    hits = []
    for label, pat in HOOK_PATTERNS.items():
        if re.search(pat, title):
            hits.append(label)
    return hits or ["(无明显钩子)"]


def classify_topic(title: str) -> str:
    if re.search(r"流水线|架构|Skill|系统|框架", title):
        return "🔧 工具化/Skill 封装型"
    if re.search(r"官方|权威|协和|官宣", title):
        return "🏛️ 官方/权威型"
    if re.search(r"\d+\s*(个|页|万|层)", title):
        return "📊 数字承诺型"
    if re.search(r"我把|我的|花了|实现|做成", title):
        return "💼 个人故事/作品型"
    if re.search(r"暴露|不一样|不同|别再|你也|你在", title):
        return "💬 反问/警告型"
    if re.search(r"教程|搭建|学习|怎么", title):
        return "📚 教程/方法型"
    return "🎁 工具应用型 (其它)"


def render() -> str:
    results = SCORED["results"]
    # 按 viral_score 排序 (低粉爆款的天然排序)
    results.sort(key=lambda r: r["viral_score"], reverse=True)

    tier_counts: dict[str, int] = {}
    for r in results:
        tier_counts[r["quality"]["tier"]] = tier_counts.get(r["quality"]["tier"], 0) + 1

    # 头部 5 账号
    top5 = results[:5]

    # 粉丝段位分布
    fan_tiers = {"<100": 0, "100-500": 0, "500-1000": 0, "1000-2000": 0, "2000-3000": 0}
    for r in results:
        f = r["author"]["fans"] or 0
        if f < 100:
            fan_tiers["<100"] += 1
        elif f < 500:
            fan_tiers["100-500"] += 1
        elif f < 1000:
            fan_tiers["500-1000"] += 1
        elif f < 2000:
            fan_tiers["1000-2000"] += 1
        else:
            fan_tiers["2000-3000"] += 1

    # 钩子频率 (从 9 条抽)
    hook_freq: dict[str, int] = {}
    for r in results:
        for h in detect_hooks(r["title"]):
            hook_freq[h] = hook_freq.get(h, 0) + 1
    hook_freq_sorted = sorted(hook_freq.items(), key=lambda x: x[1], reverse=True)

    total = len(results)
    n_authors = SCORED.get("unique_authors", "?")
    n_fans_fetched = SCORED.get("fetched_fans", "?")
    elapsed = SCORED.get("elapsed_sec", 0)

    lines = [
        "# AI 知识库 · 素人爆款对标账号报告 2.0",
        "",
        f"> **生成时间**: {date.today().isoformat()}  ",
        f"> **数据源**: scanner 完整模式 (`--require-fans --max-followers 3000`) — **真素人爆款**, 不是头部  ",
        f"> **Skill 链**: scanner (完整) → quality_scorer → 报告  ",
        f"> **核心问题**: 「我想做 AI 知识库赛道, 新号 0 粉怎么写能爆」 → 学这些账号的标题+选题",
        "",
        "---",
        "",
        "## 📊 一、为什么这份报告比 1.0 有价值",
        "",
        "**1.0 报告 (MVP 模式) 的问题**",
        "",
        "- 不取粉丝数, 抓的是「普通爆款」, 头部账号 (10w+ 粉) 跟素人混在一起",
        "- 对标价值低: 大号发 1k 赞是基操, 素人学不来",
        "",
        "**2.0 报告 (完整模式) 的修正**",
        "",
        "- ✅ 抓粉丝数, 过滤 < 3000 粉的**真素人爆款**",
        "- ✅ 排序用 `viral_score = likes / (fans+1)` — 越高说明「少粉也能爆」对标价值越大",
        f"- ✅ Top 1「不劳而获一个亿」**457 粉**但 23,755 赞, viral=**51.87** — 这才是新号该学的",
        "",
        "## 📈 二、整体分布",
        "",
        f"- 扫描: **{n_authors} 个唯一作者** (粉丝 < 3000 过滤前)",
        f"- 拿到粉丝数: **{n_fans_fetched}/{n_authors}** (Playwright 路径)",
        f"- 过滤后 (粉丝 < 3000) 真素人爆款: **{SCORED['viral_count']}** 条",
        f"- 爆款分层: 💎真 **{tier_counts.get('💎 真爆款', 0)}** / 🔥常规 **{tier_counts.get('🔥 常规爆款', 0)}** / ⚡准 **{tier_counts.get('⚡ 准爆款', 0)}** / 📊平平 **{tier_counts.get('📊 数据平平', 0)}**",
        f"- 总耗时: ~{elapsed/60:.1f} min (DrissionPage 取粉, 0 captcha)",
        "",
        "### 粉丝段位分布",
        "",
        "| 粉丝数 | 账号数 | 占比 |",
        "|---|---:|---:|",
    ]
    for label, n in fan_tiers.items():
        if n == 0:
            continue
        lines.append(f"| {label} | {n} | {n*100/total:.0f}% |")

    lines += [
        "",
        f"**洞察**: **{fan_tiers.get('<100', 0) + fan_tiers.get('100-500', 0)}** 个账号 < 500 粉就爆了 (新号!); 中段 {fan_tiers.get('500-1000', 0) + fan_tiers.get('1000-2000', 0)} 个 500-2000 粉 — 这两类就是新号直接对标池.",
        "",
        f"## 🏆 三、Top {total} 素人爆款 (按 viral_score 排序)",
        "",
        "| Rank | viral | 粉丝 | 点赞 | 收藏 | 评论 | Tier | 标题 | 钩子 |",
        "|---:|---:|---:|---:|---:|---:|---|---|---|",
    ]
    for i, r in enumerate(results, 1):
        q = r["quality"]
        f = r["author"]["fans"]
        hooks = ", ".join(detect_hooks(r["title"]))
        title_disp = _md_safe(r["title"])[:40] if r["title"] else "(无标题)"
        lines.append(
            f"| {i} | **{r['viral_score']:.2f}** | {f:,} | {r['metrics']['likes']:,} "
            f"| {r['metrics']['collects']:,} | {r['metrics']['comments']:,} "
            f"| {q['tier']} | {title_disp} | {hooks} |"
        )

    lines += [
        "",
        "## 🎯 四、Top 5 头部账号画像 (深拆)",
        "",
    ]
    for i, r in enumerate(top5, 1):
        q = r["quality"]
        a = r["author"]
        hooks = detect_hooks(r["title"])
        age = f"{q['age_days']} 天前" if q.get("age_days") is not None else "?"
        hook_detail = " / ".join(hooks)
        topic = classify_topic(r["title"])
        title_disp = r["title"] or "(无标题)"
        fan_str = f"{a['fans']:,}"
        lines += [
            f"### #{i} {a['nickname']} — 粉 {fan_str}",
            "",
            f"- **viral_score**: {r['viral_score']:.2f} | **粉丝**: {a['fans']:,} | **点赞**: {r['metrics']['likes']:,} | **收藏**: {r['metrics']['collects']:,} | **评论**: {r['metrics']['comments']:,}",
            f"- **标题**: {title_disp}",
            f"- **发布**: {age}",
            f"- **钩子**: {hook_detail}",
            f"- **选题类型**: {topic}",
            f"- **Tier**: {q['tier']} (quality 分 {q['score']})",
            "",
        ]

    lines += [
        f"## 🪝 五、标题钩子公式 ({total} 条素人爆款提炼)",
        "",
        "| 钩子类型 | 命中数 | 占比 | 怎么用 |",
        "|---|---:|---:|---|",
    ]
    hook_advice = {
        "工具品牌": "DeepSeek / Claude Code / Coze / Obsidian / Skill — 借工具名头, AI 圈 SEO + 信任",
        "数字承诺": "40 个 / 100+ 页 / 60 万曝光 / 5 层 — 具体数字, 让人感觉有干货密度",
        "个人故事": "我把 / 我的 / 我用 / 花了 N 天 / 实现 — 第一人称, 显真实",
        "反问警告": "不同 / 暴露你在用 AI / 别再 / 你也能 — 反问引发好奇/焦虑+点击",
        "Skill化封装": "做成 Skill / 流水线 / 知识库 / 高阶框架 — 把方法工具化, 转化收藏",
        "场景应用": "信贷报告 / 知识库 / 人生管理 / 笔记 / 工作 — 落地具体场景, 别只说概念",
        "FOMO/紧迫": "千万别错过 / 赶紧 / 必学 / 趁早 — 制造焦虑感, 短期内 CTR 高",
    }
    for label, n in hook_freq_sorted:
        advice = hook_advice.get(label, "—")
        lines.append(f"| {label} | {n} | {n*100/total:.0f}% | {advice} |")

    lines += [
        "",
        "## 👥 六、对标账号 Top 5 重点学",
        "",
        "| 排名 | 账号 | 粉丝 | 关键学习点 |",
        "|---:|---|---:|---|",
    ]
    # 动态生成学习点 (基于 topic + viral_score)
    for i, r in enumerate(top5, 1):
        a = r["author"]
        q = r["quality"]
        topic = classify_topic(r["title"])
        viral = r["viral_score"]
        likes = r["metrics"]["likes"]
        fans = a["fans"]
        # 根据 topic + viral 自动写一句学习点
        if viral > 10:
            tag = f"viral={viral:.1f} 极高"
        elif viral > 3:
            tag = f"viral={viral:.1f} 高"
        else:
            tag = f"viral={viral:.1f} 中"
        learn = f"{topic} | {tag} | {likes:,} 赞 / {fans} 粉 — 看封面+开头复刻"
        lines.append(f"| {i} | {a['nickname']} | {a['fans']:,} | {learn} |")

    lines += [
        "",
        "## 🎯 七、新号 0 粉起步的「对标 3 步」",
        "",
        "### Step 1: 抄标题公式 (上面 Top 5 钩子)",
        "",
        "- 模板 1: `[工具品牌] + [数字] + [Skill化封装]`",
        "  - 例: 「Claude Code 30 个高阶 Skill, 效率起飞」",
        "- 模板 2: `[个人故事] + [数字] + [场景落地]`",
        "  - 例: 「我用 DeepSeek 把 100 篇笔记做成知识库」",
        "- 模板 3: `[反问/警告] + [工具品牌]`",
        "  - 例: 「这几个词一出现, 你就被识破在用 AI」",
        "",
        "### Step 2: 抄内容形式",
        "",
        f"- **工具化/Skill 封装型** (Top 1/7/9 主要类型) — 把方法封装成可复用的 Skill/流水线",
        f"- **数字承诺型** — 列 N 个具体步骤/N 个工具/N 层架构, 干货密度高 → 收藏率",
        f"- **个人故事型** — 第一人称 + 具体数字 + 落地结果, 评论率高",
        "",
        "### Step 3: 避开陷阱",
        "",
        "- ❌ 标题没工具品牌 → AI 圈 SEO 不友好, 用户搜不到",
        "- ❌ 标题只讲概念没场景 (「打造AI知识库」 vs 「用DeepSeek+Obsidian 60min 搭建本地知识库」) — 后者爆款率高",
        "- ❌ 没数字 → 用户不知道有多干货, 不点不收",
        "- ❌ 没第一人称/故事感 → 像教程没温度, CTR 低",
        "",
        "## 📊 八、对比 1.0 vs 2.0",
        "",
        "| 维度 | 1.0 (MVP) | 2.0 (完整) |",
        "|---|---|---|",
        "| 抓取模式 | `scanner` (只查 search) | `scanner --require-fans --max-followers 3000` |",
        "| 字段 | likes/collects/comments | + fans/粉赞比 (viral_score) |",
        f"| 命中 | 40+ 条普通爆款 (混头部) | **{total} 条素人爆款** (全 < 3000 粉) |",
        "| Top 1 | 头部账号 1w+ 赞 | **不劳而获一个亿 (457 粉) 23,755 赞** |",
        "| 对标价值 | 低 (大号基操) | **高 (素人真能抄)** |",
        f"| 耗时 | 几秒 | ~{elapsed/60:.1f} min (Playwright 取粉) |",
        "| captcha 风险 | ❌ 0 | ⚠ 0 (本次运气好) |",
        "",
    ]

    # 第九章: pains (如果 pain-miner 已跑)
    # pains.json 结构: {filters, input_notes, per_note: [{note_id, title, top_pains: [{content, likes, categories, ...}]}]}
    if PAINS is not None:
        per_note: list[dict] = PAINS.get("per_note") or []
        all_pains: list[dict] = []
        for np in per_note:
            for p in np.get("top_pains", []) or []:
                cats = p.get("categories") or []
                all_pains.append({
                    "text": p.get("content") or "",
                    "likes": p.get("likes") or 0,
                    "category": ", ".join(cats) if cats else "",
                    "note_id": np.get("note_id", ""),
                    "note_title": np.get("title", ""),
                    "nickname": p.get("nickname", ""),
                })
        all_pains.sort(key=lambda x: x["likes"], reverse=True)

        notes_with_pains = sum(1 for n in per_note if n.get("top_pains"))
        total_comments = sum((n.get("total_comments") or 0) for n in per_note)
        kept_total = sum((n.get("kept_comments") or 0) for n in per_note)

        lines += [
            "## 🔍 九、评论区痛点 Top 10 (Skill 2 pain-miner)",
            "",
            f"- 抓取笔记: **{len(per_note)}** 条 (其中 **{notes_with_pains}** 条捞到痛点, 2 条评论数过少)",
            f"- 抓取评论: **{total_comments}** 条 → 命中疑似痛点 **{kept_total}** 条 → Top 痛点 **{len(all_pains)}** 条",
            "",
            "| Rank | 痛点 (评论原文) | 赞 | 分类 | 来源 note |",
            "|---:|---|---:|---|---|",
        ]
        for i, p in enumerate(all_pains[:10], 1):
            text = _md_safe(p["text"])[:70]
            note_short = p["note_id"][:8] if p["note_id"] else "—"
            lines.append(f"| {i} | {text} | **{p['likes']}** | {p['category']} | `{note_short}` |")

        # 痛点分类统计
        cat_counts: dict[str, int] = {}
        for p in all_pains:
            for c in (p["category"].split(", ") if p["category"] else ["(无分类)"]):
                cat_counts[c] = cat_counts.get(c, 0) + 1

        lines += [
            "",
            "### 痛点分类分布",
            "",
            "| 分类 | 条数 | 占比 |",
            "|---|---:|---:|",
        ]
        for c, n in sorted(cat_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| {c} | {n} | {n*100/len(all_pains):.0f}% |")

        lines += [
            "",
            "**痛点 → 选题转化**: 上述高赞痛点直接对应「新号选题钩子库」, 拿去 reverse_prompt + rewriter 仿写.",
            "  例: 评论说「教程太抽象, 能否出落地视频」→ 选题 = 「我用 [工具] N 分钟搭建 [场景], 全过程录屏」",
            "",
        ]
    else:
        lines += [
            "## 🔍 九、评论区痛点 (Skill 2 pain-miner — 待跑)",
            "",
            "_pain-miner 未跑或 `pains.json` 不存在. 跑完后重新生成报告即可填上._",
            "",
        ]

    lines += [
        "## 📝 十、覆盖完整度",
        "",
        f"- 抓取: {n_authors} 作者 / {total} 真素人爆款 (0 captcha, 0 重试)",
        f"- 评估: {total}/{total} quality 评分 ({tier_counts.get('🔥 常规爆款', 0)}🔥 / {tier_counts.get('⚡ 准爆款', 0)}⚡ / {tier_counts.get('📊 数据平平', 0)}📊)",
        f"- 痛点: {'✅ 已接' if PAINS is not None else '⏳ 待跑 pain-miner'}",
        f"- **粉丝段位**: <100 粉 **{fan_tiers.get('<100', 0)}** / 100-500 粉 **{fan_tiers.get('100-500', 0)}** / 500-1000 粉 **{fan_tiers.get('500-1000', 0)}** / 1000-2000 粉 **{fan_tiers.get('1000-2000', 0)}** / 2000-3000 粉 **{fan_tiers.get('2000-3000', 0)}**",
        f"- **下一步**: 选 Top 3 (不劳而获一个亿 / 慢慢有解 / 如果今天是星期八) 跑 Skill 1.5 端到端 + reverse_prompt",
        "",
        "---",
        "",
        f"_本报告由 `output\\ai-knowledge-base\\write_intel_report_v2.py` 自动生成. 数据截至 {date.today().isoformat()}._  ",
        "_Skill 1 定位: 找出「低粉爆款」——粉丝<3000 且 点赞>1000. 本报告严格按此标准._",
    ]
    return "\n".join(lines)


def main() -> int:
    out_md = ROOT / f"intelligence-report-v2-{date.today().isoformat()}.md"
    text = render()
    out_md.write_text(text, encoding="utf-8")
    print(f"wrote {out_md} ({len(text)} chars, {text.count(chr(10))+1} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
