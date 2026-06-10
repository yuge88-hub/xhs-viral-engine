"""run_top5_cover_bench.py — 任务 20: 补 cover_analyzer + benchmark_check 各 5 条.

复用 scored-full.json 拿 Top 5, 对每条:
  1. cover_analyzer.py --note-id --xsec-token --out-dir
  2. benchmark_check.py --note-id --out-dir  (依赖 analysis.json 已在)
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path("output/ai-knowledge-base")
SRC = json.loads((ROOT / "scored-full.json").read_text(encoding="utf-8"))
results = sorted(SRC["results"], key=lambda r: r["viral_score"], reverse=True)[:5]

PYTHON = sys.executable
ENV = {**os.environ, "PYTHONPATH": "skills"}


def run(cmd: list[str], log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        r = subprocess.run(cmd, env=ENV, stdout=f, stderr=subprocess.STDOUT, text=True, encoding="utf-8")
    return r.returncode


def nick_safe(r: dict, i: int) -> str:
    s = "".join(c for c in r["author"]["nickname"] if c.isalnum() or c in "._- ")[:20].strip()
    return s or f"author{i}"


def main() -> int:
    for i, r in enumerate(results, 1):
        nick = nick_safe(r, i)
        out_dir = ROOT / "skill-1.5-top5" / f"rank{i}-{nick}"
        note_id = r["note_id"]
        token = r["xsec_token"]
        print(f"\n=== [{i}/5] rank{i} {nick} | viral={r['viral_score']:.2f} ===")

        # 1. cover_analyzer
        rc = run([PYTHON, "skills/skill-1.5-viral-analyzer/cover_analyzer.py",
                  "--note-id", note_id, "--xsec-token", token,
                  "--out-dir", str(out_dir),
                  "--skip-llm"],
                 out_dir / "cover.log")
        print(f"  cover_analyzer: rc={rc}")

        # 2. benchmark_check (依赖 analysis.json)
        rc = run([PYTHON, "skills/skill-1.5-viral-analyzer/benchmark_check.py",
                  "--note-id", note_id,
                  "--out-dir", str(out_dir),
                  "--target-audience", "25-35 AI 知识工作者 / 笔记控 / 副业新手",
                  "--target-action", "涨粉到 1W / 私域引流 AI Skill 课程"],
                 out_dir / "bench.log")
        print(f"  benchmark_check: rc={rc}")

    print("\n=== 5/5 cover + benchmark done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
