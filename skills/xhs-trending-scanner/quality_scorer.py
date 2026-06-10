#!/usr/bin/env python3
"""quality_scorer — 对 scanner 输出做"标准化爆款评估"。

为什么需要：scanner MVP 模式只按 likes 排序，但"是不是爆款"要结合：
1. **互动率**：collect/like (收藏率, 干货指标) / comment/like (共鸣率) / share/like (传播率)
2. **时间衰减**：越近发布的爆款价值越高（窗口期）
3. **多维加权**：单一指标不靠谱，用多维加权算出"真爆款分"

输入：scanner.py 输出的 JSON
输出：在原 results 数组每个 item 加 `quality` 字段，重新排序

Usage:
  python quality_scorer.py <scanner.json> [--out <new.json>] [--top N]
"""
from __future__ import annotations
from skills._bootstrap import *  # noqa: F401,F403  ← UTF-8 项目级基线 (CONVENTIONS #17)

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

# 终端 UTF-8 — 由 skills._bootstrap 项目级基线处理 (CONVENTIONS #17)


# ---------- 互动率阈值 (xhs 行业经验) ----------
COLLECT_RATE_DRY_GOODS = 0.8   # 收藏/点赞 > 0.8 算 "干货爆款"
COLLECT_RATE_NORMAL = 0.4      # 0.4-0.8 算 "常规爆款"
SHARE_RATE_VIRAL = 0.15        # 分享/点赞 > 0.15 算 "传播性强"
COMMENT_RATE_ENGAGE = 0.03     # 评论/点赞 > 0.03 算 "高共鸣"
RECENT_DAYS_HOT = 30           # 30 天内算 "热" (窗口期)
RECENT_DAYS_WARM = 90          # 90 天内算 "温"


# ---------- publish_time 解析 (scanner 输出是 "2024-06-14" 或 "05-24" 或 "04-21") ----------

def parse_publish_time(s: str) -> date | None:
    """把 xhs publish_time 转 date。格式可能是:
    - "2024-06-14" 完整日期
    - "05-24" 当年 MM-DD (假设当年)
    - "2024-11" 只到月
    """
    if not s:
        return None
    s = s.strip()
    # 完整日期
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    # 当年 MM-DD
    m = re.match(r"^(\d{2})-(\d{2})$", s)
    if m:
        try:
            return date(date.today().year, int(m.group(1)), int(m.group(2)))
        except ValueError:
            return None
    # 只到月 YYYY-MM
    m = re.match(r"^(\d{4})-(\d{2})$", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), 15)
        except ValueError:
            return None
    return None


def days_since(d: date | None) -> int | None:
    if d is None:
        return None
    return (date.today() - d).days


# ---------- 互动率分维度 ----------

def compute_quality(item: dict) -> dict:
    """给一条 note 算 quality 字段, 返回 {score, tier, rates, freshness}。"""
    m = item.get("metrics") or {}
    likes = max(int(m.get("likes") or 0), 1)
    collects = int(m.get("collects") or 0)
    comments = int(m.get("comments") or 0)
    shares = int(m.get("shares") or 0)

    collect_rate = round(collects / likes, 3)
    comment_rate = round(comments / likes, 3)
    share_rate = round(shares / likes, 3)

    # 维度 1: 互动率 (0-1)
    rate_score = 0.0
    if collect_rate >= COLLECT_RATE_DRY_GOODS:
        rate_score += 0.5
    elif collect_rate >= COLLECT_RATE_NORMAL:
        rate_score += 0.3
    else:
        rate_score += 0.1
    if share_rate >= SHARE_RATE_VIRAL:
        rate_score += 0.3
    else:
        rate_score += share_rate * 2  # 0-0.3 线性
    if comment_rate >= COMMENT_RATE_ENGAGE:
        rate_score += 0.2
    else:
        rate_score += min(comment_rate * 5, 0.15)  # 0-0.15

    # 维度 2: 互动总量 (log scale, 避免 likes 1w 完全压制 1k 的好内容)
    # log10(likes) ∈ [3, 5] (1000~100000) 映射 [0, 1]
    import math
    log_likes = math.log10(max(likes, 1))
    volume_score = max(0.0, min(1.0, (log_likes - 3.0) / 2.0))

    # 维度 3: 时间衰减 (越近越好)
    pub = parse_publish_time(item.get("publish_time") or "")
    age_days = days_since(pub)
    if age_days is None:
        freshness_score = 0.5  # 未知日期给中间值
    elif age_days <= RECENT_DAYS_HOT:
        freshness_score = 1.0
    elif age_days <= RECENT_DAYS_WARM:
        freshness_score = 0.7
    elif age_days <= 365:
        freshness_score = 0.4
    else:
        freshness_score = 0.2

    # 综合分 (0-100)
    # rate 40% + volume 40% + freshness 20%
    total = (rate_score * 0.4 + volume_score * 0.4 + freshness_score * 0.2) * 100
    total = round(total, 2)

    # 分层
    if total >= 70 and collect_rate >= COLLECT_RATE_DRY_GOODS:
        tier = "💎 真爆款"  # 高分 + 干货
    elif total >= 60:
        tier = "🔥 常规爆款"
    elif total >= 40:
        tier = "⚡ 准爆款"
    else:
        tier = "📊 数据平平"

    return {
        "score": total,
        "tier": tier,
        "collect_rate": collect_rate,
        "comment_rate": comment_rate,
        "share_rate": share_rate,
        "rate_score": round(rate_score, 3),
        "volume_score": round(volume_score, 3),
        "freshness_score": round(freshness_score, 3),
        "age_days": age_days,
        "publish_date": pub.isoformat() if pub else None,
    }


def render_quality_summary(payload: dict) -> str:
    """人读版摘要, 给 terminal / 文件头用。"""
    lines = [
        f"# 📊 标准化爆款评估 · {payload['keyword']}",
        "",
        f"- 扫描: **{payload['scanned_notes']}** 条 / 命中: **{payload['viral_count']}** 条",
        f"- 模式: {payload['filter'].get('mode', 'MVP')}",
        f"- 真爆款 (💎): **{payload['quality_summary']['tier_counts'].get('💎 真爆款', 0)}** 条",
        f"- 常规爆款 (🔥): **{payload['quality_summary']['tier_counts'].get('🔥 常规爆款', 0)}** 条",
        f"- 准爆款 (⚡): **{payload['quality_summary']['tier_counts'].get('⚡ 准爆款', 0)}** 条",
        f"- 数据平平 (📊): **{payload['quality_summary']['tier_counts'].get('📊 数据平平', 0)}** 条",
        "",
        "## 🏆 Top 10 (按 quality.score 排序)",
        "",
        "| Rank | Score | Tier | 标题 | 点赞 | 收藏 | 评论 | 分享 | 收藏率 | 分享率 | 发布 |",
        "|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for i, r in enumerate(payload["results"][:10], 1):
        q = r["quality"]
        title = (r["title"] or "").replace("|", "\\|")[:40]
        pub = (r.get("publish_time") or "?")
        if q.get("age_days") is not None:
            pub += f" ({q['age_days']}天前)"
        lines.append(
            f"| {i} | **{q['score']}** | {q['tier']} | {title} "
            f"| {r['metrics']['likes']:,} | {r['metrics']['collects']:,} "
            f"| {r['metrics']['comments']:,} | {r['metrics']['shares']:,} "
            f"| {q['collect_rate']:.2f} | {q['share_rate']:.2f} | {pub} |"
        )

    lines += [
        "",
        "## 🔍 爆款标准说明",
        "",
        f"- **💎 真爆款**: quality.score ≥ 70 **且** 收藏率 ≥ {COLLECT_RATE_DRY_GOODS} (干货)",
        f"- **🔥 常规爆款**: score ≥ 60",
        f"- **⚡ 准爆款**: score ≥ 40",
        f"- **📊 数据平平**: score < 40 (可能赞高但收藏低 = 看热闹; 或赞低但收藏率高 = 潜力股)",
        "",
        "## 📈 综合分公式",
        "",
        "`score = (rate_score × 0.4 + volume_score × 0.4 + freshness_score × 0.2) × 100`",
        "",
        "- **rate_score** (40%): 收藏率 + 分享率 + 评论率 三个子分加和 (0-1)",
        f"  - 收藏率 ≥ {COLLECT_RATE_DRY_GOODS}: 0.5 (干货); ≥ {COLLECT_RATE_NORMAL}: 0.3; 否则 0.1",
        f"  - 分享率 ≥ {SHARE_RATE_VIRAL}: 0.3 (传播); 否则线性 0-0.3",
        f"  - 评论率 ≥ {COMMENT_RATE_ENGAGE}: 0.2 (共鸣); 否则线性 0-0.15",
        "- **volume_score** (40%): `log10(likes) ∈ [3,5] → [0,1]` (避免 1w 赞的 1k 赞被秒杀)",
        "- **freshness_score** (20%): 30天内=1.0 / 90天内=0.7 / 1年内=0.4 / 超1年=0.2",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("input", help="scanner.py 输出的 JSON 文件")
    ap.add_argument("--out", default="-", help="输出 JSON 路径 ('-' 表 stdout)")
    ap.add_argument("--md-out", default="", help="额外输出 markdown 摘要到该路径")
    ap.add_argument("--top", type=int, default=0, help="只保留 quality.score Top N (0=全部)")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"[ERROR] 文件不存在: {src}", file=sys.stderr)
        return 1

    payload = json.loads(src.read_text(encoding="utf-8"))
    results = payload.get("results") or []
    print(f"[quality_scorer] 处理 {len(results)} 条…", file=sys.stderr)

    # 给每条算 quality
    tier_counts: dict[str, int] = {}
    for r in results:
        r["quality"] = compute_quality(r)
        tier = r["quality"]["tier"]
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    # 按 quality.score 重排
    results.sort(key=lambda r: r["quality"]["score"], reverse=True)
    if args.top > 0:
        results = results[:args.top]

    payload["results"] = results
    payload["quality_summary"] = {
        "tier_counts": tier_counts,
        "scoring_formula": "rate×0.4 + volume×0.4 + freshness×0.2",
    }
    payload["skill"] = "xhs-trending-scanner + quality_scorer"
    payload["version"] = "0.1.0"

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out == "-":
        print(text)
    else:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"[quality_scorer] wrote {args.out} ({len(results)} results, 💎={tier_counts.get('💎 真爆款', 0)})", file=sys.stderr)

    if args.md_out:
        Path(args.md_out).write_text(render_quality_summary(payload), encoding="utf-8")
        print(f"[quality_scorer] wrote {args.md_out}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
