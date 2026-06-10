"""fix-sync-v2.py — 一次性彻底修复 sync.py 的所有字符串字面量问题

策略: 重写 sync.py 的全部多行字符串为单行 raw 字符串 + .format() 占位符
避免: Python 3.14 lexer 在多行 string literal 内做算术折叠 + 中文标点 invalid

只修复 make_index 函数 (其他部分已修复)
"""
from __future__ import annotations
import re
from pathlib import Path

p = Path(r"C:\Users\张哥\Downloads\web-clipper-master\skills\skill-5-obsidian-sync\sync.py")

# 读原文 (bytes 模式, 避免任何编码问题)
text = p.read_bytes().decode("utf-8", errors="replace")
lines = text.split("\n")

# 找 make_index 函数范围
start_idx = None
for i, line in enumerate(lines):
    if "def make_index(" in line:
        start_idx = i
        break
print(f"make_index starts at line {start_idx + 1}")

# 找函数结束 (下一个 def 或文件结束)
end_idx = None
for i in range(start_idx + 1, len(lines)):
    if lines[i].startswith("def ") or (lines[i].startswith("if __name__")):
        end_idx = i
        break
if end_idx is None:
    end_idx = len(lines)
print(f"make_index ends at line {end_idx}")

# 完全重写 make_index 函数
new_func = '''def make_index(vault_path: Path, mappings: dict, dry_run: bool = False) -> None:
    """生成 00-index.md 首页"""
    target = vault_path / VAULT_SUBFOLDER / "00-index.md"

    parts: list[str] = []
    parts.append("---")
    parts.append("type: index")
    parts.append("date: '2026-06-09'")
    parts.append("source: skill-5-obsidian-sync")
    parts.append("tags: [小红书, 爆款引擎, 索引]")
    parts.append("---")
    parts.append("")
    parts.append("# 🏠 小红书爆款引擎 — 知识库")
    parts.append("")
    parts.append(f"> 最后同步: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    parts.append("> 来源: [web-clipper-master](../../web-clipper-master)")
    parts.append("> Skill: 1加2加3加4 (4 阶段全部跑通)")
    parts.append("")
    parts.append("## 🎯 5 关键词速览")
    parts.append("")
    parts.append("| 关键词 | Viral 笔记 | 痛点 | 仿写 v0.1 | 仿写 v0.4 |")
    parts.append("|---|---|---|---|---|")
    for kw in KEYWORDS:
        has_v01 = "✅" if any(kw in k for k in mappings["03-rewrites"].keys()) else "—"
        has_v04 = "✅" if any(kw in k and 'v0.4' in k for k in mappings["03-rewrites"].keys()) else "—"
        parts.append(f"| [[{kw}]] | [[{kw}-viral]] | [[{kw}-pains]] | {has_v01} | {has_v04} |")
    parts.append("")
    parts.append("## 📚 01-raw 原始数据")
    parts.append("")
    parts.append("按关键词分组的爆款笔记 加 痛点评论 加 汇总报告。")
    parts.append("")
    parts.append("- [[_batch-summary]] - 5 关键词汇总")
    for kw in KEYWORDS:
        parts.append(f"- [[{kw}]] - 关键词首页")
    parts.append("")
    parts.append("## 🧠 02-formula 公式库")
    parts.append("")
    parts.append("Skill 4 反推的爆款公式 加 痛点重分类 加 A/B 标题矩阵 加 3 个 Body 模板。")
    parts.append("")
    parts.append("- [[formula-report]] - v0.1 跨关键词公式 (5 标题 加 3 hook 加 3 结构 加 3 CTA)")
    parts.append("- [[pain-reclassified]] - v0.2 159 痛点 LLM 重分类 (5 行动触发)")
    parts.append("- [[ab-titles]] - v0.2 15 A/B 备选标题")
    parts.append("- [[body-formula-v2]] - v0.2 3 个可复用 Body 模板")
    parts.append("")
    parts.append("## ✍️ 03-rewrites 仿写")
    parts.append("")
    parts.append("每关键词 2 版本: v0.1 手写 加 v0.4 DeepSeek auto-filled。")
    parts.append("")
    for kw in KEYWORDS:
        parts.append(f"### {kw}")
        parts.append(f"- [[{kw}-v0.1-手写]] - 手写仿写")
        if any(kw in k and 'v0.4' in k for k in mappings["03-rewrites"].keys()):
            parts.append(f"- [[{kw}-v0.4-auto-filled]] - DeepSeek 自动填")
        parts.append("")

    if "04-benchmarks" in mappings:
        parts.append("")
        parts.append("## 🔬 04-benchmarks 爆款拆解 (v0.2 新)")
        parts.append("")
        parts.append(f"Skill 1.5 viral_analyzer 加 cover_analyzer 加 benchmark_check 的全部输出 ({len(mappings['04-benchmarks'])} 个文件)")
        parts.append("")
        for fname in sorted(mappings["04-benchmarks"].keys()):
            parts.append(f"- [[{fname.replace('.md', '')}]]")

    if "05-reverse-prompts" in mappings:
        parts.append("")
        parts.append("## 🎯 05-reverse-prompts 5 段式 prompt (v0.2 新)")
        parts.append("")
        parts.append(f"Skill 4 v0.5 输出的 4问加6维转5段式仿写 prompt ({len(mappings['05-reverse-prompts'])} 个)")
        parts.append("")
        for fname in sorted(mappings["05-reverse-prompts"].keys()):
            parts.append(f"- [[{fname.replace('.md', '')}]]")

    if "06-reports" in mappings:
        parts.append("")
        parts.append("## 📊 06-reports 情报报告 (v0.2 新)")
        parts.append("")
        parts.append(f"HTML dashboard 加 summarize markdown ({len(mappings['06-reports'])} 个)")
        parts.append("")
        for fname in sorted(mappings["06-reports"].keys()):
            parts.append(f"- [[{fname.replace('.html', '').replace('.md', '')}]]")

    parts.append("")
    parts.append("## 🔧 元数据")
    parts.append("")
    parts.append("- 所有文件含 YAML frontmatter (date 加 keyword 加 tags)")
    parts.append("- 关键词自动 [[wikilink]] 互链")
    parts.append("- Dataview 友好表格")
    parts.append("")
    parts.append("## 🚀 重新同步")
    parts.append("")
    parts.append("```powershell")
    parts.append('cd "C:\\Users\\张哥\\Downloads\\web-clipper-master"')
    parts.append("python skills\\skill-5-obsidian-sync\\sync.py --vault \\"你的 vault 路径\\"")
    parts.append("```")
    parts.append("")

    content = "\\n".join(parts)

    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
'''

# 替换
new_lines = lines[:start_idx] + new_func.split("\n") + lines[end_idx:]
new_text = "\n".join(new_lines)

# 写回 UTF-8
p.write_text(new_text, encoding="utf-8")
print(f"Rewrote {len(new_text)} chars to {p}")
print("Now run: python -m py_compile skills\\skill-5-obsidian-sync\\sync.py")
