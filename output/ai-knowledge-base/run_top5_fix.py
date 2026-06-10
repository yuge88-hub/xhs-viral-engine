"""run_top5_fix.py — AI 知识库 Top 5 真拆 (复用 children-height 模板, 改 ROOT/SRC)

读 scored-full.json 拿 Top 5 (已按 viral 排, 保险起见再排一次), 5 条串行:
  - viral_analyzer (LLM 4问+6维 DeepSeek)
  - pain_miner (--input/--out web 路径, 单 note JSON)
benchmark_check 在后面单独并行跑.
"""
from __future__ import annotations
from skills._bootstrap import *  # noqa: F401,F403  ← UTF-8 项目级基线

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("output/ai-knowledge-base")
SRC = json.loads((ROOT / "scored-full.json").read_text(encoding="utf-8"))
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

        print(f"\n=== [{i}/5] {rank} {nick_safe} | viral={r['viral_score']:.2f} | likes={r['metrics']['likes']:,} ===")

        # 1. viral_analyzer (不 skip-llm, 跑 DeepSeek 4问+6维)
        rc = run([PYTHON, "skills/skill-1.5-viral-analyzer/viral_analyzer.py",
                  "--note-id", note_id, "--xsec-token", token,
                  "--out-dir", str(out_dir)],  # 不带 --skip-llm
                 out_dir / "viral_fix.log")
        print(f"  viral_analyzer (LLM): rc={rc}")

        # 2. pain_miner (用 --input + --out, web 路径)
        # 写单 note JSON 给 --input (pain_miner 需要 results 数组)
        single_note_json = pain_dir / "_input_note.json"
        pain_dir.mkdir(parents=True, exist_ok=True)
        single_note_json.write_text(
            json.dumps({"results": [{
                "note_id": note_id,
                "xsec_token": token,
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "author": r.get("author", {}),
                "metrics": r.get("metrics", {}),
            }]}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        rc = run([PYTHON, "skills/xhs-comment-pain-miner/pain_miner.py",
                  "--input", str(single_note_json),
                  "--out", str(pain_dir / "pains.json"),
                  "--use-web", "--output", "json",
                  "--min-likes", "1", "--top-per-note", "10",
                  "--exclude-author"],
                 pain_dir / "pain_fix.log")
        print(f"  pain_miner (web): rc={rc}")

    print("\n=== Top 5 deep dive done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
