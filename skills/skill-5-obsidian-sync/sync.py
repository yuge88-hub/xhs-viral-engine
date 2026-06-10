"""skill-5-obsidian-sync v0.2

把 Skill 1+2+3+4+1.5 全部输出同步到 Obsidian vault (v0.2 加 04/05/06 三章节)

Usage:
    python sync.py --vault "C:\\path\\to\\vault" --dry-run
    python sync.py --vault "C:\\path\\to\\vault"

v0.2 增量 (vs v0.1):
- 04-benchmarks: Skill 1.5 viral_analyzer 加 cover_analyzer 加 benchmark_check
- 05-reverse-prompts: Skill 4 v0.5 reverse_prompt (5 段式仿写 prompt)
- 06-reports: HTML 情报报告 加 summarize markdown

特性:
- YAML frontmatter (date, keyword, trigger, likes, tags)
- wikilinks 关键词互链
- 增量同步 (mtime 对比, 不重写未变更文件)
- 00-index.md 首页一键导航
- 不破坏原文件 (read-only on source)
"""
import argparse
import sys
import io
import re
import json
from pathlib import Path
from datetime import datetime

# 修 Windows GBK 终端乱码 (POSTMORTEM 17)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# === 配置 ===
VAULT_SUBFOLDER = "小红书爆款引擎"
KEYWORDS = ["AI 副业", "营养食疗", "副业赚钱", "减肥", "自媒体"]
DATE = "2026-06-09"

# === Frontmatter 模板 (用 chr(10) 拼接避免多行字面量 lexer 折叠问题) ===
def _fm(typ, **fields):
    """生成 YAML frontmatter 字符串"""
    lines = ["---", f"type: {typ}", f"date: '{DATE}'"]
    for k, v in fields.items():
        if v is None:
            continue
        # 任何值是含 - 数字 / + 数字 / 数字+标识符 / 中文的都加引号
        s = str(v)
        if re.search(r"[一-鿿]", s) or "-" in s or "+" in s:
            lines.append(f"{k}: '{s}'")
        else:
            lines.append(f"{k}: {s}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


# === 文件路径映射 ===

def get_source_files(source_root: Path) -> dict:
    """返回 6 章节 {section: {filename: (source_path, file_type)}}"""
    src = source_root / "output"
    mappings = {
        "01-raw": {},
        "02-formula": {},
        "03-rewrites": {},
        "04-benchmarks": {},
        "05-reverse-prompts": {},
        "06-reports": {},
    }

    # 01-raw: 每关键词 viral + pain-miner
    for kw in KEYWORDS:
        kw_safe = kw.replace(" ", "_")
        viral_p = src / f"batch-full-5kw/viral-{kw_safe}.json"
        if viral_p.exists():
            mappings["01-raw"][f"{kw}/viral.md"] = (viral_p, "viral", kw)
        pain_p = src / f"batch-full-5kw/pain-miner-{kw_safe}.json"
        if pain_p.exists():
            mappings["01-raw"][f"{kw}/pains.md"] = (pain_p, "pain", kw)

    summary_p = src / "batch-full-5kw/batch-full-5kw-summary.md"
    if summary_p.exists():
        mappings["01-raw"]["_batch-summary.md"] = (summary_p, "summary", None)

    # 02-formula: Skill 4 公式文档
    formula_dir = src / "skill-4-formula-rewrites-v0.1"
    if (formula_dir / "formula-report.md").exists():
        mappings["02-formula"]["formula-report.md"] = (formula_dir / "formula-report.md", "formula-report", None)

    v02_dir = src / "skill-4-formula-rewrites-v0.2"
    for fname, ftype in [
        ("pain-reclassified.md", "pain-reclassified"),
        ("ab-titles.md", "ab-titles"),
        ("body-formula-v2.md", "body-formula"),
    ]:
        if (v02_dir / fname).exists():
            mappings["02-formula"][fname] = (v02_dir / fname, ftype, None)

    # 03-rewrites: Skill 4 仿写
    v01_rewrites = src / "skill-4-formula-rewrites-v0.1/rewrites"
    v04_filled = src / "skill-4-formula-rewrites-v0.3"
    for kw in KEYWORDS:
        f_ws = v01_rewrites / f"{kw}.md"
        f_ns = v01_rewrites / f"{kw.replace(' ', '')}.md"
        f = f_ws if f_ws.exists() else f_ns
        if f.exists():
            mappings["03-rewrites"][f"{kw}/v0.1-手写.md"] = (f, "rewrite-v01", kw)
    for kw in KEYWORDS:
        for cand in v04_filled.glob(f"{kw}*.filled.md"):
            mappings["03-rewrites"][f"{kw}/v0.4-auto-filled.md"] = (cand, "rewrite-v04", kw)

    # 04-benchmarks: Skill 1.5 analysis / cover / benchmark
    v15_dir = src / "skill-1.5-viral-analyzer-v0.1"
    for p in v15_dir.glob("*-analysis.json"):
        nid = p.stem.replace("-analysis", "")
        mappings["04-benchmarks"][f"{nid}-4q6d.md"] = (p, "viral-analysis", None)
    for p in v15_dir.glob("*-4问+6维.md"):
        nid = p.stem.replace("-4问+6维", "")
        mappings["04-benchmarks"][f"{nid}-4问+6维-原文.md"] = (p, "viral-analysis", None)
    for p in v15_dir.glob("*-cover.json"):
        nid = p.stem.replace("-cover", "")
        mappings["04-benchmarks"][f"{nid}-封面.md"] = (p, "viral-cover", None)
    for p in v15_dir.glob("*-benchmark.json"):
        nid = p.stem.replace("-benchmark", "")
        mappings["04-benchmarks"][f"{nid}-benchmark.md"] = (p, "viral-benchmark", None)

    # 05-reverse-prompts: Skill 4 v0.5
    v45_dir = src / "skill-4-reverse-prompts-v0.5"
    for p in v45_dir.glob("*-reverse-prompt.md"):
        nid = p.stem.replace("-reverse-prompt", "")
        mappings["05-reverse-prompts"][f"{nid}-prompt.md"] = (p, "reverse-prompt", None)

    # 06-reports: HTML + summarize
    for p in src.glob("AI*_爆款情报报告_*.html"):
        mappings["06-reports"][p.name] = (p, "html-report", None)
    for p in src.glob("AI*_爆款逻辑_*.md"):
        mappings["06-reports"][p.name] = (p, "viral-analysis", None)

    return mappings


# === 内容生成 ===

def make_viral_md(src: Path, kw: str) -> str:
    data = json.loads(src.read_text(encoding="utf-8-sig"))
    notes = data if isinstance(data, list) else data.get("notes", [])
    total = len(notes)
    total_likes = sum((n.get("likes") or 0) for n in notes)

    fm = _fm("viral-note-collection", keyword=kw, keyword_tag=kw.replace(" ", ""),
             total=total, total_likes=total_likes, source="xhs-batch-full-5kw")
    body = f"# {kw} - Viral 爆款笔记 ({total} 条)\n\n"
    body += f"**总点赞**: {total_likes:,} | **总收藏**: {sum((n.get('collects') or 0) for n in notes):,}\n\n"
    body += "## 爆款 Top 30 (按点赞降序)\n\n"
    body += "| # | 点赞 | 收藏 | 评论 | 标题 | 作者 |\n|---:|---:|---:|---:|---|---|\n"
    for i, n in enumerate(sorted(notes, key=lambda x: x.get("likes") or 0, reverse=True)[:30], 1):
        title = (n.get("title") or "(无标题)").replace("|", "\\|")[:50]
        body += f"| {i} | {n.get('likes', 0):,} | {n.get('collects', 0):,} | {n.get('comments', 0):,} | {title} | {n.get('author', '?')} |\n"
    return fm + body


def make_pain_md(src: Path, kw: str) -> str:
    data = json.loads(src.read_text(encoding="utf-8-sig"))
    per_note = data.get("per_note", [])
    total_comments = sum(n.get("total_comments", 0) for n in per_note)
    total_pains = sum(len(n.get("top_pains", [])) for n in per_note)

    fm = _fm("pain-mining", keyword=kw, keyword_tag=kw.replace(" ", ""),
             total_comments=total_comments, total_pains=total_pains, source="xhs-pain-miner")
    body = f"# {kw} - 痛点云 ({total_pains} 条 / {total_comments} 评论)\n\n## 按笔记分组\n\n"
    for note in per_note:
        if not note.get("top_pains"):
            continue
        body += f"### 📝 {note.get('title', '(无标题)')}\n\n"
        for p in note["top_pains"]:
            likes = p.get("likes", 0)
            content = (p.get("content") or "").replace("\n", " ")[:200]
            cats = ", ".join(p.get("categories", []))
            nickname = p.get("nickname", "匿名")
            body += f"- **{likes} 赞** `[{cats}]` {content}\n  — @{nickname}\n"
        body += "\n"
    return fm + body


def make_simple_md(src: Path, ftype: str) -> str:
    """简单复制 + frontmatter (markdown/json/html 通用)"""
    raw = src.read_bytes()
    try:
        content = raw.decode("utf-8-sig")
    except Exception:
        content = raw.decode("utf-8", errors="replace")
    type_map = {
        "summary": "batch-summary",
        "formula-report": "formula-report",
        "pain-reclassified": "pain-reclassified",
        "ab-titles": "ab-titles",
        "body-formula": "body-formula",
        "rewrite-v01": "rewrite",
        "rewrite-v04": "rewrite",
        "viral-analysis": "viral-analysis",
        "viral-cover": "viral-cover",
        "viral-benchmark": "viral-benchmark",
        "reverse-prompt": "reverse-prompt",
        "html-report": "html-report",
    }
    extra = {}
    if ftype in ("rewrite-v01", "rewrite-v04"):
        formula_match = re.search(r"采用公式[::]\s*([^\n]+)", content)
        extra["formula"] = formula_match.group(1).strip() if formula_match else "未知"
        extra["method"] = "auto-filled by deepseek-v4-flash" if ftype == "rewrite-v04" else "手写 加 mimeng"
    fm = _fm(type_map.get(ftype, ftype), source="skill-1.5-viral-analyzer", **extra)
    return fm + content


# === Wikilink 注入 ===

def add_wikilinks(content: str, current_keyword=None) -> str:
    others = [k for k in KEYWORDS if k != current_keyword] if current_keyword else KEYWORDS
    related = "\n\n---\n\n## 🔗 相关关键词\n\n"
    if current_keyword:
        related += f"- 当前关键词: **{current_keyword}**\n"
    for k in others:
        related += f"- [[{k}]]\n"
    return content + related


# === 同步逻辑 ===

def sync_file(src: Path, vault: Path, rel: str, ftype: str, kw=None, dry_run=False) -> dict:
    target = vault / VAULT_SUBFOLDER / rel
    if ftype == "viral":
        content = make_viral_md(src, kw)
    elif ftype == "pain":
        content = make_pain_md(src, kw)
    else:
        content = make_simple_md(src, ftype)

    if ftype in ("viral", "pain", "rewrite-v01", "rewrite-v04"):
        content = add_wikilinks(content, current_keyword=kw)
    else:
        content = add_wikilinks(content, current_keyword=None)

    if not dry_run and target.exists():
        if target.stat().st_mtime > src.stat().st_mtime:
            return {"src": str(src), "tgt": str(target), "status": "skip"}

    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"src": str(src), "tgt": str(target), "status": "written"}
    return {"src": str(src), "tgt": str(target), "status": "would write"}


# === Index 生成 (list 拼接, 避免 f-string 折叠) ===

def make_index(vault: Path, mappings: dict, dry_run=False) -> None:
    target = vault / VAULT_SUBFOLDER / "00-index.md"
    parts: list[str] = []
    parts.append("---")
    parts.append("type: index")
    parts.append(f"date: '{DATE}'")
    parts.append("source: skill-5-obsidian-sync")
    parts.append("tags: [小红书, 爆款引擎, 索引]")
    parts.append("---")
    parts.append("")
    parts.append("# 🏠 小红书爆款引擎 — 知识库")
    parts.append("")
    parts.append(f"> 最后同步: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    parts.append("> 来源: web-clipper-master 项目")
    parts.append("> Skill: 1+2+3+4+1.5 (5 阶段全部跑通)")
    parts.append("")
    parts.append("## 🎯 5 关键词速览")
    parts.append("")
    parts.append("| 关键词 | Viral 笔记 | 痛点 | 仿写 v0.1 | 仿写 v0.4 |")
    parts.append("|---|---|---|---|---|")
    for kw in KEYWORDS:
        has_v01 = "Y" if any(kw in k for k in mappings["03-rewrites"].keys()) else "-"
        has_v04 = "Y" if any(kw in k and "v0.4" in k for k in mappings["03-rewrites"].keys()) else "-"
        parts.append(f"| [[{kw}]] | [[{kw}-viral]] | [[{kw}-pains]] | {has_v01} | {has_v04} |")
    parts.append("")
    parts.append("## 📚 01-raw 原始数据")
    parts.append("")
    parts.append("按关键词分组的爆款笔记, 痛点评论, 汇总报告。")
    parts.append("")
    parts.append("- [[_batch-summary]] - 5 关键词汇总")
    for kw in KEYWORDS:
        parts.append(f"- [[{kw}]] - 关键词首页")
    parts.append("")
    parts.append("## 🧠 02-formula 公式库")
    parts.append("")
    parts.append("Skill 4 反推的爆款公式, 痛点重分类, A/B 标题矩阵, 3 个 Body 模板。")
    parts.append("")
    parts.append("- [[formula-report]] - v0.1 跨关键词公式")
    parts.append("- [[pain-reclassified]] - v0.2 159 痛点 LLM 重分类")
    parts.append("- [[ab-titles]] - v0.2 15 A/B 备选标题")
    parts.append("- [[body-formula-v2]] - v0.2 3 个可复用 Body 模板")
    parts.append("")
    parts.append("## ✍️ 03-rewrites 仿写")
    parts.append("")
    parts.append("每关键词 2 版本: v0.1 手写 + v0.4 DeepSeek auto-filled")
    parts.append("")
    for kw in KEYWORDS:
        parts.append(f"### {kw}")
        parts.append(f"- [[{kw}-v0.1-手写]]")
        if any(kw in k and "v0.4" in k for k in mappings["03-rewrites"].keys()):
            parts.append(f"- [[{kw}-v0.4-auto-filled]]")
        parts.append("")

    if "04-benchmarks" in mappings and mappings["04-benchmarks"]:
        parts.append("")
        parts.append("## 🔬 04-benchmarks 爆款拆解 (v0.2 新)")
        parts.append("")
        parts.append(f"Skill 1.5 viral_analyzer + cover_analyzer + benchmark_check 全部输出 ({len(mappings['04-benchmarks'])} 个文件)")
        parts.append("")
        for fname in sorted(mappings["04-benchmarks"].keys()):
            parts.append(f"- [[{fname.replace('.md', '')}]]")

    if "05-reverse-prompts" in mappings and mappings["05-reverse-prompts"]:
        parts.append("")
        parts.append("## 🎯 05-reverse-prompts 5 段式 prompt (v0.2 新)")
        parts.append("")
        parts.append(f"Skill 4 v0.5 输出 ({len(mappings['05-reverse-prompts'])} 个)")
        parts.append("")
        for fname in sorted(mappings["05-reverse-prompts"].keys()):
            parts.append(f"- [[{fname.replace('.md', '')}]]")

    if "06-reports" in mappings and mappings["06-reports"]:
        parts.append("")
        parts.append("## 📊 06-reports 情报报告 (v0.2 新)")
        parts.append("")
        parts.append(f"HTML dashboard + summarize ({len(mappings['06-reports'])} 个)")
        parts.append("")
        for fname in sorted(mappings["06-reports"].keys()):
            parts.append(f"- [[{fname.replace('.html', '').replace('.md', '')}]]")

    parts.append("")
    parts.append("## 🔧 元数据")
    parts.append("")
    parts.append("- 所有文件含 YAML frontmatter")
    parts.append("- 关键词自动 wikilink 互链")
    parts.append("- Dataview 友好表格")
    parts.append("")
    parts.append("## 🚀 重新同步")
    parts.append("")
    parts.append("```powershell")
    parts.append('cd "C:\\Users\\<user>\\Downloads\\web-clipper-master"')
    parts.append("python skills\\skill-5-obsidian-sync\\sync.py --vault <vault_path>")
    parts.append("```")
    parts.append("")

    content = "\n".join(parts)

    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


# === Main ===

def main() -> int:
    p = argparse.ArgumentParser(description="Skill 5 v0.2 - Obsidian 同步")
    p.add_argument("--vault", required=True, help="Obsidian vault 根目录")
    p.add_argument("--source", default=str(PROJECT_ROOT), help="项目根 (含 output/)")
    p.add_argument("--dry-run", action="store_true", help="只预览不写")
    args = p.parse_args()

    vault = Path(args.vault)
    source = Path(args.source)
    if not args.dry_run and not vault.exists():
        print(f"ERROR: vault 不存在: {vault}")
        return 1

    print(f"=== Skill 5 v0.2 Obsidian Sync ===")
    print(f"vault: {vault}")
    print(f"source: {source}")
    if args.dry_run:
        print(f"mode: DRY RUN (不会写文件)")

    mappings = get_source_files(source)
    results = []
    for section, files in mappings.items():
        for rel, (src_p, ftype, kw) in files.items():
            r = sync_file(src_p, vault, f"{section}/{rel}", ftype, kw, dry_run=args.dry_run)
            results.append((section, r))

    make_index(vault, mappings, dry_run=args.dry_run)
    if not args.dry_run:
        results.append(("00-index.md", {"src": "(generated)", "tgt": str(vault / VAULT_SUBFOLDER / "00-index.md"), "status": "written"}))

    # 汇总
    counts = {"written": 0, "would write": 0, "skip": 0}
    for _, r in results:
        s = r["status"]
        counts[s] = counts.get(s, 0) + 1
    print(f"\n=== 汇总 ===")
    print(f"  written:     {counts.get('written', 0)}")
    print(f"  would write: {counts.get('would write', 0)}")
    print(f"  skip:        {counts.get('skip', 0)}")
    print(f"  章节数:      {len(mappings)}")

    if args.dry_run:
        print(f"\n各章节文件数:")
        for s, files in mappings.items():
            print(f"  {s}: {len(files)} 个")
    return 0


PROJECT_ROOT = Path(__file__).resolve().parents[2]

if __name__ == "__main__":
    sys.exit(main())
