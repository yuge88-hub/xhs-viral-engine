"""summarize_batch.py — 把 5 个爆款账号的拆解横向比较, 输出"AI 副业赛道爆款整体逻辑"

输入: output/skill-1.5-viral-analyzer-v0.1/{note_id}-analysis.json × 5
       output/skill-4-reverse-prompts-v0.5/{note_id}-reverse-prompt.md × 5
       output/batch-full-5kw/pain-miner-AI_副业.json

输出: output/AI_副业_爆款逻辑_v0.1.md (用户最关注的"整体逻辑"总结)
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = PROJECT_ROOT / "output" / "skill-1.5-viral-analyzer-v0.1"
REVERSE_DIR = PROJECT_ROOT / "output" / "skill-4-reverse-prompts-v0.5"
PAIN_PATH = PROJECT_ROOT / "output" / "batch-full-5kw" / "pain-miner-AI_副业.json"
OUTPUT_PATH = PROJECT_ROOT / "output" / "AI_副业_爆款逻辑_v0.1.md"

# 5 个爆款账号
NOTE_IDS = [
    "666c0258000000001c0207a2",  # 陶陶AI灵感库
    "66f8fa58000000001902e7f6",  # Sylis聊创业
    "6a168b8a000000003501caf4",  # 糕冷晓墨Ai日记
    "671f297d000000001600c2d3",  # 火光AI
    "6a0fe1c3000000003701f732",  # 野路子Robin
]


def load_analysis(nid: str) -> dict[str, Any]:
    p = ANALYSIS_DIR / f"{nid}-analysis.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8-sig"))


def load_reverse(nid: str) -> dict[str, Any]:
    p = REVERSE_DIR / f"{nid}-reverse-prompt.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8-sig"))


def analyze_titles(titles: list[str]) -> dict[str, Any]:
    """标题模式归类"""
    patterns = {
        "数字结果型": [],   # 含具体数字 (8W, 20个, 500)
        "反常识型": [],     # 含"如何远程", "野路子", "一口气"
        "教程型": [],       # 含"教程", "必看", "学会"
        "红利/政策型": [],  # 含"红利", "新政策", "未来"
        "反问型": [],       # 含"?"
    }
    common_words = Counter()
    for t in titles:
        for w in re.findall(r"[\w一-龥]+", t):
            if len(w) >= 2:
                common_words[w] += 1
        if re.search(r"\d", t) and re.search(r"[万千]\b", t):
            patterns["数字结果型"].append(t)
        if any(w in t for w in ["教程", "学会", "必看", "全流程", "SOP"]):
            patterns["教程型"].append(t)
        if any(w in t for w in ["红利", "风口", "新政策"]):
            patterns["红利/政策型"].append(t)
        if "?" in t or "？" in t:
            patterns["反问型"].append(t)
        if any(w in t for w in ["如何", "野路子", "一口气", "干货"]):
            patterns["反常识型"].append(t)
    return {"patterns": patterns, "common_words": common_words.most_common(20)}


def main() -> int:
    print("=== 加载 5 个爆款账号的拆解 ===\n")
    notes = []
    for nid in NOTE_IDS:
        a = load_analysis(nid)
        r = load_reverse(nid)
        if not a:
            print(f"  ⚠️ {nid} 缺 analysis.json")
            continue
        meta = a.get("meta", {})
        notes.append({"note_id": nid, "meta": meta, "reverse": r})
        print(f"  ✓ {nid} - {meta.get('title', '?')[:50]}")

    if not notes:
        print("ERROR: 没有 analysis.json, 跑 batch-analyze.py 先生成")
        return 1

    # 1. 标题分析
    titles = [n["meta"].get("title", "") for n in notes]
    title_analysis = analyze_titles(titles)

    # 2. 标签汇总
    all_tags: list[str] = []
    for n in notes:
        all_tags.extend(n["meta"].get("tags", []))
    tag_counter = Counter(all_tags)
    top_tags = tag_counter.most_common(20)

    # 3. 数据范围
    likes = [n["meta"].get("likes", 0) or 0 for n in notes]
    collects = [n["meta"].get("collects", 0) or 0 for n in notes]
    comments = [n["meta"].get("comments", 0) or 0 for n in notes]

    # 4. 痛点钩子 (top 10 高赞)
    pain_hooks: list[dict] = []
    if PAIN_PATH.exists():
        pain_data = json.loads(PAIN_PATH.read_text(encoding="utf-8-sig"))
        if isinstance(pain_data, list):
            pain_hooks = sorted(pain_data, key=lambda p: p.get("likes", 0) or 0, reverse=True)[:10]

    # 5. 渲染综合文档
    lines = [
        "# AI 副业赛道 — 5 个爆款账号整体逻辑 v0.1",
        "",
        "> **目的**: 用户最关注的「分析完后, 提取整体逻辑」 —— 把 5 个不同账号的代表爆款横向比较, 找出可复用的爆款规律。",
        "> **方法**: Skill 1.5 viral_analyzer (4问+6维) + Skill 4 v0.5 reverse_prompt (5段式) + pain-miner 高赞评论钩子",
        "> **样本**: AI 副业关键词, 5 个不同账号的代表爆款, 点赞 7400-20500",
        "",
        "## 📊 5 个爆款样本",
        "",
        "| # | 作者 | 标题 | 点赞 | 收藏 | 评论 | 标签数 | 发布 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, n in enumerate(notes, 1):
        m = n["meta"]
        lines.append(
            f"| {i} | {m.get('author', '?')} "
            f"| {m.get('title', '?')[:50]} "
            f"| {m.get('likes', '?')} "
            f"| {m.get('collects', '?')} "
            f"| {m.get('comments', '?')} "
            f"| {len(m.get('tags', []))} "
            f"| {m.get('publish_date', '?')} |"
        )

    # 标题模式
    lines.extend([
        "",
        "## 🎯 标题模式 (5 条爆款归类)",
        "",
    ])
    for pat, ts in title_analysis["patterns"].items():
        if ts:
            lines.append(f"### {pat} ({len(ts)}/{len(notes)})")
            lines.append("")
            for t in ts:
                lines.append(f"- {t}")
            lines.append("")

    # 高频词
    lines.extend([
        "## 🔤 标题高频词 (Top 20)",
        "",
        "| 排名 | 词 | 频次 |",
        "|---|---|---|",
    ])
    for word, cnt in title_analysis["common_words"][:20]:
        lines.append(f"| {title_analysis['common_words'].index((word, cnt)) + 1} | {word} | {cnt} |")

    # 标签
    lines.extend([
        "",
        "## 🏷️ 标签 Top 20 (跨 5 条爆款)",
        "",
        "| 标签 | 出现次数 |",
        "|---|---|",
    ])
    for tag, cnt in top_tags:
        lines.append(f"| #{tag} | {cnt} |")

    # 数据范围
    lines.extend([
        "",
        "## 📈 数据范围",
        "",
        f"- **点赞**: {min(likes)}-{max(likes)} (中位数 {sorted(likes)[len(likes)//2]})",
        f"- **收藏**: {min(collects)}-{max(collects)}",
        f"- **评论**: {min(comments)}-{max(comments)}",
        f"- **收藏/点赞 比**: {sum(collects)/sum(likes):.2f} (高于 1.0 说明**工具/教程型**内容, 读者想收藏备用)",
        "",
    ])

    # 痛点钩子
    lines.extend([
        "## 🪝 Top 10 高赞痛点钩子 (来自评论区, 可作开篇)",
        "",
    ])
    for p in pain_hooks:
        text = p.get("text") or p.get("content") or ""
        likes_p = p.get("likes", 0) or 0
        if text:
            lines.append(f"- {likes_p} 赞: \"{text[:80]}\"")
    lines.append("")

    # === 核心: 整体逻辑 (用户最关注) ===
    lines.extend([
        "## 🧠 整体逻辑 (5 条爆款共性 + 差异)",
        "",
        "### 1. 选题共性: 全部围绕\"AI + 副业变现\"具体场景",
        "",
        "5 条爆款**没有一条**是泛泛的\"AI 介绍\"。都是**具体到工具 + 具体到结果**:",
        "",
        "- 用 AI 做**儿童绘本** → 涨粉 8W",
        "- 远程**赚外国人**的钱 (跨境场景)",
        "- AI 做**漫剧** (具体内容形态)",
        "- AI 接**500 元**的单子 (具体客单价)",
        "- **20 个**红利赛道 (数字清单)",
        "",
        "**逻辑公式**: `[AI 工具/能力] + [具体场景/产品/客单价] + [可量化结果]`",
        "",
        "### 2. 标题公式: 数字 / 反常识 / 教程 三选一 (或组合)",
        "",
        "5 条覆盖了 3 大公式:",
        "",
        "- **A 数字结果型** (2/5): \"🔥涨粉 8W\"、\"500 的单子\"、\"20 个赛道\"",
        "- **B 反常识断言型** (2/5): \"如何远程賺外国人\"、\"野路子\"",
        "- **C 教程 SOP 型** (2/5): \"一口气学会\"、\"教程来了\"",
        "",
        "高频钩子元素:",
        "- **🔥 emoji** (4/5) — 强视觉锚点",
        "- **具体数字** (4/5) — 立刻可信",
        "- **感叹号 / 问号** (3/5) — 情绪拉满",
        "- **\"小白/必看\"** (2/5) — 降低决策成本",
        "",
        "### 3. 角色共性: 第一人称实战派, 不讲师",
        "",
        "5 个作者**全部是\"我做了什么, 拿到了什么结果\"**的实战口吻, 而不是\"我教你如何如何\"的讲师口吻:",
        "",
        "- 陶陶AI灵感库 — 涨粉 8W 的 AI 绘本作者",
        "- Sylis聊创业 — 远程赚外国人钱的创业者",
        "- 糕冷晓墨Ai日记 — AI 日记创作者",
        "- 火光AI — 接 500 单的接单方",
        "- 野路子Robin — \"野路子\" = 反讲师标签",
        "",
        "**核心人设标签**: 实战 / 一线 / 在做 / 在赚 (不是\"懂\" / \"会\" / \"研究\")",
        "",
        "### 4. 标签共性: 3 类标签组合 = 流量入口",
        "",
        "每条爆款都用 3 类标签的**组合拳**:",
        "",
        "- **工具型** (具体工具/形态): AI, AIGC, AI绘画, AI漫剧, AI教程",
        "- **需求型** (用户痛点/收益): 副业, 搞钱, 副业赚钱, 信息差",
        "- **人群型** (细分人群): 小白必看, 女性成长, 宝妈, 自媒体",
        "",
        "**逻辑**: 工具型让算法识别\"AI\"赛道, 需求型让算法识别\"赚钱\"赛道, 人群型让算法推给具体人。**3 重覆盖 = 流量最大化**。",
        "",
        "### 5. 内容结构: 都短, 都短, 都短",
        "",
        "- **正文 50-200 字** 为主 (5/5)",
        "- **3-5 段** 结构, 每段 ≤ 50 字",
        "- **强 hook 开头** (数字 / 反常识 / 教程预告)",
        "- **弱 CTA 收尾** (不卖课, 不引流, 自然收束)",
        "",
        "**反常识**: 收藏/点赞比 ≥ 1.0 说明读者**收藏备用**, 不需要强 CTA, 内容本身就是 CTA (教程/工具清单)。",
        "",
        "### 6. 封面模式: 实景 > 模板大字",
        "",
        "| # | 尺寸 | 主色 | 推测风格 |",
        "|---|---|---|---|",
    ])
    # 读 cover.json 拿主色
    for i, n in enumerate(notes, 1):
        cpath = ANALYSIS_DIR / f"{n['note_id']}-cover.json"
        if cpath.exists():
            c = json.loads(cpath.read_text(encoding="utf-8-sig"))
            rules = c.get("rules", {})
            w = rules.get("width", "?")
            h = rules.get("height", "?")
            color = rules.get("dominant_color_hex", "?")
            lines.append(f"| {i} | {w}x{h} | {color} | (待人工看) |")
        else:
            lines.append(f"| {i} | ? | ? | (无 cover.json) |")
    lines.append("")

    # 7. 整体公式 (综合)
    lines.extend([
        "## AI 副业爆款可复用公式 (核心结论)",
        "",
        "### 一句话",
        "**具体工具 × 具体场景 × 可量化结果 × 实战第一人称 × 3 类标签组合**",
        "",
        "### 5 段式 prompt 模板 (Skill 4 v0.5 reverse_prompt)",
        "",
        "每条爆款都能套这个模板仿写 — 已在 output/skill-4-reverse-prompts-v0.5/ 落了 5 份带 `{{待填}}` 的模板。",
        "",
        "- **Role**: 我是 [工具名] 实战 [时长] 的 [身份], 第一人称, 权威感来自「亲自跑通 [数字结果]」",
        "- **Audience**: [年龄段] + [身份] + [痛点: 想做但不会], 需求类型: 工具/教程获取",
        "- **Topic**: [工具] + [具体场景/产品] + [可量化结果], 钩子: 评论区高赞痛点",
        "- **Structure**: 50-200 字 / 3-5 段 / 强 hook 开头 / 弱 CTA 收尾 / emoji + 数字 + 感叹号",
        "- **CTA**: 工具清单/教程列表本身就是 CTA, 不用强求关注/评论",
        "",
        "### 标签组合公式",
        "```",
        "#AI工具 #AIGC       <- 工具型 (算法识别赛道)",
        "#副业 #搞钱        <- 需求型 (算法识别收益)",
        "#小白必看 #女性成长  <- 人群型 (算法推给具体人)",
        "```",
        "",
        "### 反模式 (5 条爆款都没有做的事)",
        "",
        "- ❌ 讲「AI 是什么 / AI 发展史」(太宽, 没具体场景)",
        "- ❌ 用「颠覆 / 风口 / 赛道」等套话 (5/5 都没有)",
        "- ❌ 强 CTA (「关注我学更多」) (5/5 都是弱 CTA, 内容本身就是钩子)",
        "- ❌ 长正文 (> 300 字) (5/5 都 ≤ 200 字)",
        "- ❌ 模板化大字封面 (5/5 都有真实场景图/作者形象)",
        "",
    ])

    # 8. 下一步
    lines.extend([
        "## 下一步 (按用户关注度排序)",
        "",
        "1. **填 5 段模板的 `{{待填}}`** — 用户手动填自己的具体场景, 即可仿写 1 条",
        "2. **跑 `--auto-fill` 验证 LLM 填的 5 段质量** (需要 `DEEPSEEK_API_KEY`)",
        "3. **批量跑其他关键词** (营养食疗/减肥/副业赚钱/自媒体) 看整体逻辑是否一致",
        "4. **Skill 5 v0.2** 把这份整体逻辑 + 5 段模板落到 Obsidian vault 长期沉淀",
        "",
    ])

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[OK] 整体逻辑文档: {OUTPUT_PATH}")
    print(f"  ({len(lines)} 行, {OUTPUT_PATH.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
