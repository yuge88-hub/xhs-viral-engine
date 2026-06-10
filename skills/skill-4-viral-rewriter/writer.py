"""
skill-4-viral-rewriter v0.6
writer.py — 用 reverse_prompt.md 调 LLM 写一条仿写笔记 (Step 9)

输入:
    - Skill 4 v0.5 输出的 {note_id}-reverse-prompt.md (5 段式 prompt)
    - (可选) 用户的具体场景填入 (5 段里的 {{待填}})

输出:
    - {note_id}-imitate.md (标题 + 正文 + 9 tag + CTA + 封面建议)

机制:
    1. 读 reverse-prompt.md, 提取 5 段内容
    2. 用 LLM 套 5 段式模板写新笔记
    3. 用户填具体场景 ({{待填}} → 真实信息) 后 LLM 输出成品

用法:
    # 1. 准备: 拿 reverse-prompt.md, 手动填 5 段里的 {{待填}}
    # 2. 跑 writer:
    $env:DEEPSEEK_API_KEY="sk-..."
    python writer.py --reverse-prompt output/skill-4-reverse-prompts-v0.5/<id>-reverse-prompt.md

    # 3. 也支持 --no-llm (手工模式, 留空让你自己写)
    python writer.py --reverse-prompt <md> --no-llm
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "skill-4-writes-v0.6"


# ============================================================
# 读 reverse_prompt.md 提取 5 段
# ============================================================

def parse_reverse_prompt(md_path: Path) -> dict:
    """从 reverse-prompt.md 提取 5 段 prompt

    返回 {"meta": {...}, "sections": {role/audience/topic/structure/cta: text}}
    """
    if not md_path.exists():
        print(f"ERROR: {md_path} 不存在, 先跑 reverse_prompt.py", file=sys.stderr)
        sys.exit(1)

    content = md_path.read_text(encoding="utf-8-sig")
    sections = {}

    for key in ("role", "audience", "topic", "structure", "cta"):
        # 匹配 ## 角色设定 (Role) ... ## 目标读者 ... 之间的内容
        patterns = {
            "role": r"## 角色设定 \(Role\)(.*?)(?=## 目标读者|## 一键复制版|---|\Z)",
            "audience": r"## 目标读者 \(Audience\)(.*?)(?=## 选题方向|## 一键复制版|---|\Z)",
            "topic": r"## 选题方向 \(Topic\)(.*?)(?=## 内容结构|## 一键复制版|---|\Z)",
            "structure": r"## 内容结构 \(Structure\)(.*?)(?=## 引导动作|## 一键复制版|---|\Z)",
            "cta": r"## 引导动作 \(CTA\)(.*?)(?=## 一键复制版|## 🎯|---|\Z)",
        }
        m = re.search(patterns[key], content, re.DOTALL)
        if m:
            sections[key] = m.group(1).strip()
        else:
            sections[key] = ""

    # 提取 meta (note_id, author, metrics)
    meta = {}
    for line in content.split("\n"):
        m = re.match(r"> \*\*(\w+)\*\*:\s*`?([^`\n]+)", line)
        if m:
            meta[m.group(1).lower()] = m.group(2).strip().rstrip("`")

    return {"meta": meta, "sections": sections}


# ============================================================
# DeepSeek 调 LLM 写新笔记
# ============================================================

def call_deepseek(prompt: str, system: str = "", max_tokens: int = 2000) -> str:
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
                    {"role": "system", "content": system or "你是小红书爆款仿写专家。"},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,  # 仿写需要一定创造性
            },
            timeout=90,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"WARN: DeepSeek 调用失败: {e}", file=sys.stderr)
        return ""


def build_writer_prompt(reverse: dict) -> str:
    """构造仿写 prompt: 把 5 段 reverse 内容 + 用户填的具体场景组合"""
    sections = reverse["sections"]
    meta = reverse["meta"]

    # 检查 5 段里是否有 {{待填}} — 如果有, 用户还没填, 提示
    has_pending = any("{{待填" in v for v in sections.values())

    return f"""# 任务
基于以下爆款的 5 段式反向 prompt, 仿写一条新小红书笔记。

# 原爆款参考 (作为风格锚点)
- 标题: {meta.get('title', '?')}
- 作者: {meta.get('author', '?')}
- 点赞: {meta.get('点赞', '?')}

# 5 段式反向 prompt (Skill 4 v0.5 输出)

## 角色设定
{sections.get('role', '(无)')}

## 目标读者
{sections.get('audience', '(无)')}

## 选题方向
{sections.get('topic', '(无)')}

## 内容结构
{sections.get('structure', '(无)')}

## 引导动作
{sections.get('cta', '(无)')}

{'⚠️ 注意: 5 段里仍有 {{待填}} 槽位未填, 请用以下"我的具体场景"替换' if has_pending else ''}

# 输出要求
严格按照以下格式输出 (Markdown):

# 标题
(1 行, ≤ 20 字, 套原爆款钩子公式 + emoji + 数字)

# 正文
(200-300 字, 分 3-5 段, 每段 ≤ 50 字, 强 hook 开头 + 弱 CTA 收尾)
(段落之间空一行)

# 9 个 tag
#tag1 #tag2 #tag3 #tag4 #tag5 #tag6 #tag7 #tag8 #tag9

# CTA
(1-2 句话, 引导关注/评论/收藏, 不强卖)

# 封面建议
(描述封面应该长什么样: 主色 / 文字位置 / 元素 / 风格)

# 拆解
(1 句话说明这条仿写套用了原爆款的哪个公式, 比如 "套用 A 数字结果型 + C 教程 SOP 型")
"""


# ============================================================
# 输出
# ============================================================

def render_imitate_md(meta: dict, llm_output: str) -> str:
    """把 LLM 输出包成标准 markdown"""
    fm = f"""---
type: xhs-imitate
date: '2026-06-09'
version: v0.6
source: skill-4-viral-rewriter
method: reverse_prompt + DeepSeek 仿写
original_note_id: {meta.get('note_id', '?')}
original_author: {meta.get('author', '?')}
tags: [小红书, 仿写, imitate, v0.6]
---

# 🎨 仿写: 基于爆款的 LLM 生成笔记

> **原爆款**: {meta.get('title', '?')} (by {meta.get('author', '?')}, 点赞 {meta.get('点赞', '?')})
> **生成方式**: Skill 4 v0.6 writer.py (reverse_prompt + DeepSeek-flash)
> **生成时间**: 2026-06-09

---

{llm_output}

---

## 🔧 后续步骤

- [ ] **人工审校** — LLM 输出仅供骨架, 发布前必看 (尤其 9 tag 是否合规)
- [ ] **封面图** — 用 文生图 skill 生成 3:4 封面 (1080x1440)
- [ ] **实测发布** — 建议晚 8-10 点发, 24h 后看数据
- [ ] **A/B 测试** — 用 rewriter.py v0.3 生成备选标题, 7 天看胜率
"""
    return fm


# ============================================================
# Main
# ============================================================

def main() -> int:
    p = argparse.ArgumentParser(
        description="Skill 4 v0.6 writer — 用 reverse_prompt 调 LLM 写仿写笔记"
    )
    p.add_argument("--reverse-prompt", required=True, help="reverse_prompt.md 路径")
    p.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR))
    p.add_argument("--no-llm", action="store_true", help="只生成 prompt, 不调 LLM")
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = Path(args.reverse_prompt)
    print(f"\n=== Skill 4 v0.6 writer ===")
    print(f"reverse_prompt: {md_path}")

    # 1. 解析
    reverse = parse_reverse_prompt(md_path)
    note_id = reverse["meta"].get("note_id", "unknown")
    print(f"  ✓ 5 段解析完")
    print(f"  note_id: {note_id}")

    # 检查 {{待填}} 提示
    has_pending = any("{{待填" in v for v in reverse["sections"].values())
    if has_pending:
        print(f"\n  ⚠️ 5 段里有 {{待填}} 槽位未填, 建议先手动填 (用 Edit 工具), 再跑 writer")
        print(f"     或: 用 LLM 自动填 (但质量不如人工)")

    # 2. 构造 prompt
    user_prompt = build_writer_prompt(reverse)
    if args.no_llm:
        print(f"\n>>> --no-llm: 只输出 prompt, 不调 LLM")
        prompt_path = out_dir / f"{note_id}-writer-prompt.md"
        prompt_path.write_text(
            f"# Skill 4 v0.6 writer prompt\n\n```\n{user_prompt}\n```\n",
            encoding="utf-8",
        )
        print(f"  ✓ {prompt_path}")
        return 0

    # 3. 调 LLM
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("ERROR: 需要 DEEPSEEK_API_KEY (或 --no-llm)", file=sys.stderr)
        return 1

    print(f"\n>>> DeepSeek 仿写 (max_tokens=2000)")
    llm_out = call_deepseek(user_prompt)
    if not llm_out:
        print("ERROR: LLM 返回空, 仿写失败", file=sys.stderr)
        return 1

    # 4. 输出
    md = render_imitate_md(reverse["meta"], llm_out)
    out_path = out_dir / f"{note_id}-imitate.md"
    out_path.write_text(md, encoding="utf-8")
    print(f"  ✓ {out_path} ({len(md) // 1024} KB)")

    # 5. 把构造的 prompt 也存一份 (供后续 A/B 测试用)
    prompt_path = out_dir / f"{note_id}-writer-prompt.md"
    prompt_path.write_text(
        f"# Skill 4 v0.6 writer prompt\n\n```\n{user_prompt}\n```\n",
        encoding="utf-8",
    )
    print(f"  ✓ {prompt_path}")

    print(f"\n=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
