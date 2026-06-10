#!/usr/bin/env python3
"""batch-keyword-pipeline — Skill 3: 批量多关键词流水线

Pipeline:
  keywords (CLI 或文件)
  → per keyword:
      scanner.py (Skill 1) → viral notes JSON
  → 合并所有 keyword 的 viral notes (用 --source_keyword 标注)
  → per keyword (captcha 隔离):
      pain_miner.py (Skill 2) on this keyword's notes
  → 输出:
      <out-prefix>-summary.md    (per-keyword stats + 痛点云)
      <out-prefix>-viral.md      (所有 viral notes 合并)
      <out-prefix>-pains.md      (所有痛点合并 + 按关键词分组)
      <out-prefix>-raw.json     (raw data)

用法:
  python run.py --keywords "AI 副业,营养食疗,副业赚钱" --min-likes 500
  python run.py --keywords-file keywords.txt --min-likes 500 --with-pains
  python run.py --keywords "AI 副业" --full --min-likes 5000
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCANNER = ROOT / "skills" / "xhs-trending-scanner" / "scanner.py"
PAIN_MINER = ROOT / "skills" / "xhs-comment-pain-miner" / "pain_miner.py"
DEFAULT_OUT_DIR = ROOT / "output"


def run_subprocess(cmd: list[str], timeout: int = 600) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=timeout,
                           env={"PYTHONIOENCODING": "utf-8", **subprocess.os.environ})
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"timeout after {timeout}s"
    except Exception as e:
        return -1, "", str(e)


def run_scanner(keyword: str, min_likes: int, full_mode: bool, pages: int,
                work_dir: Path) -> dict | None:
    out_path = work_dir / f"scanner-{_safe_filename(keyword)}.json"
    cmd = [
        sys.executable, str(SCANNER), keyword,
        "--min-likes", str(min_likes),
        "--pages", str(pages),
        "--output", "json",
        "--out", str(out_path),
    ]
    if full_mode:
        cmd += ["--require-fans", "--fan-source", "drissionpage",
                "--max-followers", "50000"]
    print(f"  → scanner: {keyword}", file=sys.stderr)
    rc, out, err = run_subprocess(cmd, timeout=900)
    if rc != 0:
        print(f"    ✗ scanner failed (rc={rc}): {err[:200]}", file=sys.stderr)
        return None
    if not out_path.exists():
        return None
    try:
        return json.loads(out_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"    ✗ scanner output invalid JSON: {e}", file=sys.stderr)
        return None


def aggregate_viral(scanner_results: list[tuple[str, dict]]) -> list[dict]:
    combined = []
    for keyword, payload in scanner_results:
        for note in payload.get("results", []):
            n = dict(note)
            n["source_keyword"] = keyword
            combined.append(n)
    return combined


def run_pain_miner_for_keyword(keyword: str, keyword_viral_json: Path,
                                min_likes: int, top_per_note: int,
                                work_dir: Path) -> dict | None:
    """Run Skill 2 on a single keyword's viral notes. Captcha is contained per-keyword."""
    out_path = work_dir / f"pain-miner-{_safe_filename(keyword)}.json"
    cmd = [
        sys.executable, str(PAIN_MINER),
        "--input", str(keyword_viral_json),
        "--min-likes", str(min_likes),
        "--top-per-note", str(top_per_note),
        "--output", "json",
        "--out", str(out_path),
    ]
    print(f"  → pain-miner: {keyword}", file=sys.stderr)
    rc, out, err = run_subprocess(cmd, timeout=1800)
    if rc != 0:
        print(f"    ✗ pain-miner [{keyword}] failed (rc={rc}): {err[:200]}", file=sys.stderr)
        return None
    if not out_path.exists():
        return None
    try:
        return json.loads(out_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"    ✗ pain-miner [{keyword}] invalid JSON: {e}", file=sys.stderr)
        return None


def _safe_filename(s: str) -> str:
    return re.sub(r"[^\w一-鿿\-_]+", "_", s)[:40]


# 改进的中文停用词 (更大)
STOPWORDS = set("""
的 了 是 在 我 你 他 她 它 我们 你们 他们 这 那 一 个 些 不 也 都 还
就 但 和 与 或 没有 没 对 到 从 把 被 让 给 向 为 于 上 下 里 出
有 会 能 可 吗 呢 吧 啊 哦 哈 嗯 哎 啦 呀 么 的 嘛 吧 咯
说 看 想 做 用 来 去 走 听 写 买 卖 吃 喝 玩 学 习 工 作 完
知道 觉得 应该 可能 需要 应该 想 说 喜欢 觉得 自己 自己 我们
时候 现在 去 做 看到 一下 一些 觉得 想 想 说 这种 这样
这个 那个 这么 那么 这样 那样 这些 那些 还是 或者 以及 和
可以 不可以 不行 可以吗 能 能够 想 想问 求 求问 求教
觉 觉得 真的 感觉 说说 说一下 说真的 其实 个人 一人 大家
然后 之后 之前 第一次 一直
么 啦 啊 哦 吧 嗯 啊哈 哈哈哈 哈哈哈
一个 一种 一样 一直 一定 一定 会 一起来
觉得 知道 需要 想要 想让 想想 说 说说
""".split())


def extract_pain_keywords(pain_payload: dict, top_n: int = 30) -> list[tuple[str, int]]:
    counter: Counter = Counter()
    for note in pain_payload.get("per_note", []):
        for c in note.get("top_pains", []):
            text = c.get("content", "")
            # 中文按 [一-鿿]{2,} 拆词, 英文按 [A-Za-z]{3,}
            words = re.findall(r"[一-鿿]{2,}|[A-Za-z]{3,}", text)
            for w in words:
                if w.lower() in STOPWORDS or len(w) < 2:
                    continue
                # 过滤 emoji 等非常规字符
                if any(0xE000 <= ord(ch) <= 0xF8FF for ch in w):  # Private Use Area (emoji)
                    continue
                counter[w] += c.get("likes", 1)  # 用 likes 加权
    return counter.most_common(top_n)


def render_summary(keywords: list[str], scanner_results: list[tuple[str, dict]],
                   pain_payload: dict | None, elapsed: float) -> str:
    lines = [
        f"# 小红书批量关键词分析报告",
        f"",
        f"- 关键词: {len(keywords)} 个 → {', '.join(keywords)}",
        f"- 总耗时: {elapsed:.0f}s",
        f"- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"",
        f"## Per-keyword 概览",
        f"",
        f"| 关键词 | 扫到 | 命中 | 候选作者 | 拿粉丝 | 爆款 |",
        f"|---|---:|---:|---:|---:|---:|",
    ]
    for kw, p in scanner_results:
        if not p:
            lines.append(f"| {kw} | - | - | - | - | ⚠ failed |")
            continue
        f = p.get("filter", {})
        lines.append(
            f"| {kw} | {p.get('scanned_notes', 0)} | {p.get('pre_filter_pass', 0)} "
            f"| {p.get('unique_authors', 0)} | {p.get('fetched_fans', 0)} | {p.get('viral_count', 0)} |"
        )
    lines.append("")

    if pain_payload:
        lines.append(f"## 痛点云 (Top 20, 按 likes 加权)")
        lines.append("")
        kws = extract_pain_keywords(pain_payload, top_n=20)
        if kws:
            max_count = max(c for _, c in kws)
            for word, count in kws:
                bar = "█" * max(1, int(count * 10 / max_count))
                lines.append(f"- **{word}** ({count}) {bar}")
        lines.append("")

        lines.append("## Per-keyword 痛点数")
        lines.append("")
        lines.append("| 关键词 | 笔记 | 评论 | 命中痛点 |")
        lines.append("|---|---:|---:|---:|")
        kw_to_notes: dict[str, list[dict]] = {}
        for n in pain_payload.get("per_note", []):
            kw = n.get("source_keyword") or "(无)"
            kw_to_notes.setdefault(kw, []).append(n)
        for kw, notes in kw_to_notes.items():
            total_comments = sum(n.get("total_comments", 0) for n in notes)
            total_kept = sum(len(n.get("top_pains", [])) for n in notes)
            lines.append(f"| {kw} | {len(notes)} | {total_comments} | {total_kept} |")
        lines.append("")

        lines.append("## 痛点类别分布")
        lines.append("")
        cat_counter: Counter = Counter()
        for n in pain_payload.get("per_note", []):
            for c in n.get("top_pains", []):
                for cat in c.get("categories", []):
                    cat_counter[cat] += 1
        if cat_counter:
            lines.append("| 类别 | 数量 |")
            lines.append("|---|---:|")
            for cat, count in cat_counter.most_common():
                lines.append(f"| {cat} | {count} |")
        lines.append("")

    return "\n".join(lines)


def render_viral_table(combined: list[dict], top_n: int = 30) -> str:
    sorted_notes = sorted(combined, key=lambda n: n.get("viral_score", 0), reverse=True)
    if not sorted_notes:
        return "(无结果)"
    lines = [
        f"# Top {min(top_n, len(sorted_notes))} 低粉爆款 (跨关键词合并)",
        "",
        "| viral | 点赞 | 收藏 | 评论 | 粉丝 | 标题 | 作者 | 关键词 | 链接 |",
        "|---:|---:|---:|---:|---:|---|---|---|---|",
    ]
    for n in sorted_notes[:top_n]:
        title = (n.get("title") or "").replace("|", "\\|")[:50]
        author = n.get("author", {}).get("nickname", "").replace("|", "\\|")
        fans = n.get("author", {}).get("fans")
        fans_str = f"{fans}" if fans is not None else "-"
        kw = n.get("source_keyword", "")
        lines.append(
            f"| {n.get('viral_score', '-')} | {n['metrics']['likes']} | {n['metrics']['collects']} "
            f"| {n['metrics']['comments']} | {fans_str} | {title} | {author} "
            f"| {kw} | [link]({n['url']}) |"
        )
    return "\n".join(lines)


def render_pains_table(pain_payload: dict) -> str:
    if not pain_payload:
        return "(无痛点数据)"
    lines = [
        f"# 全部痛点 (合并 {pain_payload.get('input_notes', 0)} 笔记)",
        "",
    ]
    kw_to_notes: dict[str, list[dict]] = {}
    for n in pain_payload.get("per_note", []):
        kw = n.get("source_keyword") or "(无)"
        kw_to_notes.setdefault(kw, []).append(n)
    for kw, notes in kw_to_notes.items():
        lines.append(f"## 关键词: {kw}")
        lines.append("")
        for note in notes:
            if not note.get("top_pains"):
                continue
            title = (note.get("title") or "")[:50]
            lines.append(f"### {title} (`{note['note_id'][:8]}…`)")
            lines.append("")
            for c in note["top_pains"]:
                cats = "/".join(c.get("categories", []))
                content = c.get("content", "").replace("\n", " ")
                sub = "↪ " if c.get("is_sub") else ""
                lines.append(f"- **{c['likes']}赞** {sub}`[{cats}]` {content}")
                lines.append(f"  — @{c['nickname']} · {c['ip_location']}")
            lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1] if "\n" in __doc__ else "")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--keywords", help="逗号分隔的关键词列表")
    src.add_argument("--keywords-file", help="关键词文件 (一行一个)")
    ap.add_argument("--min-likes", type=int, default=500, help="每条笔记最小点赞")
    ap.add_argument("--pages", type=int, default=1, help="每关键词搜索页数")
    ap.add_argument("--full", action="store_true", help="完整模式 (取作者粉丝, 慢, 可能 captcha)")
    ap.add_argument("--with-pains", action="store_true", default=True, help="同时跑 Skill 2 (默认开)")
    ap.add_argument("--no-pains", dest="with_pains", action="store_false")
    ap.add_argument("--pain-min-likes", type=int, default=5, help="痛点最小点赞")
    ap.add_argument("--pain-top", type=int, default=5, help="每笔记 Top N 痛点")
    ap.add_argument("--sleep", type=float, default=10.0, help="每关键词间隔 (秒), 推荐 8-15s 防 captcha")
    ap.add_argument("--out-prefix", default=None, help="输出文件前缀, 默认 batch-YYYYMMDD-HHMMSS")
    args = ap.parse_args()

    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    else:
        keywords = [k.strip() for k in Path(args.keywords_file).read_text(encoding="utf-8").splitlines()
                    if k.strip() and not k.strip().startswith("#")]
    if not keywords:
        print("no keywords provided", file=sys.stderr)
        return 1
    print(f"[batch] {len(keywords)} keywords: {keywords}", file=sys.stderr)

    DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)
    prefix = args.out_prefix or f"batch-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    work_dir = DEFAULT_OUT_DIR / prefix
    work_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    scanner_results: list[tuple[str, dict]] = []
    for i, kw in enumerate(keywords, 1):
        print(f"\n[{i}/{len(keywords)}] keyword: {kw}", file=sys.stderr)
        payload = run_scanner(kw, args.min_likes, args.full, args.pages, work_dir)
        scanner_results.append((kw, payload))
        if i < len(keywords):
            print(f"  sleeping {args.sleep}s…", file=sys.stderr)
            time.sleep(args.sleep)

    combined = aggregate_viral(scanner_results)
    print(f"\n[batch] combined {len(combined)} viral notes", file=sys.stderr)
    combined_json = work_dir / "combined-viral.json"
    combined_json.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")

    # Per-keyword pain-miner (captcha 隔离)
    pain_per_keyword: list[tuple[str, dict]] = []
    if args.with_pains and combined:
        print(f"\n[batch] running pain-miner per keyword (captcha isolated)…", file=sys.stderr)
        for keyword, payload in scanner_results:
            if not payload or not payload.get("results"):
                print(f"  ⏭ {keyword}: no viral notes, skip", file=sys.stderr)
                continue
            kw_viral = work_dir / f"viral-{_safe_filename(keyword)}.json"
            kw_viral.write_text(json.dumps(payload["results"], ensure_ascii=False, indent=2),
                               encoding="utf-8")
            p = run_pain_miner_for_keyword(keyword, kw_viral, args.pain_min_likes,
                                            args.pain_top, work_dir)
            if p:
                for note in p.get("per_note", []):
                    note["source_keyword"] = keyword
                pain_per_keyword.append((keyword, p))
                print(f"    {keyword}: kept {p.get('stats', {}).get('total_kept_pain', 0)} pains",
                      file=sys.stderr)
            if keyword != scanner_results[-1][0]:
                time.sleep(args.sleep)
        # 合并
        pain_payload = {
            "skill": "xhs-comment-pain-miner",
            "version": "0.1.0",
            "input_notes": sum(len(p.get("per_note", [])) for _, p in pain_per_keyword),
            "stats": {
                "total_comments": sum(p.get("stats", {}).get("total_comments", 0) for _, p in pain_per_keyword),
                "total_kept_pain": sum(p.get("stats", {}).get("total_kept_pain", 0) for _, p in pain_per_keyword),
                "elapsed_sec": round(sum(p.get("stats", {}).get("elapsed_sec", 0) for _, p in pain_per_keyword), 1),
            },
            "per_note": [n for _, p in pain_per_keyword for n in p.get("per_note", [])],
        }
    else:
        pain_payload = None

    elapsed = time.time() - t0

    # 输出报告
    summary_md = render_summary(keywords, scanner_results, pain_payload, elapsed)
    viral_md = render_viral_table(combined)
    pains_md = render_pains_table(pain_payload) if pain_payload else ""

    (work_dir / f"{prefix}-summary.md").write_text(summary_md, encoding="utf-8")
    (work_dir / f"{prefix}-viral.md").write_text(viral_md, encoding="utf-8")
    if pains_md:
        (work_dir / f"{prefix}-pains.md").write_text(pains_md, encoding="utf-8")
    (work_dir / f"{prefix}-raw.json").write_text(
        json.dumps({
            "keywords": keywords,
            "scanner_results": [r for _, r in scanner_results],
            "pain_per_keyword": [{"keyword": k, "result": p} for k, p in pain_per_keyword],
            "pain_combined": pain_payload,
            "elapsed_sec": elapsed,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    # 顶层快捷入口
    (DEFAULT_OUT_DIR / f"{prefix}-summary.md").write_text(summary_md, encoding="utf-8")
    if pains_md:
        (DEFAULT_OUT_DIR / f"{prefix}-pains.md").write_text(pains_md, encoding="utf-8")

    print(f"\n[batch] DONE in {elapsed:.0f}s", file=sys.stderr)
    print(f"  summary: {work_dir / prefix}-summary.md", file=sys.stderr)
    print(f"  viral:   {work_dir / prefix}-viral.md", file=sys.stderr)
    if pains_md:
        print(f"  pains:   {work_dir / prefix}-pains.md", file=sys.stderr)
    print(f"  raw:     {work_dir / prefix}-raw.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
