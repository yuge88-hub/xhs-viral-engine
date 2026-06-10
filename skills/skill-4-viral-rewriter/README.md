# Skill 4 v0.3 — Viral Rewriter 自动化脚本

> **输入痛点 → 输出爆款仿写骨架**
> **耗时**：5 秒/条（vs v0.2 30 分钟手动）
> **核心**：3 个 body 模板 + 5 类标题公式 + 行动触发自动检测

---

## 🚀 快速使用

### 最简调用（auto-detect 一切）

```powershell
cd "C:\Users\张哥\Downloads\web-clipper-master"
python skills\skill-4-viral-rewriter\rewriter.py `
  --keyword "AI 副业" `
  --pain "切记，真能赚钱的不会和你说的" `
  --likes 535 `
  --source "五个副业我全踩了，亏了快四千..."
```

### 显式指定（更精准）

```powershell
python skills\skill-4-viral-rewriter\rewriter.py `
  --keyword "减肥" `
  --pain "我有点崩溃，这几天吃的很干净就是不怎么掉" `
  --likes 13 `
  --source "年后减肥｜同样120斤｜感受体脂率的变化" `
  --trigger H `
  --body-template B `
  --title-formula C
```

### 自定义输出路径

```powershell
python skills\skill-4-viral-rewriter\rewriter.py `
  --keyword "我的新选题" `
  --pain "求一个副业 SOP" `
  --trigger B `
  --out "D:\path\to\my.md"
```

---

## 📋 参数说明

| 参数 | 必填 | 说明 |
|---|---|---|
| `--keyword` | ✅ | 目标关键词（文件名用） |
| `--pain` | ✅ | 核心痛点（直接粘贴评论） |
| `--likes` | ❌ | 痛点点赞数（仅用于显示） |
| `--source` | ❌ | 痛点来源笔记标题 |
| `--trigger` | ❌ | 行动触发 V/H/C/B/S，**不传则自动检测** |
| `--title-formula` | ❌ | 主标题公式 A/B/C/D/E，**不传则按 trigger 自动选** |
| `--body-template` | ❌ | Body 模板 A/B/C，**不传则按 trigger 自动选** |
| `--out` | ❌ | 输出文件路径，**默认 `output/skill-4-formula-rewrites-v0.3/<keyword>.md`** |

---

## 🎯 行动触发（trigger）说明

| 缩写 | 类型 | 适用模板 | 自动检测关键词 |
|---|---|---|---|
| **V** | 求证型 | A (反常识揭露) | 切记/真能/割韭菜/骗子/假的 |
| **H** | 犹豫型 | B (分群干货) | (默认) |
| **C** | 吐槽型 | A (反常识揭露) | 骗子/坑/失败/放弃/没收益 |
| **B** | 求带型 | C (政策红利) | 求/怎么/有没有/教我/在哪买 |
| **S** | 炫耀型 | A (反常识揭露) | 我赚/我做/我用了/我成功 |

> **自动检测准确率约 70%**。当评论同时含多类词时，优先 V > C > B > S > H。**重要选题建议显式传 `--trigger`**。

---

## 📐 3 个 Body 模板

### 模板 A：反常识揭露型（5-7 段）
```
Hook (反常识) → 痛点放大 → 01-0N 真相 → 转折 → CTA
```
**适用**：V 求证型 / C 吐槽型 / S 炫耀型痛点
**范本**：v0.1 AI 副业 / 副业赚钱

### 模板 B：分群干货型（6-8 段）
```
Hook → 痛点共鸣 → 自测 → 01-0N 类型 (自测+方案) → 警告 → CTA
```
**适用**：H 犹豫型痛点（"我这种行不行"）
**范本**：v0.1 营养食疗 / 减肥

### 模板 C：政策红利型（7-9 段）
```
Hook (数据+羡慕) → 反问 → 承诺 → 01-0N 红利 (为什么+怎么做) → 总结 → CTA
```
**适用**：B 求带型痛点（"求方法"）
**范本**：v0.1 自媒体

---

## 📝 5 类标题公式

| 公式 | 范本 | 适用 |
|---|---|---|
| **A 数字结果** | `130➡️90｜瘦了40斤换了种人生！` | 炫耀型 S |
| **B 反常识断言** | `正常人是做不好自媒体的` | 求证型 V / 吐槽型 C |
| **C 痛点+方案** | `内脏脂肪才是肚子胖的根源❗️懒人减肚子干货` | 犹豫型 H |
| **D 政策/红利** | `小红书新政策！普通人做自媒体新红利已来！！` | 求带型 B |
| **E 教程/SOP** | `一口气学会ai漫剧制作全流程，小白必看！` | 求带型 B |

---

## 🔄 完整工作流

```
Step 1: 从 output/batch-full-5kw/pain-miner-*.json 找 1 条痛点
        ↓
Step 2: 跑 rewriter.py（auto-detect 或显式指定 trigger/template）
        ↓
Step 3: 5 秒后 output/skill-4-formula-rewrites-v0.3/<keyword>.md 落盘
        ↓
Step 4: 编辑器打开，参考 v0.1 仿写 + 模板内的 [TODO: ...] 替换
        ↓
Step 5: mimeng 自检清单过一遍
        ↓
Step 6: 复制到 xhs 发布
```

**总耗时**：5-10 分钟/条（原 30-60 分钟）。

---

## 📁 输出示例

参见 [output/skill-4-formula-rewrites-v0.3/](../../output/skill-4-formula-rewrites-v0.3/) 下的 5 个 demo 跑。

---

## 🛠️ 高级用法

### 批量跑（从 pain-miner JSON 提取所有痛点）

```powershell
# 假设你已写一个 wrapper（v0.4 候选）
python batch_run.py --input output/batch-full-5kw/pain-miner-AI_副业.json --top-pains 10
```

（v0.4 候选：自动从 JSON 提取 top 10 痛点批量生成）

### 配合 Skill 3 batch pipeline

```powershell
# Step 1: 跑 Skill 3 拿新痛点
python skills\batch-keyword-pipeline\run.py --keywords "AI 副业,减肥" --out output/new-batch

# Step 2: 用 rewriter 批量生成仿写
for /f %i in ('python -c "import json; print(len(json.load(open(\"output/new-batch/pain-miner-AI_副业.json\"))['per_note']))"') do (
    # 循环提取每条痛点跑 rewriter
)
```

---

## ⚠️ 限制 / 已知问题

1. **自动检测 trigger ~70% 准确率**：模糊评论建议显式传 `--trigger`
2. **模板 A 标题套用复杂**：数字结果型标题需要手动调整（A1、A2、A3 三种子公式）
3. **没有 LLM 调用**：所有 TODO 需手动填写（v0.4 候选：调用 Claude API 自动填）
4. **仅支持 5 个关键词** 的 tag 模板：其它关键词需要自定义 9 tag

---

## 🗺️ 版本演进

- **v0.1** (2026-06-09) — 5 仿写 + 公式（手写）
- **v0.2** (2026-06-09) — 159 痛点 LLM 重分类 + 15 A/B 标题 + 3 模板（半自动）
- **v0.3** (2026-06-09) — rewriter.py 一键生成骨架（**本版本**）
- **v0.4** (候选) — 接 Claude API 自动填 TODO + 批量从 JSON 跑
