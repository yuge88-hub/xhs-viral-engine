"""
skill-4-viral-rewriter v0.3
输入痛点 → 输出爆款仿写骨架

Usage:
    python rewriter.py --keyword "AI 副业" --pain "切记，真能赚钱的不会和你说的" --likes 535 --source "五个副业我全踩了，亏了快四千..."

Auto-detects action trigger (V/H/C/B/S) and body template (A/B/C).
Picks main title formula + 3 alternatives for A/B testing.

Time: 5s/run (vs 30min manual in v0.2)
"""
import argparse
import sys
import io
from pathlib import Path

# 修 Windows GBK 终端乱码（POSTMORTEM #17）
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# === 配置数据 ===

# 行动触发 → Body 模板 映射
TRIGGER_TO_TEMPLATE = {
    "V": "A",  # V 求证 → 模板 A (反常识揭露)
    "H": "B",  # H 犹豫 → 模板 B (分群干货)
    "C": "A",  # C 吐槽 → 模板 A (反常识揭露)
    "B": "C",  # B 求带 → 模板 C (政策红利)
    "S": "A",  # S 炫耀 → 模板 A (反常识揭露)
}

# 默认主标题公式（按 trigger 选最匹配的）
DEFAULT_TITLE_FORMULA = {
    "V": "B",  # 求证 → 反常识断言
    "H": "C",  # 犹豫 → 痛点+方案
    "C": "B",  # 吐槽 → 反常识断言
    "B": "D",  # 求带 → 政策/红利
    "S": "A",  # 炫耀 → 数字结果
}

TRIGGER_DESC = {
    "V": "求证型 - 读者质疑真伪/求真相",
    "H": "犹豫型 - 读者想试但有顾虑",
    "C": "吐槽型 - 读者抱怨/批判",
    "B": "求带型 - 读者直接求方法",
    "S": "炫耀型 - 读者分享成功经历",
}

TITLE_FORMULAS = {
    "A": "数字结果型: [反差点1]➡[反差点2]｜[结果]！附[方案]",
    "B": "反常识断言型: [反常识判断]！",
    "C": "痛点+方案型: [反常识归因]才是[症状]根源❗️[方案]",
    "D": "政策/红利型: [权威事件]！[人群] [红利] 已来！！",
    "E": "教程/SOP 型: [极致效率词]！[教程/SOP]，[人群限定]",
}

# 自动检测行动触发（启发式 ~70% 准确率，不确定时默认 H）
def detect_trigger(pain_text: str) -> str:
    text = pain_text.lower()
    # V 求证型: 切记/真能/割韭菜/骗/假/真的/没那么/怀疑
    if any(w in text for w in ["切记", "真能", "割韭菜", "骗子", "假的", "真的", "没那么", "怀疑", "智商税"]):
        return "V"
    # B 求带型: 求/怎么/有没有/教我/在哪
    if any(w in text for w in ["求带", "求", "怎么", "有没有", "能分享", "在哪买", "教我", "带带"]):
        return "B"
    # C 吐槽型: 骗子/割/坑/失败/放弃/没收益/不容易
    if any(w in text for w in ["骗子", "割韭菜", "坑", "失败", "放弃", "没收益", "不容易", "难"]):
        return "C"
    # S 炫耀型: 我赚/我做/我用了/我成功/我坚持/我知道
    if any(w in text for w in ["我赚", "我做", "我用了", "我成功", "我坚持", "我知道", "我用了", "我月入"]):
        return "S"
    # H 犹豫型: default
    return "H"


# === Body 模板 ===

BODY_TEMPLATE_A = """# {keyword} 仿写 v0.3 (模板 A - 反常识揭露型)

> **参考 v0.1 仿写**: AI 副业 用了相同模板（[../skill-4-formula-rewrites-v0.1/rewrites/AI副业.md](file:///C:/Users/张哥/Downloads/web-clipper-master/output/skill-4-formula-rewrites-v0.1/rewrites/AI副业.md)）

## 📥 输入

- **关键词**: {keyword}
- **核心痛点**: {pain_text}
- **来源**: {pain_source} ({likes} 赞)
- **行动触发**: {trigger} - {trigger_desc}
- **主标题公式**: {main_formula} - {formula_desc}
- **备选公式**: {alt1}, {alt2}, {alt3}
- **Body 模板**: A (反常识揭露)

---

## 📝 标题

**主标题**: [TODO: 套公式 {main_formula} = {formula_desc}]

**备选 1** (公式 {alt1}): [TODO]
**备选 2** (公式 {alt2}): [TODO]
**备选 3** (公式 {alt3}): [TODO]

---

## 📝 正文骨架

### [Hook - 反常识断言开场]

> **v0.1 参考**: "你去小红书搜 AI 副业，跳出来的全是'月入 5 万'、'3 个月涨粉 8W'。你是不是也心动了？听我说完这 5 个真相再决定！🔥"

[TODO: 用 1-2 句话写反常识结论 + 制造认知冲突]

### [痛点放大 - 引用评论]

> "{pain_text}" ({likes} 赞)

[TODO: 解释为什么这条评论代表读者最痛的点（1-2 句）]

### [过渡 - 制造悬念]

> **v0.1 参考**: "今天就扒给你看！"

[TODO: 1 句话过渡到正文 N 个真相]

### 01 [第 1 个真相/元凶]

> **v0.1 参考**: "真相一：90% 教 AI 副业的人，自己就是割韭菜的。"

[TODO: 现象描述 1 行]
[TODO: 数据/案例 1-2 行]
**[金句压底]** [TODO: 1 句情绪最重的话]

### 02 [第 2 个真相]

[同上结构]

### 03 [第 3 个真相]

[同上结构]

### [可选 - 04/05 额外真相]

[同上结构]

### [转折 - "真相 X：不是不能做，是..."]

[TODO: 1 句话给希望]

### [CTA - 行动触发]

> **v0.1 参考**: "评论区扣'我准备好了'，我整理了 3 类人的 AI 副业实操路径。先收藏，转发给那个天天想 AI 副业的朋友。别让他再被割了。✊"

[TODO: 评论区扣 [关键词] / 转发给 [人群] / 先收藏 [惩罚语]]

---

## 🏷️ 9 Tag

[TODO: 1 大词 + 2 中词 + 3 长尾 + 3 情绪/场景]
模板: #{keyword} #副业 #赚钱 #[长尾词1] #[长尾词2] #[长尾词3] #[场景1] #[场景2] #[场景3]

---

## ✅ mimeng 自检清单

- [ ] 至少 10 个感叹号
- [ ] 至少 1 个反问句
- [ ] "你" 字 ≥ 50 次
- [ ] 至少 3 个具体细节（人名/场景/神态）
- [ ] 没有禁用词 (综上所述/赋能/闭环/可能/似乎/我们认为)
- [ ] 段落 ≤ 150 字
- [ ] 结尾是全文情绪最重的句子
"""


BODY_TEMPLATE_B = """# {keyword} 仿写 v0.3 (模板 B - 分群干货型)

> **参考 v0.1 仿写**: 营养食疗 / 减肥 用了相同模板

## 📥 输入

- **关键词**: {keyword}
- **核心痛点**: {pain_text}
- **来源**: {pain_source} ({likes} 赞)
- **行动触发**: {trigger} - {trigger_desc}
- **主标题公式**: {main_formula} - {formula_desc}
- **备选公式**: {alt1}, {alt2}, {alt3}
- **Body 模板**: B (分群干货)

---

## 📝 标题

**主标题**: [TODO: 套公式 {main_formula} = {formula_desc}]

**备选 1** (公式 {alt1}): [TODO]
**备选 2** (公式 {alt2}): [TODO]
**备选 3** (公式 {alt3}): [TODO]

---

## 📝 正文骨架

### [Hook - 反常识发现]

> **v0.1 参考**: "你是不是也这样？看到博主推荐'五红汤'养气血，赶紧买材料煮来喝。结果呢？嗓子干、爆痘、上火、月经推迟——越补越虚了！🤯"

[TODO: 1-2 句反常识发现]

### [痛点共鸣 - 引用评论]

> "{pain_text}" ({likes} 赞)

### [反问 - "是不是你？"]

[TODO: 1 句话反问]

### [自测 - 3-5 个症状]

- [症状 1]
- [症状 2]
- [症状 3]
- [症状 4]
- [症状 5]

（如有 3 条 → 你就是 [类型 1]）

### 01 [类型 1 名称]

**自测**:
- [症状 A]
- [症状 B]

**错的做法**: [TODO]

**正确做法**:
- [动作 1]
- [动作 2]
- [动作 3]
- [动作 4]

**[金句压底]** [TODO]

### 02 [类型 2 名称]

[同上结构]

### 03 [类型 3 名称]

[同上结构]

### [警告 - 顺序/搭配错了 = 灾难]

[TODO: 1-2 句警告]

### [CTA]

> **v0.1 参考**: "评论区告诉我你的体质（湿热/虚寒/痰湿），我发你对应的 7 天食谱。先收藏！别下次又乱喝五红汤了！💪"

[TODO: 评论区告诉我你的 [类型] / 收藏]

---

## 🏷️ 9 Tag

[TODO: 1 大词 + 2 中词 + 3 长尾 + 3 情绪/场景]

---

## ✅ mimeng 自检清单

- [ ] 至少 10 个感叹号
- [ ] 至少 1 个反问句
- [ ] "你" 字 ≥ 50 次
- [ ] 至少 3 个具体细节
- [ ] 没有禁用词
- [ ] 段落 ≤ 150 字
"""


BODY_TEMPLATE_C = """# {keyword} 仿写 v0.3 (模板 C - 政策红利型)

> **参考 v0.1 仿写**: 自媒体 用了相同模板

## 📥 输入

- **关键词**: {keyword}
- **核心痛点**: {pain_text}
- **来源**: {pain_source} ({likes} 赞)
- **行动触发**: {trigger} - {trigger_desc}
- **主标题公式**: {main_formula} - {formula_desc}
- **备选公式**: {alt1}, {alt2}, {alt3}
- **Body 模板**: C (政策红利)

---

## 📝 标题

**主标题**: [TODO: 套公式 {main_formula} = {formula_desc}]

**备选 1** (公式 {alt1}): [TODO]
**备选 2** (公式 {alt2}): [TODO]
**备选 3** (公式 {alt3}): [TODO]

---

## 📝 正文骨架

### [Hook - 数据冲击 + 羡慕评论]

> **v0.1 参考**: "你看到那个爆款了吗——'小红书新政策！普通人做自媒体新红利已来！！'47K 赞！评论区第一句话震碎我——'感觉你们是真能发财，我听到机制已经困了。'1645 赞。"

[TODO: 1 句震撼数据 + 1 句羡慕评论]

### [反问 - "真传一句话，假传万卷书"]

[TODO: 1 句反问]

### [承诺 - 建立信任]

> **v0.1 参考**: "今天不教你怎么月入过万，只教你 5 个真正能接住的 2026 红利。全是实操路径，看完就能干！🔥"

[TODO: "今天不教你 X，只教 [N] 个 [具体价值]"]

### 01 [红利 1 名称]

**为什么是红利**: [TODO: 数据/算法变化 1-2 句]

**3 个必杀技**:
- [动作 1]
- [动作 2]
- [动作 3]

**[金句压底]** [TODO]

### 02 [红利 2 名称]

[同上结构]

### 03 [红利 3 名称]

[同上结构]

### 04 [红利 4 名称]

[同上结构]

### 05 [红利 5 名称]

[同上结构]

### [总结 - N 个真相]

> **v0.1 参考**: "2026 年自媒体，5 个真相——完播率 > 粉丝数、深度互动 > 互动数量、垂直深耕 > 全能选手、100 铁粉 > 10 万泛粉、小而美 > 大爆款。"

[TODO: 1-2 句总结]

### [CTA]

> **v0.1 参考**: "评论区扣你的'赛道'（家居/早餐/穿搭/读书/宠物），我发你对应的'100 天爆款计划'。先收藏！2026 看完这一篇就够了！✊"

[TODO: 评论区扣你的 [赛道] / 关注下篇]

---

## 🏷️ 9 Tag

[TODO: 1 大词 + 2 中词 + 3 长尾 + 3 情绪/场景]

---

## ✅ mimeng 自检清单

- [ ] 至少 10 个感叹号
- [ ] 至少 1 个反问句
- [ ] "你" 字 ≥ 50 次
- [ ] 至少 3 个具体细节
- [ ] 没有禁用词
- [ ] 段落 ≤ 150 字
"""


BODY_TEMPLATES = {"A": BODY_TEMPLATE_A, "B": BODY_TEMPLATE_B, "C": BODY_TEMPLATE_C}


# === Main ===

def main():
    parser = argparse.ArgumentParser(
        description="Skill 4 v0.3 爆款仿写骨架生成器 - 输入痛点 → 输出可填空骨架"
    )
    parser.add_argument("--keyword", required=True, help="目标关键词 (e.g. 'AI 副业')")
    parser.add_argument("--pain", required=True, help="核心痛点文本（直接粘贴评论）")
    parser.add_argument("--likes", type=int, default=0, help="痛点点赞数")
    parser.add_argument("--source", default="未指定", help="痛点来源 (note title)")
    parser.add_argument(
        "--trigger", choices=["V", "H", "C", "B", "S"],
        help="行动触发 (V/H/C/B/S), 不传则自动检测（启发式 ~70%% 准确率）"
    )
    parser.add_argument(
        "--title-formula", choices=["A", "B", "C", "D", "E"],
        help="主标题公式, 不传则按 trigger 自动选"
    )
    parser.add_argument(
        "--body-template", choices=["A", "B", "C"],
        help="Body 模板, 不传则按 trigger 自动选 (V→A / H→B / C→A / B→C / S→A)"
    )
    parser.add_argument(
        "--out",
        help="输出文件路径, 默认 output/skill-4-formula-rewrites-v0.3/<keyword>.md"
    )
    args = parser.parse_args()

    # 1. Auto-detect
    trigger = args.trigger or detect_trigger(args.pain)
    body_template = args.body_template or TRIGGER_TO_TEMPLATE[trigger]

    # 2. Pick title formulas
    all_formulas = ["A", "B", "C", "D", "E"]
    main_formula = args.title_formula or DEFAULT_TITLE_FORMULA[trigger]
    alts = [f for f in all_formulas if f != main_formula]
    alt1, alt2, alt3 = alts[0], alts[1], alts[2]

    # 3. Render template
    template = BODY_TEMPLATES[body_template]
    content = template.format(
        keyword=args.keyword,
        pain_text=args.pain,
        pain_source=args.source,
        likes=args.likes,
        trigger=trigger,
        trigger_desc=TRIGGER_DESC[trigger],
        main_formula=main_formula,
        alt1=alt1,
        alt2=alt2,
        alt3=alt3,
        formula_desc=TITLE_FORMULAS[main_formula],
    )

    # 4. Output
    if args.out:
        out_path = Path(args.out)
    else:
        out_dir = Path("output/skill-4-formula-rewrites-v0.3")
        out_dir.mkdir(parents=True, exist_ok=True)
        # Sanitize keyword for filename
        safe_keyword = args.keyword.replace("/", "_").replace("\\", "_").strip()
        out_path = out_dir / f"{safe_keyword}.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")

    # 5. Print summary
    print(f"\n{'='*60}")
    print(f"✅ 仿写骨架已生成")
    print(f"{'='*60}")
    print(f"📄 文件: {out_path}")
    print(f"🔑 关键词: {args.keyword}")
    print(f"🎯 行动触发: {trigger} - {TRIGGER_DESC[trigger]}")
    print(f"📐 Body 模板: {body_template}")
    print(f"📝 主标题公式: {main_formula} - {TITLE_FORMULAS[main_formula]}")
    print(f"📝 备选公式: {alt1}, {alt2}, {alt3}")
    print(f"\n⏭️  下一步:")
    print(f"   1. 用编辑器打开 {out_path}")
    print(f"   2. 把 [TODO: ...] 替换成你的内容（参考 v0.1 仿写）")
    print(f"   3. 按 mimeng 自检清单过一遍")
    print(f"   4. 复制到 xhs 发布")
    print()


if __name__ == "__main__":
    main()
