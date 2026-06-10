"""run_top5.py — 串行跑 Top 5 素人爆款: Skill 1.5 + pain_miner。

输入: scanner-full.json (按 viral_score 排序的 Top 5)
输出: output/children-height/skill-1.5-top5/{rank}-{nickname}/{note_id}-*.{md,json,png}
       output/children-height/pain-miner-top5/{rank}-{nickname}/pains.json
"""
from __future__ import annotations
from skills._bootstrap import *  # noqa: F401,F403  ← UTF-8 项目级基线

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("output/children-height")
SRC = json.loads((ROOT / "scanner-full.json").read_text(encoding="utf-8"))
results = sorted(SRC["results"], key=lambda r: r["viral_score"], reverse=True)[:5]

PYTHON = sys.executable
ENV = {**__import__("os").environ, "PYTHONPATH": "skills"}


def run(cmd: list[str], log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        r = subprocess.run(cmd, env=ENV, stdout=f, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    return r.returncode


def main() -> int:
    for i, r in enumerate(results, 1):
        rank = f"rank{i}"
        nick_safe = "".join(c for c in r["author"]["nickname"] if c.isalnum() or c in "._- ")[:20]
        nick_safe = nick_safe.strip() or f"author{i}"
        out_dir = ROOT / "skill-1.5-top5" / f"{rank}-{nick_safe}"
        pain_dir = ROOT / "pain-miner-top5" / f"{rank}-{nick_safe}"
        note_id = r["note_id"]
        token = r["xsec_token"]

        print(f"\n=== [{i}/5] {rank} {nick_safe} | viral={r['viral_score']:.2f} | fans={r['author']['fans']} | {r['title'][:30]} ===")

        # 1. Skill 1.5 viral_analyzer
        rc = run([PYTHON, "skills/skill-1.5-viral-analyzer/viral_analyzer.py",
                  "--note-id", note_id, "--xsec-token", token,
                  "--out-dir", str(out_dir), "--skip-llm"],
                 out_dir / "viral.log")
        print(f"  viral_analyzer: rc={rc}")

        # 2. Skill 1.5 cover_analyzer
        rc = run([PYTHON, "skills/skill-1.5-viral-analyzer/cover_analyzer.py",
                  "--note-id", note_id, "--xsec-token", token,
                  "--out-dir", str(out_dir), "--skip-llm"],
                 out_dir / "cover.log")
        print(f"  cover_analyzer: rc={rc}")

        # 3. Skill 1.5 benchmark_check
        rc = run([PYTHON, "skills/skill-1.5-viral-analyzer/benchmark_check.py",
                  "--note-id", note_id, "--out-dir", str(out_dir)],
                 out_dir / "benchmark.log")
        print(f"  benchmark_check: rc={rc}")

        # 4. pain_miner (web 抓, 5s/note)
        rc = run([PYTHON, "skills/xhs-comment-pain-miner/pain_miner.py",
                  "--note-id", note_id, "--xsec-token", token,
                  "--output-dir", str(pain_dir)],
                 pain_dir / "pain_miner.log")
        print(f"  pain_miner: rc={rc}")

    print("\n=== All 5 done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
