"""
topic_generator.py — Skill 2.x 选题库生成器 (Step ⑥ 补齐)

输入: pain-miner JSON × N (多个关键词) + (可选) combined-viral.json
输出: output/topic-library/{date}-topic-library.md + .json

零抓取, 零 API 成本: 基于已有 pain-miner 159 痛点反向聚合选题库
⚠️ 限制: 选题质量 = 痛点信号强度 (likes) + 跨关键词通用度

用法:
    python topic_generator.py --pain-dir output/batch-full-5kw --pattern "pain-miner-*.json"
    python topic_generator.py --pain-dir output/batch-full-5kw --pattern "pain-miner-*.json" --viral-json output/batch-full-5kw/combined-viral.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

# 防 Windows GBK (CONVENTIONS #17)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "topic-library"


def load_all_pains(pain_dir: Path, pattern: str) -> list[dict[str, Any]]:
    """从多个 pain-miner JSON 加载所有痛点"""
    files = sorted(pain_dir.glob(pattern))
    all_pains: list[dict] = []
    for f in files:
        d = json.loads(f.read_text(encoding="utf-8-sig"))
        kw = d.get("filters", {}).get("keyword") or f.stem.replace("pain-miner-", "")
        for n in d.get("per_note", []):
            for tp in n.get("top_pains", []):
                all_pains.append({
                    "keyword": kw,
                    "note_id": n.get("note_id", "?"),
                    "content": tp.get("content", ""),
                    "likes": tp.get("likes", 0),
                    "categories": tp.get("categories", []),
                    "is_author": tp.get("is_author", False),
                    "nickname": tp.get("nickname", ""),
                })
    return all_pains


def normalize_content(text: str) -> str:
    """痛点文本归一化 (去标点/空格/emoji 大小写)"""
    text = re.sub(r"[【】\-\s,.，。!！?？、…​]+", "", text)
    return text.strip().lower()


def aggregate_by_content(pains: list[dict]) -> list[dict[str, Any]]:
    """按归一化 content 聚合 (识别跨关键词通用痛点)"""
    groups: dict[str, dict] = defaultdict(lambda: {
        "sample": "",
        "keywords": Counter(),
        "categories": Counter(),
        "total_likes": 0,
        "max_likes": 0,
        "occurrences": 0,
        "note_ids": set(),
    })
    for p in pains:
        norm = normalize_content(p["content"])
        if not norm or len(norm) < 4:
            continue
        g = groups[norm]
        if not g["sample"]:
            g["sample"] = p["content"]
        g["keywords"][p["keyword"]] += 1
        for c in p["categories"]:
            g["categories"][c] += 1
        g["total_likes"] += p["likes"]
        g["max_likes"] = max(g["max_likes"], p["likes"])
        g["occurrences"] += 1
        g["note_ids"].add(p["note_id"])
    # 转 list, 计算价值分
    results = []
    for norm, g in groups.items():
        # 价值分 = 跨关键词数 × 3 + 总 likes / 10 + 出现次数
        score = len(g["keywords"]) * 30 + g["total_likes"] / 10 + g["occurrences"] * 5
        results.append({
            "normalized": norm,
            "sample": g["sample"],
            "keywords": dict(g["keywords"]),
            "categories": dict(g["categories"]),
            "total_likes": g["total_likes"],
            "max_likes": g["max_likes"],
            "occurrences": g["occurrences"],
            "n_keywords": len(g["keywords"]),
            "n_notes": len(g["note_ids"]),
            "value_score": round(score, 1),
        })
    return sorted(results, key=lambda x: x["value_score"], reverse=True)


def group_by_category(pains: list[dict]) -> dict[str, list[dict]]:
    """按 categories 字段分桶 (单痛点可属多类, 这里取首个)"""
    buckets: dict[str, list] = defaultdict(list)
    for p in pains:
        if p["categories"]:
            cat = p["categories"][0]  # 取首个 category
            buckets[cat].append(p)
        else:
            buckets["uncategorized"].append(p)
    # 每桶按 likes 降序
    return {k: sorted(v, key=lambda x: -x["likes"]) for k, v in buckets.items()}


CATEGORY_LABEL = {
    "question": "❓ question (用户问什么 — 科普答疑类)",
    "pain": "😣 pain (用户痛什么 — 解决方案类)",
    "request": "🙏 request (用户求什么 — 教程类)",
    "suggestion": "💡 suggestion (用户建议 — 对比测评类)",
    "criticism": "⚠️ criticism (用户批评 — 避坑指南类)",
    "praise": "👏 praise (用户夸 — 验证已有方向)",
    "uncategorized": "❔ uncategorized",
}

CATEGORY_TITLE_HINT = {
    "question": "→ 适合写「为什么/怎么/是不是」科普答疑型笔记",
    "pain": "→ 适合写「我懂你的痛 — 解决方案」笔记",
    "request": "→ 适合写「求带/教程/清单」型笔记",
    "suggestion": "→ 适合写「对比/测评/建议」型笔记",
    "criticism": "→ 适合写「避坑指南/内幕揭秘」笔记",
    "praise": "→ 验证已有爆款方向, 复用同款",
}


def write_markdown(out_path: Path, pains: list[dict], groups: list[dict], by_cat: dict, pain_dir: Path, viral_path: Path | None) -> None:
    n_pains = len(pains)
    n_unique = len(groups)
    n_cross = sum(1 for g in groups if g["n_keywords"] >= 2)
    lines = [
        f"# 选题库 (Step ⑥ 补齐)",
        "",
        f"> **数据源**: `{pain_dir}` (5 个 pain-miner JSON)  ",
        f"> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"> **痛点条数 / 归一去重后 / 跨关键词通用**: {n_pains} / {n_unique} / {n_cross}",
        "",
        "---",
        "",
        "## 🎯 跨关键词通用痛点 (最高价值)",
        "",
        "> 同一痛点出现在 ≥2 个关键词下 → 跨行业通用 → **优先做这种选题**",
        "",
        "| 排名 | 痛点 (示例) | 跨关键词数 | 出现次数 | 总点赞 | 价值分 | 涉及关键词 | 适合写 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    cross_top = [g for g in groups if g["n_keywords"] >= 2][:10]
    if not cross_top:
        lines.append("| - | _无跨关键词通用痛点_ | | | | | | |")
    else:
        for i, g in enumerate(cross_top, 1):
            kw_str = " / ".join(g["keywords"].keys())
            cat = max(g["categories"].items(), key=lambda x: x[1])[0] if g["categories"] else "uncategorized"
            hint = CATEGORY_TITLE_HINT.get(cat, "").split("「")[0].replace("→ 适合写", "")
            sample = g["sample"][:50].replace("|", "/").replace("\n", " ")
            lines.append(
                f"| {i} | {sample} | {g['n_keywords']} | {g['occurrences']} | {g['total_likes']} | {g['value_score']} | {kw_str} | {hint} |"
            )

    lines += [
        "",
        "---",
        "",
        "## 📚 按分类分桶 (6 类 + 1 兜底)",
        "",
    ]
    for cat in ["question", "pain", "request", "suggestion", "criticism", "praise", "uncategorized"]:
        items = by_cat.get(cat, [])
        if not items:
            continue
        lines += [
            f"### {CATEGORY_LABEL[cat]}",
            "",
            f"**{len(items)} 条 / 总点赞 {sum(p['likes'] for p in items):,}** {CATEGORY_TITLE_HINT.get(cat, '')}",
            "",
            "| 排名 | 点赞 | 关键词 | 评论 (Top 5) |",
            "|---|---|---|---|",
        ]
        for i, p in enumerate(items[:5], 1):
            kw = p["keyword"]
            text = p["content"][:60].replace("|", "/").replace("\n", " ")
            lines.append(f"| {i} | {p['likes']} | {kw} | {text} |")
        lines.append("")

    # 按关键词分桶
    lines += [
        "---",
        "",
        "## 🏷️ 按关键词分桶",
        "",
    ]
    by_kw: dict[str, list] = defaultdict(list)
    for p in pains:
        by_kw[p["keyword"]].append(p)
    for kw in sorted(by_kw.keys()):
        items = by_kw[kw]
        lines += [
            f"### {kw}",
            "",
            f"**{len(items)} 条痛点 / 总点赞 {sum(p['likes'] for p in items):,}**",
            "",
            "| 排名 | 点赞 | 分类 | 评论 (Top 3) |",
            "|---|---|---|---|",
        ]
        for i, p in enumerate(sorted(items, key=lambda x: -x["likes"])[:3], 1):
            cat = p["categories"][0] if p["categories"] else "-"
            text = p["content"][:55].replace("|", "/").replace("\n", " ")
            lines.append(f"| {i} | {p['likes']} | {cat} | {text} |")
        lines.append("")

    # 总洞察
    lines += [
        "---",
        "",
        "## 💡 选题行动建议",
        "",
    ]
    insights: list[str] = []
    if cross_top:
        top1 = cross_top[0]
        insights.append(
            f"1. **优先做 {top1['sample'][:30]}** —— 跨 {top1['n_keywords']} 关键词 / {top1['total_likes']} 总点赞 / 价值分 {top1['value_score']}（最高）"
        )
    # 最多 category
    cat_counter = Counter()
    for p in pains:
        for c in p["categories"]:
            cat_counter[c] += 1
    if cat_counter:
        top_cat = cat_counter.most_common(1)[0]
        insights.append(f"2. **最多的是 {top_cat[0]} 类 ({top_cat[1]} 条)** → 选题主战场: {CATEGORY_TITLE_HINT.get(top_cat[0], '')}")
    # 跨关键词占比
    if n_unique > 0:
        cross_pct = n_cross / n_unique * 100
        insights.append(f"3. **跨关键词通用痛点占比 {cross_pct:.0f}%** ({n_cross}/{n_unique}) → 头部价值选题基数")
    # 点赞极差
    all_likes = [p["likes"] for p in pains]
    if all_likes:
        insights.append(f"4. **点赞分布**: 最高 {max(all_likes)} / 中位 {sorted(all_likes)[len(all_likes)//2]} / 最低 {min(all_likes)} → 高赞选题用 Top 20% 痛点")
    lines.extend(insights)
    lines.append("")

    # 互补性分析
    if viral_path and viral_path.exists():
        try:
            viral = json.loads(viral_path.read_text(encoding="utf-8-sig"))
            if isinstance(viral, dict):
                viral = viral.get("notes") or viral.get("data") or []
            viral_titles = [n.get("title", "") for n in viral]
            viral_kw = [n.get("source_keyword", "") for n in viral]
            lines += [
                "---",
                "",
                "## 🔍 与 87 爆款的互补性 (蓝海机会)",
                "",
                f"> 痛点 vs 已爆标题 → 找「用户痛但没爆款」的 = 蓝海",
                "",
            ]
            # 痛点关键词（高频字） vs 爆款标题关键词
            pain_words = Counter()
            for p in pains:
                tokens = re.findall(r"[一-龥]{2,4}", p["content"])
                for t in tokens:
                    if len(t) >= 2:
                        pain_words[t] += p["likes"]
            viral_words = Counter()
            for t in viral_titles:
                for w in re.findall(r"[一-龥]{2,4}", t):
                    viral_words[w] += 1
            # 痛点热度高但爆款少的
            blue_ocean: list[tuple[str, int, int]] = []
            for w, plikes in pain_words.most_common(50):
                vcount = viral_words.get(w, 0)
                if plikes > 500 and vcount <= 2:
                    blue_ocean.append((w, plikes, vcount))
            if blue_ocean:
                lines += ["| 关键词 | 痛点总赞 | 爆款提及数 | 蓝海指数 |", "|---|---|---|---|"]
                for w, pl, vc in blue_ocean[:10]:
                    bo = pl / max(vc, 1) / 100
                    lines.append(f"| {w} | {pl} | {vc} | {'🔥' * min(int(bo), 5)} |")
            else:
                lines.append("_痛点高赞词基本都被爆款覆盖, 没有明显蓝海_")
            lines.append("")
        except Exception as e:
            lines.append(f"> ⚠️ 互补性分析失败: {e}\n")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Skill 2.x 选题库生成器 (Step ⑥)")
    p.add_argument("--pain-dir", required=True, help="pain-miner JSON 所在目录")
    p.add_argument("--pattern", default="pain-miner-*.json", help="文件匹配 glob")
    p.add_argument("--viral-json", default="", help="(可选) combined-viral.json 做蓝海分析")
    p.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = p.parse_args()

    pain_dir = Path(args.pain_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Skill 2.x topic-generator v0.1.0 ===")
    print(f"pain_dir: {pain_dir}")

    pains = load_all_pains(pain_dir, args.pattern)
    print(f"  ✓ 加载 {len(pains)} 条痛点 (raw)")

    groups = aggregate_by_content(pains)
    by_cat = group_by_category(pains)
    n_cross = sum(1 for g in groups if g["n_keywords"] >= 2)
    print(f"  ✓ 去重后 {len(groups)} 条 / 跨关键词通用 {n_cross} 条")

    viral_path = Path(args.viral_json) if args.viral_json else None
    date_str = datetime.now().strftime("%Y%m%d")
    md_path = out_dir / f"{date_str}-topic-library.md"
    json_path = out_dir / f"{date_str}-topic-library.json"
    write_markdown(md_path, pains, groups, by_cat, pain_dir, viral_path)
    json_path.write_text(json.dumps({"groups": groups, "by_category_count": {k: len(v) for k, v in by_cat.items()}}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ {md_path}")
    print(f"  ✓ {json_path}")

    print(f"\n=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
