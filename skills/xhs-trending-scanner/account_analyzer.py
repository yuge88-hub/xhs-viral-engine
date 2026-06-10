"""
account_analyzer.py — Skill 1.x 账号拆解 (Step ④ 补齐)

输入: scanner JSON (combined-viral.json 或单关键词 viral-XX.json)
输出: output/account-analysis/{date}-{label}-accounts.md + .json

零抓取, 零 API 成本: 基于已有 viral notes 反向聚合账号
⚠️ 限制: MVP 模式跑的 scanner 数据 fans=None, 账号粉丝数不可得
         (要粉丝数得跑 scanner --full 模式, 有 captcha 风险)
         本分析聚焦 "内容策略维度": 榜单 / 爆款分布 / 跨关键词 / 头部长尾

用法:
    python account_analyzer.py --viral-json output/batch-full-5kw/combined-viral.json
    python account_analyzer.py --viral-json output/batch-full-5kw/combined-viral.json --label "5kw合并"
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

# 防 Windows GBK 终端乱码 (CONVENTIONS #17)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "account-analysis"


def load_viral(viral_path: Path) -> list[dict[str, Any]]:
    if not viral_path.exists():
        print(f"ERROR: {viral_path} 不存在", file=sys.stderr)
        sys.exit(1)
    data = json.loads(viral_path.read_text(encoding="utf-8-sig"))
    # 兼容 list / {"notes": [...]} / {"data": [...]} / {"results": [...]}  ← #41 加 results (scored-full.json)
    if isinstance(data, dict):
        notes = data.get("notes") or data.get("data") or data.get("viral_notes") or data.get("results") or []
    else:
        notes = data
    return notes if isinstance(notes, list) else []


def aggregate_by_author(notes: list[dict]) -> dict[str, dict[str, Any]]:
    """按 author.user_id 聚合"""
    by_author: dict[str, dict[str, Any]] = {}
    for n in notes:
        a = n.get("author") or {}
        uid = a.get("user_id") if isinstance(a, dict) else None
        if not uid:
            continue
        if uid not in by_author:
            by_author[uid] = {
                "user_id": uid,
                "nickname": a.get("nickname", "?"),
                "profile_url": a.get("profile_url", ""),
                "fan_source": a.get("fan_source"),
                "notes": [],
                "viral_score_total": 0.0,
                "total_likes": 0,
                "total_collects": 0,
                "total_comments": 0,
                "keywords": Counter(),
                "tags": Counter(),
            }
        e = by_author[uid]
        e["notes"].append(n)
        e["viral_score_total"] += n.get("viral_score", 0) or 0
        m = n.get("metrics") or {}
        e["total_likes"] += m.get("likes", 0) or 0
        e["total_collects"] += m.get("collects", 0) or 0
        e["total_comments"] += m.get("comments", 0) or 0
        kw = n.get("source_keyword")
        if kw:
            e["keywords"][kw] += 1
        for t in n.get("tags", []) or []:
            e["tags"][t] += 1
    return by_author


def extract_title_keywords(titles: list[str], top_n: int = 5) -> list[str]:
    """从标题抽高频关键词 (去停用词)"""
    STOP = {"的", "了", "是", "我", "有", "在", "和", "就", "不", "人", "都", "一",
            "上", "也", "很", "到", "说", "要", "去", "会", "着", "没", "看", "好",
            "这", "那", "吗", "什么", "怎么", "为什么", "做", "让", "用", "你", "他",
            "她", "它", "们", "啊", "吧", "呢", "哦", "哈", "哎", "哇", "呀"}
    words: Counter = Counter()
    for t in titles:
        # 中文: 2-gram 切 (用非中文单字)
        tokens = re.findall(r"[一-龥]{2,6}", t)
        for tok in tokens:
            if tok not in STOP and len(tok) >= 2:
                words[tok] += 1
    return [w for w, _ in words.most_common(top_n)]


def analyze(by_author: dict[str, dict]) -> dict[str, Any]:
    """核心分析: 榜单 / 爆款分布 / 跨关键词 / 头部长尾"""
    n_authors = len(by_author)
    n_notes = sum(len(e["notes"]) for e in by_author.values())
    total_viral = sum(e["viral_score_total"] for e in by_author.values())

    # 1. 榜单 (按 viral_score 总和)
    ranking = sorted(by_author.values(), key=lambda x: x["viral_score_total"], reverse=True)
    top_n = min(20, n_authors)

    # 2. 爆款次数分布
    notes_per_author = Counter(len(e["notes"]) for e in by_author.values())
    burst_distribution = {
        "1_爆款": notes_per_author.get(1, 0),
        "2_3_爆款": sum(v for k, v in notes_per_author.items() if 2 <= k <= 3),
        "4+_爆款": sum(v for k, v in notes_per_author.items() if k >= 4),
    }

    # 3. 跨关键词账号 (在 ≥2 个关键词下都爆)
    cross_kw = [e for e in by_author.values() if len(e["keywords"]) >= 2]
    cross_kw.sort(key=lambda x: x["viral_score_total"], reverse=True)

    # 4. 头部 / 长尾分布 (top 10% vs 其他)
    top10pct = max(1, n_authors // 10)
    top10_viral = sum(e["viral_score_total"] for e in ranking[:top10pct])
    rest_viral = total_viral - top10_viral
    head_tail = {
        "top10pct_accounts": top10pct,
        "top10pct_viral_share": round(top10_viral / total_viral * 100, 1) if total_viral else 0,
        "rest_accounts": n_authors - top10pct,
        "rest_viral_share": round(rest_viral / total_viral * 100, 1) if total_viral else 0,
    }

    return {
        "summary": {
            "n_authors": n_authors,
            "n_notes": n_notes,
            "total_viral_score": int(total_viral),
            "avg_viral_per_author": round(total_viral / n_authors, 0) if n_authors else 0,
        },
        "ranking": ranking[:top_n],
        "burst_distribution": burst_distribution,
        "cross_keyword": cross_kw[:10],
        "head_tail": head_tail,
    }


def write_markdown(out_path: Path, analysis: dict, viral_path: Path) -> None:
    """写账号拆解报告 markdown"""
    s = analysis["summary"]
    lines = [
        f"# 账号拆解报告 (Step ④)",
        "",
        f"> **数据源**: `{viral_path}`  ",
        f"> **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"> **账号数 / 爆款数 / viral_score 总和**: {s['n_authors']} / {s['n_notes']} / {s['total_viral_score']:,}",
        "",
        "---",
        "",
        "## 📊 总览",
        "",
        f"- **账号数**: {s['n_authors']}",
        f"- **爆款笔记数**: {s['n_notes']}",
        f"- **viral_score 总和**: {s['total_viral_score']:,}",
        f"- **平均 viral_score / 账号**: {s['avg_viral_per_author']:.0f}",
        "",
        "### 爆款次数分布",
        "",
        "| 区间 | 账号数 |",
        "|---|---|",
        f"| 仅 1 爆款 | {analysis['burst_distribution']['1_爆款']} |",
        f"| 2-3 爆款 | {analysis['burst_distribution']['2_3_爆款']} |",
        f"| 4+ 爆款 (头部) | {analysis['burst_distribution']['4+_爆款']} |",
        "",
        "### 头部 vs 长尾 (Top 10% 账号贡献)",
        "",
        f"- **Top 10% ({analysis['head_tail']['top10pct_accounts']} 个账号)**: 贡献 {analysis['head_tail']['top10pct_viral_share']}% viral_score",
        f"- **其余 {analysis['head_tail']['rest_accounts']} 个账号**: 贡献 {analysis['head_tail']['rest_viral_share']}%",
        "",
        "---",
        "",
        f"## 🏆 Top {len(analysis['ranking'])} 账号榜单 (按 viral_score 总和)",
        "",
        "| 排名 | 昵称 | 爆款数 | viral_score 总 | 总点赞 | 跨关键词 | 高频标签 |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, e in enumerate(analysis["ranking"], 1):
        top_tags = " / ".join(t for t, _ in e["tags"].most_common(3))
        cross = "✅" if len(e["keywords"]) >= 2 else ""
        kw_count = len(e["keywords"])
        lines.append(
            f"| {i} | {e['nickname']} | {len(e['notes'])} | {int(e['viral_score_total']):,} | {e['total_likes']:,} | {cross} ({kw_count}) | {top_tags or '-'} |"
        )
    lines += [
        "",
        "---",
        "",
        "## 🔀 跨关键词操盘手 (≥2 关键词下都爆款)",
        "",
    ]
    if not analysis["cross_keyword"]:
        lines.append("_无_ — 多数账号专注于单关键词")
    else:
        lines.append("| 账号 | 覆盖关键词 | 爆款数 | viral_score |")
        lines.append("|---|---|---|---|")
        for e in analysis["cross_keyword"][:10]:
            kws = " / ".join(e["keywords"].keys())
            lines.append(f"| {e['nickname']} | {kws} | {len(e['notes'])} | {int(e['viral_score_total']):,} |")
    lines += [
        "",
        "---",
        "",
        "## 🔬 单账号内容拆解 (Top 5)",
        "",
    ]
    for i, e in enumerate(analysis["ranking"][:5], 1):
        kw_list = list(e["keywords"].keys())
        kw_str = ", ".join(kw_list) if kw_list else "-"
        titles = [n.get("title", "?") for n in e["notes"]]
        title_kws = extract_title_keywords(titles, top_n=5)
        lines += [
            f"### {i}. {e['nickname']}",
            "",
            f"- **覆盖关键词**: {kw_str}",
            f"- **爆款数 / viral_score 总 / 总点赞**: {len(e['notes'])} / {int(e['viral_score_total']):,} / {e['total_likes']:,}",
            f"- **内容主题 (从标题抽)**: {', '.join(title_kws) if title_kws else '-'}",
            f"- **代表作品** ({min(3, len(titles))} 条):",
        ]
        for t in titles[:3]:
            lines.append(f"  - {t}")
        lines.append("")
    lines += [
        "---",
        "",
        "## 💡 洞察 & 建议",
        "",
    ]
    # 自动洞察 (#41: total_acc > 0 守卫 → 避免 ZeroDivisionError)
    insights: list[str] = []
    bt = analysis["burst_distribution"]
    total_acc = s["n_authors"]
    if total_acc > 0:
        if bt["4+_爆款"] / total_acc > 0.1:
            insights.append(f"- **头部集中**: {bt['4+_爆款']} 个账号 ({(bt['4+_爆款']/total_acc*100):.0f}%) 贡献 4+ 爆款, 强者恒强")
        if analysis["head_tail"]["top10pct_viral_share"] > 50:
            insights.append(f"- **头部马太效应**: Top 10% 账号独占 {analysis['head_tail']['top10pct_viral_share']}% viral_score, 关注头部能事半功倍")
        if analysis["cross_keyword"]:
            insights.append(f"- **跨领域操盘手**: {len(analysis['cross_keyword'])} 个账号在 ≥2 关键词下爆款, 他们是行业**方法论级**选手, 优先对标")
        if bt["1_爆款"] / total_acc > 0.7:
            insights.append(f"- **长尾海量化**: {bt['1_爆款']} 个账号 ({(bt['1_爆款']/total_acc*100):.0f}%) 只 1 条爆款, 流量分散")
    else:
        insights.append("- ⚠️ 未识别到账号 (n_authors=0) — 检查输入 JSON 字段名 (notes / data / viral_notes / results)")
    if not insights:
        insights.append("- 数据规模较小, 洞察有限")
    lines.extend(insights)
    lines.append("")
    lines.append("> ⚠️ **MVP 模式限制**: 本报告基于 scanner MVP 模式 (无粉丝数), 仅做了**内容策略维度**分析。")
    lines.append("> 要做「账号增长曲线 / 粉丝画像」等深度拆解, 需跑 `scanner.py --full` 抓粉丝 (有 captcha 风险)。")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description="Skill 1.x 账号拆解 (Step ④)")
    p.add_argument("--viral-json", required=True, help="scanner 输出的 viral JSON")
    p.add_argument("--label", default="", help="输出文件 label (默认用 viral 文件名 stem)")
    p.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = p.parse_args()

    viral_path = Path(args.viral_json)
    label = args.label or viral_path.stem
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Skill 1.x account-analyzer v0.1.0 ===")
    print(f"viral: {viral_path}")
    print(f"out:   {out_dir}")

    notes = load_viral(viral_path)
    print(f"  ✓ 加载 {len(notes)} 条 viral notes")

    by_author = aggregate_by_author(notes)
    print(f"  ✓ 聚合 {len(by_author)} 个唯一账号")

    analysis = analyze(by_author)
    s = analysis["summary"]
    print(f"  ✓ 分析: {s['n_authors']} 账号 / {s['n_notes']} 爆款 / viral 总和 {s['total_viral_score']:,}")

    date_str = datetime.now().strftime("%Y%m%d")
    md_path = out_dir / f"{date_str}-{label}-accounts.md"
    json_path = out_dir / f"{date_str}-{label}-accounts.json"
    write_markdown(md_path, analysis, viral_path)
    json_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ {md_path}")
    print(f"  ✓ {json_path}")

    print(f"\n=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
