"""
benchmark_check.py — Skill 1.5 对标评估 (4 标准)

输入: viral_analyzer 输出的 analysis.json (含 meta)
输出: {note_id}-benchmark.json — 4 标准评分 + 总评

4 标准 (新方法论):
1. 素人爆款 (low follower, high engagement)
2. 结构清晰 (4问+6维都填充完整)
3. 人群一致 (基于 self 目标人群对比, 需 user input)
4. 目标一致 (基于 self 目标动作对比, 需 user input)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests  # noqa: F401  -- 备用, 实际在函数内按需 import

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "skill-1.5-viral-analyzer-v0.1"


# ============================================================
# 4 标准评分
# ============================================================

def score_素人(meta: dict[str, Any]) -> dict[str, Any]:
    """素人爆款: 粉丝 < 5万 + 互动率 (likes/粉丝) > 10%

    评分 0-1:
    - 1.0: <1万粉 + 互动 > 50%
    - 0.7: <5万粉 + 互动 > 10%
    - 0.4: <10万粉 + 互动 > 5%
    - 0.0: >50万粉 (大 V)
    """
    fans = meta.get("fans") or 0
    likes = meta.get("likes") or 0
    if fans == 0:
        return {"score": 0.5, "reason": "粉丝数未抓到, 无法判断", "fans": fans, "likes": likes}

    engagement = likes / fans

    if fans < 10000 and engagement > 0.5:
        score = 1.0
        reason = f"🎯 强素人爆款: {fans} 粉 + {engagement:.1%} 互动率"
    elif fans < 50000 and engagement > 0.1:
        score = 0.7
        reason = f"✅ 素人爆款: {fans} 粉 + {engagement:.1%} 互动率"
    elif fans < 100000 and engagement > 0.05:
        score = 0.4
        reason = f"⚠️ 中等: {fans} 粉 + {engagement:.1%} 互动率"
    elif fans > 500000:
        score = 0.0
        reason = f"❌ 大 V 流量: {fans} 粉, 内容本身可能不关键"
    else:
        score = 0.3
        reason = f"普通: {fans} 粉 + {engagement:.1%} 互动率"

    return {"score": score, "reason": reason, "fans": fans, "engagement": round(engagement, 4)}


def score_结构(analysis: dict[str, Any]) -> dict[str, Any]:
    """结构清晰: 4 问 + 6 维都填充完整 (规则评分)"""
    q_count = sum(1 for v in analysis.get("4_questions", {}).values() if v.get("content"))
    d_count = sum(1 for v in analysis.get("6_dimensions", {}).values() if v)

    q_score = q_count / 4  # 满分 4
    d_score = d_count / 6  # 满分 6
    total = (q_score + d_score) / 2

    if total >= 0.9:
        reason = f"✅ 拆解完整: 4 问 {q_count}/4, 6 维 {d_count}/6"
    elif total >= 0.6:
        reason = f"⚠️ 拆解较完整: 4 问 {q_count}/4, 6 维 {d_count}/6"
    else:
        reason = f"❌ 拆解不全: 4 问 {q_count}/4, 6 维 {d_count}/6"

    return {
        "score": round(total, 2),
        "reason": reason,
        "q_filled": q_count,
        "d_filled": d_count,
    }


def score_人群(analysis: dict[str, Any], target_audience: str = "") -> dict[str, Any]:
    """人群一致: LLM 对比 self.target_audience vs note 的人群画像

    target_audience 由用户传 (e.g. "25-35 宝妈 + AI 副业新手")
    """
    reader = analysis.get("6_dimensions", {}).get("reader_profile", "")
    if not target_audience:
        return {
            "score": 0.5,
            "reason": "未指定目标人群, 跳过对比",
            "note_audience": reader[:200],
        }
    if not reader:
        return {
            "score": 0.5,
            "reason": "笔记人群画像未抓到, 无法对比",
            "note_audience": "",
        }

    # 走 DeepSeek
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return {
            "score": 0.5,
            "reason": "DeepSeek API 未配置, 跳过 LLM 对比",
            "note_audience": reader[:200],
        }

    prompt = f"""判断下面两个画像的匹配度(0-1):
- 我的目标人群: {target_audience}
- 笔记实际人群: {reader}

只回答一个数字(0-1, 1=完全匹配)和 1 句话理由。
"""
    try:
        r = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 100,
                "temperature": 0.1,
            },
            timeout=30,
        )
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
        score_m = re.search(r"([0-9]+\.?[0-9]*)", text)
        score = float(score_m.group(1)) if score_m else 0.5
        score = max(0.0, min(1.0, score))
        return {
            "score": score,
            "reason": text.strip(),
            "note_audience": reader[:200],
            "target_audience": target_audience,
        }
    except Exception as e:
        return {"score": 0.5, "reason": f"LLM 调用失败: {e}", "note_audience": reader[:200]}


def score_目标(analysis: dict[str, Any], target_action: str = "") -> dict[str, Any]:
    """目标一致: LLM 对比 self.target_action (关注/收藏/购买) vs note 的 CTA"""
    where = analysis.get("4_questions", {}).get("where_lead", {}).get("content", "")
    if not target_action:
        return {
            "score": 0.5,
            "reason": "未指定目标动作, 跳过对比",
            "note_cta": where[:200],
        }
    if not where:
        return {"score": 0.5, "reason": "笔记 CTA 未抓到, 无法对比", "note_cta": ""}

    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return {"score": 0.5, "reason": "DeepSeek API 未配置, 跳过 LLM 对比", "note_cta": where[:200]}

    prompt = f"""判断下面两个动作的匹配度(0-1):
- 我的目标动作: {target_action}
- 笔记实际 CTA: {where}

只回答一个数字(0-1, 1=完全匹配)和 1 句话理由。
"""
    try:
        r = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 100,
                "temperature": 0.1,
            },
            timeout=30,
        )
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
        score_m = re.search(r"([0-9]+\.?[0-9]*)", text)
        score = float(score_m.group(1)) if score_m else 0.5
        score = max(0.0, min(1.0, score))
        return {
            "score": score,
            "reason": text.strip(),
            "note_cta": where[:200],
            "target_action": target_action,
        }
    except Exception as e:
        return {"score": 0.5, "reason": f"LLM 调用失败: {e}", "note_cta": where[:200]}


# ============================================================
# Main
# ============================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Skill 1.5 benchmark-check — 4 标准对标评估")
    parser.add_argument("--note-id", required=True, help="viral_analyzer 输出的 note_id")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--target-audience", default="", help="你的目标人群 (e.g. '25-35 宝妈 + AI 副业新手')")
    parser.add_argument("--target-action", default="", help="你的目标动作 (e.g. '涨粉到 1W' / '私域引流' / '卖 9.9 课程')")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    analysis_path = out_dir / f"{args.note_id}-analysis.json"

    if not analysis_path.exists():
        print(f"ERROR: {analysis_path} 不存在, 先跑 viral_analyzer.py", file=sys.stderr)
        return 1

    print(f"\n=== Skill 1.5 benchmark-check v0.1.0 ===")
    print(f"note_id: {args.note_id}\n")

    analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    meta = analysis.get("meta", {})

    # 1. 素人
    print(">>> 标准 1: 素人爆款")
    s1 = score_素人(meta)
    print(f"  评分: {s1['score']} — {s1['reason']}")

    # 2. 结构
    print(">>> 标准 2: 结构清晰")
    s2 = score_结构(analysis)
    print(f"  评分: {s2['score']} — {s2['reason']}")

    # 3. 人群
    print(">>> 标准 3: 人群一致")
    s3 = score_人群(analysis, args.target_audience)
    print(f"  评分: {s3['score']} — {s3['reason'][:80]}")

    # 4. 目标
    print(">>> 标准 4: 目标一致")
    s4 = score_目标(analysis, args.target_action)
    print(f"  评分: {s4['score']} — {s4['reason'][:80]}")

    # 总评
    weights = {"素人": 0.3, "结构": 0.2, "人群": 0.25, "目标": 0.25}
    total = (
        s1["score"] * weights["素人"]
        + s2["score"] * weights["结构"]
        + s3["score"] * weights["人群"]
        + s4["score"] * weights["目标"]
    )
    recommendation = (
        "✅ 强推荐对标" if total >= 0.7
        else "⚠️ 可参考" if total >= 0.5
        else "❌ 不建议对标"
    )

    print(f"\n=== 总评 ===")
    print(f"  加权总分: {total:.2f}")
    print(f"  建议: {recommendation}")

    # 落盘
    benchmark = {
        "skill": "skill-1.5-benchmark-check",
        "version": "0.1.0",
        "note_id": args.note_id,
        "target_audience": args.target_audience,
        "target_action": args.target_action,
        "scores": {
            "素人": s1,
            "结构": s2,
            "人群": s3,
            "目标": s4,
        },
        "weights": weights,
        "total_score": round(total, 2),
        "recommendation": recommendation,
    }
    out_path = out_dir / f"{args.note_id}-benchmark.json"
    out_path.write_text(json.dumps(benchmark, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  ✓ {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
