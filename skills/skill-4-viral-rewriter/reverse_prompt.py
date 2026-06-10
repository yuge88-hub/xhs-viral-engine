"""
skill-4-viral-rewriter v0.5
reverse_prompt.py — 4 问 + 6 维 → 5 段式仿写 prompt

输入:
    - Skill 1.5 输出的 {note_id}-analysis.json (meta + 4 问 + 6 维)
    - (可选) Skill 2 输出的 pain-miner JSON (痛点钩子)
输出:
    - {note_id}-reverse-prompt.md (5 段式仿写 prompt, 留空待填)
    - {note_id}-reverse-prompt.filled.md (--auto-fill 时, DeepSeek 填好)

设计:
    5 段 prompt = Role + Audience + Topic + Structure + CTA
    每个 {{xxx}} 是待填空, 用户可手动填, 或 --auto-fill 让 DeepSeek 填

用法:
    # 手工版 (5 段模板, 留空)
    python reverse_prompt.py --note-id 666c0258...0207a2

    # 自动填 (DeepSeek 填好)
    $env:DEEPSEEK_API_KEY="sk-xxx"
    python reverse_prompt.py --note-id 666c0258...0207a2 --auto-fill

    # 带痛点钩子 (来自 pain-miner)
    python reverse_prompt.py --note-id 666c0258...0207a2 --pains pain-miner.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# 修 Windows GBK 终端乱码 (POSTMORTEM #17)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ANALYSIS_DIR = PROJECT_ROOT / "output" / "skill-1.5-viral-analyzer-v0.1"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "skill-4-reverse-prompts-v0.5"


# ============================================================
# 解析 analysis.json
# ============================================================

def load_analysis(analysis_path: Path) -> dict[str, Any]:
    if not analysis_path.exists():
        print(f"ERROR: {analysis_path} 不存在, 先跑 viral_analyzer.py", file=sys.stderr)
        sys.exit(1)
    # ⚠️ POSTMORTEM #26: 用 utf-8-sig 兼容 BOM
    return json.loads(analysis_path.read_text(encoding="utf-8-sig"))


def load_pains(pains_path: Path) -> list[dict[str, Any]]:
    """从 pain-miner JSON 抽 top 5 痛点 (按 likes 排序)"""
    if not pains_path.exists():
        return []
    data = json.loads(pains_path.read_text(encoding="utf-8-sig"))
    # 多种格式兼容: list / {"pains": [...]} / {"per_note": [...]}
    if isinstance(data, list):
        pains = data
    elif isinstance(data, dict):
        pains = data.get("pains") or data.get("per_note") or data.get("data") or []
    else:
        return []
    # 排序 + 取 top 5
    pains_sorted = sorted(pains, key=lambda p: p.get("likes", 0) or 0, reverse=True)
    return pains_sorted[:5]


# ============================================================
# 5 段式 prompt 构造
# ============================================================

def build_prompt(analysis: dict[str, Any], pains: list[dict[str, Any]]) -> dict[str, str]:
    """5 段式 prompt, 每段是结构化字段"""

    meta = analysis.get("meta", {})
    q4 = analysis.get("4_questions", {})
    d6 = analysis.get("6_dimensions", {})

    # 1. Role
    role = {
        "label": "角色设定 (Role)",
        "items": [
            ("作者身份", meta.get("author") or "{{待填: 你的身份 (e.g. 5 年 AI 副业老兵 / 营养师 / 全职妈妈)}}"),
            ("角色 DNA", d6.get("role_dna") or "{{待填: 你的第一人称视角, 权威感来源}}"),
            ("互动数据 (参照)", f"粉丝 {meta.get('fans') or '?'} / 点赞 {meta.get('likes') or '?'} / 收藏 {meta.get('collects') or '?'}"),
        ],
    }

    # 2. Audience
    audience = {
        "label": "目标读者 (Audience)",
        "items": [
            ("人群画像", d6.get("reader_profile") or q4.get("who", {}).get("content") or "{{待填: 25-35 宝妈 + AI 副业新手}}"),
            ("核心需求", "{{待填: 他们要什么 — 工具? 教程? 案例? 情绪?}}"),
            ("认知水平", "{{待填: 小白/有基础/熟练 (影响深度)}}"),
        ],
    }

    # 3. Topic
    pain_hooks = []
    for p in pains[:3]:
        text = p.get("text") or p.get("content") or p.get("comment") or ""
        likes = p.get("likes", 0) or 0
        if text:
            pain_hooks.append(f"- {likes} 赞: \"{text[:80]}\"")
    if not pain_hooks:
        pain_hooks = ["- {{待填: 痛点钩子 1 — 来自评论区高赞}}",
                      "- {{待填: 痛点钩子 2}}",
                      "- {{待填: 痛点钩子 3}}"]

    topic = {
        "label": "选题方向 (Topic)",
        "items": [
            ("爆款主题", q4.get("why_click", {}).get("content") or "{{待填: 选题角度 — 你要写什么}}"),
            ("标题标签", ", ".join(meta.get("tags", [])[:8]) or "{{待填: 9 个相关 tag}}"),
            ("痛点钩子 (开篇可用)", "\n".join(pain_hooks)),
            ("差异化", "{{待填: 你和原爆款不一样的地方 — 避免抄}}"),
        ],
    }

    # 4. Structure
    structure = {
        "label": "内容结构 (Structure)",
        "items": [
            ("总字数控制", d6.get("content_structure") or "{{待填: e.g. 200 字内 5 段}}"),
            ("开头模式", "{{待填: 反常识/痛点共鸣/数字结果/教程预告 — 选 1-2 个}}"),
            ("中段模式", "{{待填: 干货清单/分群/案例 — 选 1 个}}"),
            ("收尾模式", "{{待填: 引导评论/求关注/求教程 — 选 1 个}}"),
            ("语言风格", d6.get("language_style") or "{{待填: 短句 + 感叹号 + emoji + 反问 + 排比}}"),
        ],
    }

    # 5. CTA
    cta = {
        "label": "引导动作 (CTA)",
        "items": [
            ("爆款 CTA 原文", q4.get("where_lead", {}).get("content") or "{{待填: 原爆款末尾让读者做什么}}"),
            ("约束规则", d6.get("constraint_rules") or "{{待填: 禁用词 / 格式 / 边界}}"),
            ("工作流逻辑", d6.get("workflow_logic") or "{{待填: 哪些段落每篇都固定}}"),
        ],
    }

    return {"role": role, "audience": audience, "topic": topic, "structure": structure, "cta": cta}


# ============================================================
# Markdown 渲染
# ============================================================

def render_markdown(note_id: str, meta: dict, sections: dict, filled: dict | None = None) -> str:
    """输出 5 段式 prompt markdown

    filled (dict) 是 {section_key: filled_text} 覆盖留空, 来自 DeepSeek auto-fill
    """
    lines = [
        f"# 仿写 prompt: {meta.get('title', note_id)[:60]}",
        "",
        f"> **note_id**: `{note_id}`  ",
        f"> **作者**: {meta.get('author', '?')}  ",
        f"> **点赞/收藏/评论**: {meta.get('likes', '?')} / {meta.get('collects', '?')} / {meta.get('comments', '?')}  ",
        f"> **发布日期**: {meta.get('publish_date', '?')}  ",
        "",
        "---",
        "",
        "## 5 段式仿写 prompt (Skill 1.5 + Skill 4 v0.5)",
        "",
        "> 用法: 把下面 5 段组合成一个 prompt 发给任何 LLM (Claude / GPT / DeepSeek), 即可仿写。",
        "> `{{待填:...}}` 标记的项是**必须人工填的** — 你的具体场景别人替不了。",
        "",
    ]

    for key in ("role", "audience", "topic", "structure", "cta"):
        sec = sections[key]
        filled_text = (filled or {}).get(key)
        lines.append(f"## {sec['label']}")
        lines.append("")
        if filled_text:
            lines.append("> ✅ DeepSeek 已自动填充 (可微调):")
            lines.append("")
            lines.append(filled_text)
            lines.append("")
        for label, value in sec["items"]:
            if "\n" in str(value):
                # 多行 (e.g. 痛点列表)
                lines.append(f"**{label}**:")
                lines.append("")
                lines.append(str(value))
            else:
                lines.append(f"- **{label}**: {value}")
            lines.append("")  # 每个 item 后空行, 避免粘连
        lines.append("---")
        lines.append("")

    # 完整 prompt 拼接 (一键复制)
    lines.append("## 🎯 一键复制版 (完整 prompt)")
    lines.append("")
    lines.append("```")
    lines.append(build_full_prompt(meta, sections, filled))
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def build_full_prompt(meta: dict, sections: dict, filled: dict | None = None) -> str:
    """拼成一段可执行的 prompt (发 LLM 用)"""
    parts = [
        f"你是一位小红书爆款仿写专家。我给你一个爆款样本的逆向分析, 请基于此仿写一条新笔记。",
        "",
        f"## 爆款样本",
        f"- 标题: {meta.get('title', '?')}",
        f"- 作者: {meta.get('author', '?')}",
        f"- 标签: {', '.join(meta.get('tags', [])[:8])}",
        "",
    ]

    for key in ("role", "audience", "topic", "structure", "cta"):
        sec = sections[key]
        parts.append(f"## {sec['label']}")
        if filled and filled.get(key):
            parts.append(filled[key])
        else:
            for label, value in sec["items"]:
                if "\n" in str(value):
                    parts.append(f"**{label}**:")
                    parts.append(str(value))
                else:
                    parts.append(f"- **{label}**: {value}")
        parts.append("")

    parts.append("## 输出要求")
    parts.append("- 标题: 1 行, ≤ 20 字, 套原爆款的钩子公式")
    parts.append("- 正文: 严格按中段模式分 3-5 段, ≤ 200 字")
    parts.append("- 9 个 tag: 复用 + 微调原爆款标签")
    parts.append("- CTA: 套原爆款引导动作")
    parts.append("")
    parts.append("现在, 给出你的仿写:")

    return "\n".join(parts)


# ============================================================
# DeepSeek auto-fill
# ============================================================

def call_deepseek(prompt: str, max_tokens: int = 2000) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return ""
    import requests

    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    try:
        r = requests.post(
            DEEPSEEK_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是小红书爆款分析专家,擅长从单条笔记反推'如何仿写'的具体 prompt。"},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.5,
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"WARN: DeepSeek 调用失败: {e}", file=sys.stderr)
        return ""


def auto_fill_section(section_key: str, sec: dict, meta: dict) -> str:
    """DeepSeek 填一个 section"""
    items_str = "\n".join(f"- {label}: {value}" for label, value in sec["items"])
    prompt = f"""基于下面这条爆款笔记, 帮我把 "{sec['label']}" 这一段**填具体**(不要留{{{{待填}}}}):

笔记: {meta.get('title', '?')} (作者 {meta.get('author', '?')})
标签: {', '.join(meta.get('tags', [])[:5])}
数据: 点赞 {meta.get('likes', '?')} / 收藏 {meta.get('collects', '?')} / 评论 {meta.get('comments', '?')}

{items_str}

要求:
- 用第二人称"你"指读者
- 1-3 句中文,具体到可执行
- 不要 markdown 标题, 直接回答
"""
    return call_deepseek(prompt, max_tokens=500)


# ============================================================
# Main
# ============================================================

def main() -> int:
    p = argparse.ArgumentParser(
        description="Skill 4 v0.5 reverse_prompt — 4问6维 → 5 段式仿写 prompt",
    )
    p.add_argument("--note-id", required=True, help="xhs note_id")
    p.add_argument("--analysis-dir", default=str(DEFAULT_ANALYSIS_DIR), help="viral_analyzer 输出目录")
    p.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR), help="输出目录")
    p.add_argument("--pains", default="", help="(可选) pain-miner JSON 路径")
    p.add_argument("--auto-fill", action="store_true", help="用 DeepSeek 自动填留空项")
    args = p.parse_args()

    analysis_dir = Path(args.analysis_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Skill 4 v0.5 reverse-prompt ===")
    print(f"note_id: {args.note_id}")

    # 1. 读 analysis
    analysis_path = analysis_dir / f"{args.note_id}-analysis.json"
    analysis = load_analysis(analysis_path)
    print(f"  ✓ 读 {analysis_path.name}")

    # 2. 读 pain (可选)
    pains = []
    if args.pains:
        pains = load_pains(Path(args.pains))
        print(f"  ✓ 读 {len(pains)} 个痛点钩子 (来自 {Path(args.pains).name})")
    else:
        print("  - 跳过 pain (没传 --pains)")

    # 3. 构造 5 段
    sections = build_prompt(analysis, pains)
    meta = analysis.get("meta", {})

    # 4. auto-fill (可选)
    filled = None
    if args.auto_fill:
        if not os.environ.get("DEEPSEEK_API_KEY"):
            print("WARN: --auto-fill 但没 DEEPSEEK_API_KEY, 跳过", file=sys.stderr)
        else:
            print("\n>>> DeepSeek auto-fill 5 段")
            filled = {}
            for key in ("role", "audience", "topic", "structure", "cta"):
                sec = sections[key]
                text = auto_fill_section(key, sec, meta)
                if text:
                    filled[key] = text
                    print(f"  ✅ {key}: {len(text)} 字符")
                else:
                    print(f"  ❌ {key}: 失败")
            print(f"  填充率: {len(filled)}/5")

    # 5. 输出
    md = render_markdown(args.note_id, meta, sections, filled)
    out_path = out_dir / f"{args.note_id}-reverse-prompt.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"\n  ✓ {out_path} ({len(md) // 1024} KB)")

    # 6. JSON 也存 (含 sections 结构, 方便 Skill 5 sync 进 Obsidian)
    json_path = out_dir / f"{args.note_id}-reverse-prompt.json"
    json_path.write_text(json.dumps(
        {
            "skill": "skill-4-viral-rewriter",
            "version": "0.5.0",
            "note_id": args.note_id,
            "meta": meta,
            "sections": {k: {"label": v["label"], "items": v["items"]} for k, v in sections.items()},
            "auto_filled": filled or {},
            "pains_used": [p.get("text", "")[:100] for p in pains],
        },
        ensure_ascii=False, indent=2,
    ), encoding="utf-8")
    print(f"  ✓ {json_path}")

    print(f"\n=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
