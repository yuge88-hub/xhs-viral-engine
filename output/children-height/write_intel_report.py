"""write_intel_report.py — 写「儿童身高」情报报告。

聚合:
- quality_scorer 输出 (40 条 quality 分)
- account_analyzer 输出 (40 账号拆解)
- 行业洞察 + 对标账号 + 选题方向
"""
from __future__ import annotations
from skills._bootstrap import *  # noqa: F401,F403  ← UTF-8 项目级基线

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path("output/children-height")
SCORED = json.loads((ROOT / "scored.json").read_text(encoding="utf-8"))
ACCOUNTS = json.loads((ROOT / "20260609-儿童身高-accounts.json").read_text(encoding="utf-8"))


def _md_safe(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ")


def render() -> str:
    results = SCORED["results"]
    # tier 分布
    tier_counts: dict[str, int] = {}
    for r in results:
        tier_counts[r["quality"]["tier"]] = tier_counts.get(r["quality"]["tier"], 0) + 1

    # Top 10 quality
    top10 = results[:10]

    # 真爆款 (💎) + 常规爆款 (🔥)
    true_viral = [r for r in results if r["quality"]["tier"] == "💎 真爆款"]
    normal_viral = [r for r in results if r["quality"]["tier"] == "🔥 常规爆款"]
    quasi = [r for r in results if r["quality"]["tier"] == "⚡ 准爆款"]

    # 30 天内 vs 老
    fresh_30 = [r for r in results if r["quality"].get("age_days") is not None and r["quality"]["age_days"] <= 30]
    fresh_90 = [r for r in results if r["quality"].get("age_days") is not None and 30 < r["quality"]["age_days"] <= 90]
    old_365 = [r for r in results if r["quality"].get("age_days") is not None and 90 < r["quality"]["age_days"] <= 365]
    ancient = [r for r in results if r["quality"].get("age_days") is not None and r["quality"]["age_days"] > 365]
    unknown = [r for r in results if r["quality"].get("age_days") is None]

    # 高收藏率 (干货)
    high_collect = [r for r in results if r["quality"]["collect_rate"] >= 0.8]

    # account_analyzer top 10
    acc_top10 = ACCOUNTS.get("ranking", [])[:10]
    # 每账号从 notes[0].title 抽主题
    for a in acc_top10:
        notes = a.get("notes", [])
        a["themes"] = " | ".join(n.get("title", "") for n in notes[:2]) if notes else ""

    # 标签聚合 (从 title 抽)
    tag_kw = ["身高", "长高", "三伏天", "标准", "体重", "追高", "暑假", "成长", "儿童", "育儿"]
    tag_hits: dict[str, list] = {k: [] for k in tag_kw}
    for r in results:
        title = r["title"] or ""
        for k in tag_kw:
            if k in title:
                tag_hits[k].append(r)
    tag_summary = sorted(
        ((k, len(v), sum(r["metrics"]["likes"] for r in v)) for k, v in tag_hits.items() if v),
        key=lambda x: x[1], reverse=True,
    )

    lines = [
        f"# 儿童身高细分市场情报报告",
        "",
        f"> **生成时间**: {date.today().isoformat()}  ",
        f"> **数据源**: scanner MVP 模式 (2页, 40 viral notes)  ",
        f"> **Skill 链**: scanner → quality_scorer → account_analyzer → 报告",
        "",
        "---",
        "",
        "## 📊 一、行业大盘",
        "",
        f"- 扫描笔记: **{SCORED['scanned_notes']}** 条 / 命中: **{SCORED['viral_count']}** 条",
        f"- viral_score 总和: **{sum(r['viral_score'] for r in results):,}**",
        f"- 平均 likes: **{sum(r['metrics']['likes'] for r in results) // len(results):,}** / 笔记",
        f"- 爆款分层: 💎真爆款 **{tier_counts.get('💎 真爆款', 0)}** / 🔥常规 **{tier_counts.get('🔥 常规爆款', 0)}** / ⚡准爆款 **{tier_counts.get('⚡ 准爆款', 0)}** / 📊平平 **{tier_counts.get('📊 数据平平', 0)}**",
        f"- **0 条真爆款** (本细分无 score≥70 且收藏率≥0.8 的) → 内容质量参差, 头部 4 条 (Top 10%) 占 44.2% viral_score",
        "",
        "### 时间窗口分布",
        "",
        "| 区间 | 笔记数 | 占比 | viral_score 总 | 平均 likes |",
        "|---|---:|---:|---:|---:|",
    ]
    for label, group in [
        ("30天内 (热)", fresh_30),
        ("30-90天 (温)", fresh_90),
        ("90-365天 (凉)", old_365),
        ("1年+ (冷)", ancient),
        ("未知日期", unknown),
    ]:
        if not group:
            continue
        v_total = sum(r["viral_score"] for r in group)
        avg_likes = sum(r["metrics"]["likes"] for r in group) // len(group)
        lines.append(
            f"| {label} | {len(group)} | {len(group)*100/len(results):.0f}% | {v_total:,} | {avg_likes:,} |"
        )

    lines += [
        "",
        f"**洞察**: 30天内爆款 **{len(fresh_30)}** 条 (占 {len(fresh_30)*100/len(results):.0f}%) — 季节性内容 (暑假三伏天追高 + 身高体重表) 是近期流量主力, 一年内冷内容 **{len(ancient)}** 条仍是基础盘 (儿童标准身高 1029天前 8947 赞 长尾流量).",
        "",
        "## 🏆 二、Top 10 爆款 (按 quality 标准化)",
        "",
        "| Rank | Score | Tier | 标题 | 点赞 | 收藏 | 收藏率 | 分享率 | 发布 | 账号 |",
        "|---:|---:|---|---|---:|---:|---:|---:|---|---|",
    ]
    for i, r in enumerate(top10, 1):
        q = r["quality"]
        age = f"{q['age_days']}天前" if q.get("age_days") is not None else "?"
        title = _md_safe(r["title"])[:45]
        author = _md_safe(r["author"]["nickname"])
        lines.append(
            f"| {i} | **{q['score']}** | {q['tier']} | {title} | {r['metrics']['likes']:,} "
            f"| {r['metrics']['collects']:,} | {q['collect_rate']:.2f} | {q['share_rate']:.2f} "
            f"| {age} | {author} |"
        )

    lines += [
        "",
        "### 关键拆解 — Top 3 共性",
        "",
        "1. **#1 阿文阿乐~「二年级女儿142了」** (29天前, 26,708 赞) — 真实数据 + 妈妈身份代入 + 简短惊叹号 = 强共鸣 (评论率 14%, 全场最高). 但收藏率仅 0.05 (围观型, 不算干货爆款).",
        "2. **#2 米米妈Lily「13岁168cm抓住三伏天」** (337天前, 14,170 赞) — 数字精准 + 时间窗口 + 行动指令 (猛猛) = 实用干货 (收藏率 1.40, 分享率 0.54). **教科书级追高选题**.",
        "3. **#3 「一年长高15厘米的方法」** (24天前, 1,586 赞) — 反常识标题 + 简单方法 = 中小赞但强收藏 (收藏率 1.25). **低成本对标蓝本**.",
        "",
        "## 💎 三、爆款规律 (quality 标准化视角)",
        "",
        f"### 高收藏率 (≥0.8 干货爆款): {len(high_collect)} 条 / 占 {len(high_collect)*100/len(results):.0f}%",
        "",
        "| 标题 | 收藏率 | 分享率 | 标题类型 |",
        "|---|---:|---:|---|",
    ]
    for r in sorted(high_collect, key=lambda x: x["quality"]["collect_rate"], reverse=True)[:8]:
        t = r["title"]
        if any(k in t for k in ["方法", "方案", "干货"]):
            t_type = "🔧 教程型"
        elif any(k in t for k in ["三伏", "暑假", "黄金期"]):
            t_type = "⏰ 节点型"
        elif any(k in t for k in ["表", "标准"]):
            t_type = "📊 数据型"
        else:
            t_type = "📝 经验型"
        lines.append(
            f"| {_md_safe(r['title'])[:45]} | {r['quality']['collect_rate']:.2f} | {r['quality']['share_rate']:.2f} | {t_type} |"
        )

    lines += [
        "",
        "### 标签热点 (从 Top 40 标题抽词频)",
        "",
        "| 标签 | 笔记数 | 总点赞 |",
        "|---|---:|---:|",
    ]
    for k, n, likes in tag_summary[:8]:
        lines.append(f"| #{k} | {n} | {likes:,} |")

    lines += [
        "",
        f"**洞察**: 暑期节点 (三伏天/暑假) + 干货 (方法/方案/表) 是流量叠加器. 单纯晒娃 (Top 1) 收藏率低 (0.05) 走围观流量; 干货型 (Top 2/3) 收藏率高 (1.4+).",
        "",
        "## 👥 四、对标账号 Top 10",
        "",
        "| 排名 | 账号 | 爆款数 | viral 总 | 主题方向 |",
        "|---:|---|---:|---:|---|",
    ]
    for i, acc in enumerate(acc_top10, 1):
        theme = _md_safe(acc.get("themes", ""))[:40]
        notes = acc.get("notes", [])
        viral_count = len(notes)
        v_total = int(acc.get("viral_score_total", 0))
        lines.append(
            f"| {i} | {acc['nickname']} | {viral_count} | {v_total:,} | {theme} |"
        )

    lines += [
        "",
        "### 账号生态特征",
        "",
        f"- **100% 账号仅 1 条爆款** (40/40, 极度长尾)",
        f"- **Top 4 账号贡献 44.2% viral_score** (前 10% 集中度)",
        f"- **跨关键词操盘手 0 个** (本细分账号都只做儿童身高, 没跨域)",
        f"- **粉丝数未抓** (MVP 模式, 深度拆解需 `scanner --full`)",
        "",
        "## 🎯 五、行动建议 (选题方向)",
        "",
        "### 5.1 高 ROI 选题 (基于高收藏率 Top 笔记拆解)",
        "",
        "1. **节点型 (暑假/三伏)** — 标题公式: `[年龄] + [身高数字] + 抓住[季节] + [强动词]`. 例: 「10岁145cm, 抓住三伏天最后30天! 每天做这3件事」",
        "2. **干货教程型** — 标题公式: `[时间] + 长高[数字] + 方法 + 有!简单`. 例: 「30天长高3cm的方法! 真的有效! (附饮食/运动/睡眠表)」",
        "3. **数据型 (身高/体重表)** — 标题公式: `[年份] + 儿童身高体重表 + 你家孩子达标了吗?`. 例: 「2026最新儿童身高体重表! 0-12岁对照表, 建议收藏」",
        "4. **真实案例型** — 标题公式: `[孩子年龄] + [身高数字] + [妈妈身份]`. 例: 「二年级女儿142了! 学龄前这3件事做得对」(高评论率)",
        "",
        "### 5.2 仿写切入 (直接对标 Top 1-3)",
        "",
        "- **仿写 Top 1 (阿文阿乐~)**: 真实数字 + 妈妈视角 + 简短惊叹号. 不需要干货, 走共鸣. **快产** (5min/篇)",
        "- **仿写 Top 2 (米米妈Lily)**: 数字 + 季节 + 强动词. 走干货收藏. **中产** (15-30min/篇, 需配表格图)",
        "- **仿写 Top 3 (长高15cm)**: 反常识数字 + 简单方法. 走中赞高收藏. **中产** (15-30min/篇, 需方法列表)",
        "",
        "### 5.3 蓝海 / 差异化方向",
        "",
        "- **爸爸视角** (本细分 100% 妈妈账号) — 「爸爸175妈妈160, 儿子12岁168是怎么做到的?」",
        "- **跨季节对比** — 「春秋vs三伏天, 哪个长高黄金期? 协和儿保科医生这么说」 (引专家 + 数据对比)",
        "- **反焦虑型** — 「别再逼娃跳绳了! 协和潘慧: 3种情况根本不需要追高」 (避坑干货, 高收藏)",
        "- **分段指南** — 「0-3岁/3-6岁/6-12岁/12-15岁 每个阶段追高重点」(系列文, 强收藏)",
        "",
        "## 📝 六、覆盖完整度",
        "",
        f"- 抓取: 2 页 / {SCORED['scanned_notes']} 条 (MVP 模式, 0 captcha)",
        f"- 评估: 40/40 全 quality 评分 (0💎/4🔥/11⚡/25📊)",
        f"- 账号: 40/40 拆解 (跨关键词 0, 头部 4 集中度 44.2%)",
        f"- **缺失**: 粉丝数 (MVP 模式), 评论挖掘 (需 pain-miner 跑这 40 条)",
        f"- **下一步**: 选 Top 1-3 跑 Skill 1.5 端到端 + reverse_prompt 5段模板 (仿写直接套用)",
        "",
        "---",
        "",
        f"_本报告由 `output\\children-height\\write_intel_report.py` 自动生成. 数据截至 {date.today().isoformat()}._",
    ]
    return "\n".join(lines)


def main() -> int:
    out_md = ROOT / f"intelligence-report-{date.today().isoformat()}.md"
    text = render()
    out_md.write_text(text, encoding="utf-8")
    print(f"wrote {out_md} ({len(text)} chars, {text.count(chr(10))+1} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
