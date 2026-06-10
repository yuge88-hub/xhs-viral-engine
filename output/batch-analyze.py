"""
batch_analyze.py — 批量分析 5 个爆款账号的代表爆款

从 output/batch-full-5kw/viral-<keyword>.json 挑前 N 个不同账号的代表爆款,
逐个跑 viral_analyzer + cover_analyzer + reverse_prompt (Skill 1.5 + Skill 4 v0.5)

防 captcha: per-note 隔离 + 5-8s 随机延迟

用法:
    python output/batch-analyze.py --keyword "AI 副业" --top 5
"""
from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VIRAL_JSON = PROJECT_ROOT / "output" / "batch-full-5kw" / "viral-{keyword}.json"
PAIN_JSON = PROJECT_ROOT / "output" / "batch-full-5kw" / "pain-miner-{keyword}.json"
SKILL_DIR = PROJECT_ROOT / "skills" / "skill-1.5-viral-analyzer"
REWRITER_DIR = PROJECT_ROOT / "skills" / "skill-4-viral-rewriter"


def keyword_to_filename(kw: str) -> str:
    return kw.replace(" ", "_")


def pick_unique_authors(viral: list[dict], top: int) -> list[dict]:
    """挑 top N 个不同 user_id 的代表爆款 (按 viral_score 排序)"""
    seen = set()
    picked = []
    for note in viral:
        uid = note.get("author", {}).get("user_id")
        if uid and uid not in seen:
            seen.add(uid)
            picked.append(note)
            if len(picked) >= top:
                break
    return picked


def run_step(label: str, cmd: list[str], cwd: Path) -> bool:
    """跑一个子命令, 失败不抛"""
    print(f"\n>>> {label}")
    print(f"    {' '.join(cmd[:5])}...")
    try:
        r = subprocess.run(cmd, cwd=cwd)
        ok = r.returncode == 0
        print(f"    {'✅' if ok else '❌'} exit: {r.returncode}")
        return ok
    except Exception as e:
        print(f"    ❌ {e}", file=sys.stderr)
        return False


def main() -> int:
    p = argparse.ArgumentParser(description="批量跑 5 个爆款账号的 Skill 1.5 + Skill 4 流水线")
    p.add_argument("--keyword", required=True, help='关键词, e.g. "AI 副业"')
    p.add_argument("--top", type=int, default=5, help="挑前 N 个不同账号")
    p.add_argument("--sleep-min", type=float, default=5.0, help="每账号间最小延迟 (秒)")
    p.add_argument("--sleep-max", type=float, default=8.0, help="每账号间最大延迟 (秒)")
    p.add_argument("--skip-llm", action="store_true", help="跳过 LLM (auto-fill / 4问6维)")
    p.add_argument("--include-reverse", action="store_true", default=True, help="跑 reverse_prompt (默认开)")
    args = p.parse_args()

    # 1. 读 viral JSON
    viral_path = VIRAL_JSON.with_name(VIRAL_JSON.name.format(keyword=keyword_to_filename(args.keyword)))
    if not viral_path.exists():
        print(f"ERROR: {viral_path} 不存在", file=sys.stderr)
        return 1
    viral = json.loads(viral_path.read_text(encoding="utf-8"))
    print(f"=== 批量分析: '{args.keyword}' (从 {len(viral)} 条爆款里挑 top {args.top} 不同账号) ===\n")

    # 2. 挑 top N 账号
    picked = pick_unique_authors(viral, args.top)
    print(f"挑中 {len(picked)} 个账号:")
    for i, n in enumerate(picked, 1):
        auth = n.get("author", {}).get("nickname", "?")
        m = n.get("metrics", {})
        print(f"  {i}. {auth} — 点赞 {m.get('likes', '?')}, 收藏 {m.get('collects', '?')} — {n.get('title', '?')[:50]}")

    # 3. pain (可选)
    pain_path = PAIN_JSON.with_name(PAIN_JSON.name.format(keyword=keyword_to_filename(args.keyword)))
    pain_arg = ["--pains", str(pain_path)] if pain_path.exists() else []
    if pain_path.exists():
        print(f"\npain 钩子源: {pain_path.name}")
    else:
        print(f"\n(pain 钩子: 无 — {pain_path.name} 不存在)")

    # 4. 逐账号跑
    results = []
    for i, note in enumerate(picked, 1):
        note_id = note["note_id"]
        xsec_token = note["xsec_token"]
        auth = note.get("author", {}).get("nickname", "?")
        print(f"\n{'='*70}")
        print(f"[{i}/{len(picked)}] {auth} ({note_id})")
        print(f"{'='*70}")

        step_ok = {"viral": False, "cover": False, "reverse": False}

        # 4a. viral_analyzer
        cmd = [
            sys.executable, str(SKILL_DIR / "viral_analyzer.py"),
            "--note-id", note_id,
            "--xsec-token", xsec_token,
        ]
        if args.skip_llm:
            cmd.append("--skip-llm")
        step_ok["viral"] = run_step(f"Step A: viral_analyzer.py", cmd, cwd=SKILL_DIR)

        # 4b. cover_analyzer
        cmd = [
            sys.executable, str(SKILL_DIR / "cover_analyzer.py"),
            "--note-id", note_id,
            "--xsec-token", xsec_token,
        ]
        if args.skip_llm:
            cmd.append("--skip-llm")
        step_ok["cover"] = run_step(f"Step B: cover_analyzer.py", cmd, cwd=SKILL_DIR)

        # 4c. reverse_prompt (用 viral 输出的 analysis.json)
        if args.include_reverse:
            cmd = [
                sys.executable, str(REWRITER_DIR / "reverse_prompt.py"),
                "--note-id", note_id,
            ]
            if pain_arg:
                cmd.extend(pain_arg)
            step_ok["reverse"] = run_step(f"Step C: reverse_prompt.py", cmd, cwd=REWRITER_DIR)

        results.append({
            "rank": i,
            "note_id": note_id,
            "title": note.get("title", "?"),
            "author": auth,
            "metrics": note.get("metrics", {}),
            "steps_ok": step_ok,
        })

        # 防 captcha: 5-8s 随机延迟 (POSTMORTEM 防 captcha 手册)
        if i < len(picked):
            sleep_s = random.uniform(args.sleep_min, args.sleep_max)
            print(f"\n  ⏱  sleep {sleep_s:.1f}s (防 captcha)")
            time.sleep(sleep_s)

    # 5. 汇总
    print(f"\n{'='*70}")
    print(f"=== 批量汇总 ===")
    print(f"{'='*70}\n")
    print(f"{'#':<3} {'作者':<20} {'点赞':<8} {'viral':<6} {'cover':<6} {'reverse':<8} {'标题'}")
    print("-" * 100)
    for r in results:
        m = r["metrics"]
        v = "✅" if r["steps_ok"]["viral"] else "❌"
        c = "✅" if r["steps_ok"]["cover"] else "❌"
        rv = "✅" if r["steps_ok"]["reverse"] else "❌"
        print(f"{r['rank']:<3} {r['author'][:18]:<20} {m.get('likes', '?'):<8} {v:<6} {c:<6} {rv:<8} {r['title'][:50]}")

    all_ok = all(all(r["steps_ok"].values()) for r in results)
    print(f"\n{'全部 ✅' if all_ok else '部分 ❌'} — {sum(all(r['steps_ok'].values()) for r in results)}/{len(results)*3} 步骤成功")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
