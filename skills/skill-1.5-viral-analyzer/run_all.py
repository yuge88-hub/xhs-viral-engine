"""
run_all.py — Skill 1.5 端到端封装

顺序跑 3 个子技能:
  1. viral_analyzer.py  → {note_id}-4问+6维.md + analysis.json
  2. cover_analyzer.py  → {note_id}-cover.png + cover.json
  3. benchmark_check.py → {note_id}-benchmark.json (含 4 标准对标)

失败不阻断: 哪个失败都继续下一个, 最后汇总。

用法:
    python run_all.py --note-id <id> --xsec-token <token> \
                      --target-audience "25-35 宝妈 + AI 副业新手" \
                      --target-action "涨粉到 1W"
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SKILL_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = SKILL_DIR.parents[2] / "output" / "skill-1.5-viral-analyzer-v0.1"


def run_step(label: str, script: str, args: list[str]) -> bool:
    """跑一个子脚本, 失败打印 + 返回 False (不抛)"""
    print(f"\n>>> {label} ({script})")
    print(f"    args: {' '.join(args)}")
    cmd = [sys.executable, str(SKILL_DIR / script), *args]
    try:
        result = subprocess.run(cmd, cwd=SKILL_DIR)
        ok = result.returncode == 0
        print(f"    {'✅' if ok else '❌'} exit code: {result.returncode}")
        return ok
    except Exception as e:
        print(f"    ❌ 启动失败: {e}", file=sys.stderr)
        return False


def main() -> int:
    p = argparse.ArgumentParser(
        description="Skill 1.5 端到端: viral + cover + benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--note-id", required=True, help="xhs note_id")
    p.add_argument("--xsec-token", required=True, help="xhs xsec_token (从 Skill 1 scanner 拿)")
    p.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--target-audience", default="", help="(可选) 你的目标人群, e.g. '25-35 宝妈 + AI 副业新手'")
    p.add_argument("--target-action", default="", help="(可选) 你的目标动作, e.g. '涨粉到 1W'")
    p.add_argument("--skip-llm", action="store_true", help="跳过 DeepSeek LLM (只跑规则)")
    p.add_argument("--cookies-file", default="", help="(可选) Chrome Cookie-Editor 导出的 cookies")
    p.add_argument("--only", choices=["viral", "cover", "benchmark"], default="",
                   help="只跑某个 step (默认 3 个都跑)")
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Skill 1.5 viral-analyzer v0.1.0 (端到端) ===")
    print(f"note_id:  {args.note_id}")
    print(f"out_dir:  {out_dir}")
    if args.target_audience:
        print(f"audience: {args.target_audience}")
    if args.target_action:
        print(f"action:   {args.target_action}")
    if args.skip_llm:
        print(f"LLM:      跳过 (--skip-llm)")

    # 公共参数
    common = [
        "--note-id", args.note_id,
        "--xsec-token", args.xsec_token,
        "--out-dir", str(out_dir),
    ]
    if args.skip_llm:
        common.append("--skip-llm")
    if args.cookies_file:
        common.extend(["--cookies-file", args.cookies_file])

    # 但 benchmark_check 不需要 xsec-token (它只读 analysis.json)
    # 而且它需要 --target-audience / --target-action
    benchmark_args = [
        "--note-id", args.note_id,
        "--out-dir", str(out_dir),
    ]
    if args.target_audience:
        benchmark_args.extend(["--target-audience", args.target_audience])
    if args.target_action:
        benchmark_args.extend(["--target-action", args.target_action])

    # 跑 step
    results = {}
    if not args.only or args.only == "viral":
        results["viral"] = run_step("Step 1/3 拆爆款 4问+6维", "viral_analyzer.py", common)
    if not args.only or args.only == "cover":
        results["cover"] = run_step("Step 2/3 封面分析", "cover_analyzer.py", common)
    if not args.only or args.only == "benchmark":
        results["benchmark"] = run_step("Step 3/3 4 标准对标", "benchmark_check.py", benchmark_args)

    # 汇总
    print(f"\n=== 汇总 ===")
    for step, ok in results.items():
        print(f"  {'✅' if ok else '❌'} {step}")

    # 列出输出文件
    print(f"\n=== 产物 (在 {out_dir}) ===")
    files = sorted(out_dir.glob(f"{args.note_id}*"))
    for f in files:
        size = f.stat().st_size
        size_str = f"{size / 1024:.1f} KB" if size < 1024 * 1024 else f"{size / 1024 / 1024:.1f} MB"
        print(f"  {f.name}  ({size_str})")

    all_ok = all(results.values())
    print(f"\n=== {'全部完成' if all_ok else '部分失败'} ===")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
