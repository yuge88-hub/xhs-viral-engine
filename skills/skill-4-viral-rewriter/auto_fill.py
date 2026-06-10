"""
skill-4-viral-rewriter v0.4
auto_fill.py — 用 DeepSeek API 把 [TODO: ...] 骨架填成完整仿写

Usage:
    # 设置 API key (一次性, 不写盘)
    $env:DEEPSEEK_API_KEY="sk-xxx..."

    # 填 1 个骨架
    python auto_fill.py --in output/skill-4-formula-rewrites-v0.3/AI_副业.md

    # 批量填目录
    python auto_fill.py --batch output/skill-4-formula-rewrites-v0.3/

依赖:
    pip install requests
"""
import argparse
import os
import re
import sys
import io
import json
from pathlib import Path
from datetime import datetime

# 修 Windows GBK 终端乱码（POSTMORTEM #17）
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# === API 配置 ===
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not API_KEY:
    print("❌ 错误: 环境变量 DEEPSEEK_API_KEY 未设置")
    print("   PowerShell: $env:DEEPSEEK_API_KEY=\"sk-xxx...\"")
    print("   Bash: export DEEPSEEK_API_KEY=\"sk-xxx...\"")
    print("   或建 .env 文件, 复制 .env.example 模板")
    sys.exit(1)

API_BASE = "https://api.deepseek.com/v1"
API_MODEL = "deepseek-v4-flash"  # 用户指定

# v0.1 仿写参考 (用于 in-context learning, 按 template 分发)
V01_REFS = {
    "A": (Path(__file__).parent.parent.parent / "output/skill-4-formula-rewrites-v0.1/rewrites/AI副业.md").read_text(encoding="utf-8")[:2000],
    "B": (Path(__file__).parent.parent.parent / "output/skill-4-formula-rewrites-v0.1/rewrites/营养食疗.md").read_text(encoding="utf-8")[:2000],
    "C": (Path(__file__).parent.parent.parent / "output/skill-4-formula-rewrites-v0.1/rewrites/自媒体.md").read_text(encoding="utf-8")[:2000],
}


# === Mimeng 风格指南 (压缩) ===
MIMENG_RULES = """
[风格铁律 = mimeng 风格]
1. 每句 ≤ 2 行
2. 感叹号至少 10 个/篇 (集中爆发, 不均摊)
3. 反问句每 300 字 ≥ 1 个 ("不能吗？！" "凭什么？！" "你说是不是？")
4. 排比堆叠 (同类论据用 3+ 个 "你 XXX..." 排列)
5. 短句结尾必是金句 (每段最后一句语气最重)
6. 编号章节 01/02/03 (不用"首先其次最后")
7. 换行 = 情绪切换; 空行 = 故事→议论
8. "你" 字 ≥ 50 次/篇 (每 100 字 ≥ 3 个)
9. 极端判断 (不用"虽然...但是")
10. 禁用词: 综上所述/赋能/闭环/可能/也许/我们认为/一方面
11. 段落 ≤ 150 字
12. 结尾是全文情绪最重的句子, 不收尾直接扔出去
"""


# === Prompt 构建 ===

def build_prompt(skeleton_md: str, keyword: str) -> tuple[str, str]:
    """
    从 skeleton_md 提取:
    - 行动触发
    - Body 模板
    - 标题公式
    - 痛点
    然后构建 prompt
    """
    # 提取 trigger
    trigger_match = re.search(r"行动触发[::]\s*([A-Z])\s*-\s*([^\n]+)", skeleton_md)
    trigger = trigger_match.group(1) if trigger_match else "H"
    trigger_desc = trigger_match.group(2).strip() if trigger_match else ""

    # 提取 body template
    template_match = re.search(r"Body 模板[::]\s*([ABC])", skeleton_md)
    template = template_match.group(1) if template_match else "A"

    # 提取主标题公式
    main_formula_match = re.search(r"主标题公式[::]\s*([ABCDE])", skeleton_md)
    main_formula = main_formula_match.group(1) if main_formula_match else "B"

    # 提取痛点
    pain_match = re.search(r"核心痛点[::]\s*([^\n]+)", skeleton_md)
    pain = pain_match.group(1).strip() if pain_match else ""

    # 选 v0.1 参考
    v01_ref = V01_REFS.get(template, V01_REFS["A"])

    # 提取 [TODO: ...] 段落 (排除标题里的 TODO 标记)
    # 找标题 + 正文骨架 (从 ## 📝 标题 到 ## 🏷️ 9 Tag 之前)
    body_match = re.search(
        r"(## 📝 标题\s*\n.*?)(?=\n## 🏷️|\Z)",
        skeleton_md,
        re.DOTALL,
    )
    body_skeleton = body_match.group(1).strip() if body_match else skeleton_md

    # 提取 9 tag 模板
    tag_match = re.search(
        r"## 🏷️ 9 Tag\s*\n(.*?)(?=\n## ✅|\Z)",
        skeleton_md,
        re.DOTALL,
    )
    tag_skeleton = tag_match.group(1).strip() if tag_match else ""

    system_prompt = f"""你是小红书爆款写手。风格 = mimeng 闺蜜嘴替 + 情绪发射器。

{MIMENG_RULES}

[输入]
- 关键词: {keyword}
- 核心痛点: {pain}
- 行动触发: {trigger} - {trigger_desc}
- Body 模板: {template} (从 v0.1 范本学结构)
- 标题公式: {main_formula}

[v0.1 同模板范本 (200 字节选)]
{v01_ref}

[任务]
把下面骨架中的 **所有 [TODO: ...] 包括标题部分** 替换成 mimeng 风格的具体内容。
- 保留骨架的章节结构
- **主标题**: 直接写一行具体标题, 套公式 {main_formula}
- **备选 1/2/3**: 各写一行具体标题, 用其他公式
- **正文每个 [TODO: xxx]**: 替换为 1-3 行的 mimeng 风格内容
- **9 Tag**: 替换成 9 个真实 tag (#xxx), 1 大词 + 2 中词 + 3 长尾 + 3 情绪/场景
- 移除所有 [TODO: ...] 标记
- 保留 ## 标题结构
- 输出**纯 markdown**, 不要解释, 不要前缀说明
- mimeng 自检清单的复选框保持原样

[骨架]
{body_skeleton}

[9 Tag 骨架]
{tag_skeleton}
"""

    user_prompt = f"输出完整填好的仿写（保持骨架结构，替换所有 [TODO: ...]）。"

    return system_prompt, user_prompt


# === API 调用 ===

def call_deepseek(system_prompt: str, user_prompt: str, max_retries: int = 2) -> str:
    """调用 DeepSeek API，返回生成内容"""
    import requests

    url = f"{API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": API_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.85,
        "max_tokens": 4000,
        "stream": False,
    }

    for attempt in range(max_retries + 1):
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            return content, usage
        except requests.exceptions.RequestException as e:
            if attempt < max_retries:
                print(f"⚠️  API 错误 (重试 {attempt+1}/{max_retries}): {e}")
                continue
            raise


# === Main ===

def fill_skeleton(in_path: Path, out_path: Path = None) -> dict:
    """填 1 个骨架文件"""
    if not in_path.exists():
        raise FileNotFoundError(f"骨架文件不存在: {in_path}")

    # 从文件名推断 keyword
    keyword = in_path.stem

    # 读骨架
    skeleton_md = in_path.read_text(encoding="utf-8")

    # 提取 keyword (优先从骨架里读)
    kw_match = re.search(r"^- \*\*关键词\*\*:\s*([^\n]+)", skeleton_md, re.MULTILINE)
    if kw_match:
        keyword = kw_match.group(1).strip()

    print(f"\n🔄 正在填: {in_path.name}")
    print(f"   关键词: {keyword}")

    # 构建 prompt
    system_prompt, user_prompt = build_prompt(skeleton_md, keyword)

    # 调用 API
    content, usage = call_deepseek(system_prompt, user_prompt)

    # 拼回完整文件 (保留头部 + 替换正文)
    # 头部只到 ## 📝 标题 之前 (输入 + 命令行, 不含骨架部分)
    head_match = re.search(
        r"^(.*?)(?=\n## 📝 标题)",
        skeleton_md,
        re.DOTALL,
    )
    head = head_match.group(1).rstrip() if head_match else ""

    # 9 Tag 之后到 mimeng 自检清单
    tail_match = re.search(
        r"(## ✅ mimeng 自检清单.*)",
        skeleton_md,
        re.DOTALL,
    )
    tail = tail_match.group(1) if tail_match else ""

    # 拼装
    filled = f"{head}\n\n## 📝 仿写正文 (auto-filled)\n\n{content.strip()}\n\n---\n\n_{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 用 deepseek-v4-flash 自动填_\n\n{tail}"

    # 后处理: 清理模型可能残留的元数据
    filled = re.sub(r"^\[9 Tag 骨架\]\s*\n", "", filled, flags=re.MULTILINE)
    filled = re.sub(r"^\[Tag 骨架\]\s*\n", "", filled, flags=re.MULTILINE)

    # 写文件
    if not out_path:
        out_path = in_path.with_name(in_path.stem + ".filled.md")
    out_path.write_text(filled, encoding="utf-8")

    print(f"✅ 已生成: {out_path}")
    if usage:
        print(f"   Token: {usage.get('total_tokens', '?')} (in: {usage.get('prompt_tokens', '?')}, out: {usage.get('completion_tokens', '?')})")

    return {
        "in": str(in_path),
        "out": str(out_path),
        "keyword": keyword,
        "usage": usage,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Skill 4 v0.4 - 用 DeepSeek API 自动填仿写骨架"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--in", dest="input", help="单个骨架 .md 文件")
    group.add_argument("--batch", help="批量处理目录 (填所有 .md 但非 .filled.md)")
    args = parser.parse_args()

    results = []

    if args.input:
        results.append(fill_skeleton(Path(args.input)))
    else:
        batch_dir = Path(args.batch)
        for md_file in sorted(batch_dir.glob("*.md")):
            if md_file.name.endswith(".filled.md"):
                continue
            if md_file.name == "README.md":
                continue
            try:
                results.append(fill_skeleton(md_file))
            except Exception as e:
                print(f"❌ 失败: {md_file.name} - {e}")

    # 汇总
    print(f"\n{'='*60}")
    print(f"✅ 批量完成: {len(results)} 个文件")
    print(f"{'='*60}")
    total_tokens = sum(r["usage"].get("total_tokens", 0) for r in results if r.get("usage"))
    print(f"📊 总 Token 消耗: {total_tokens}")
    if total_tokens:
        # DeepSeek v4-flash 估算 ¥0.0005/1k tokens
        cost = (total_tokens / 1000) * 0.0005
        print(f"💰 估算成本: ¥{cost:.4f}")
    print()


if __name__ == "__main__":
    main()
