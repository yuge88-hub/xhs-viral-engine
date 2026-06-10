# Skill 5 v0.1 — Obsidian 同步

> **把 Skill 1+2+3+4 全部输出 → Obsidian vault**
> **耗时**：5-10 秒（dry-run），10-30 秒（实际）
> **核心**：YAML frontmatter + [[wikilinks]] + 增量同步 + 00-index.md

---

## 🚀 快速使用

### 1. Dry-run 预览

```powershell
cd "C:\Users\张哥\Downloads\web-clipper-master"
python skills\skill-5-obsidian-sync\sync.py `
  --vault "C:\Users\张哥\Documents\MyVault" `
  --dry-run
```

### 2. 实际同步

```powershell
python skills\skill-5-obsidian-sync\sync.py `
  --vault "C:\Users\张哥\Documents\MyVault"
```

### 3. 自定义项目根

```powershell
python skills\skill-5-obsidian-sync\sync.py `
  --vault "..." `
  --source "D:\path\to\web-clipper-master"
```

---

## 📁 vault 结构

```
<vault>/小红书爆款引擎/
├── 00-index.md                    ← 首页索引
├── 01-raw/                       ← Skill 1+2+3 原始数据
│   ├── AI 副业/
│   │   ├── viral.md
│   │   └── pains.md
│   ├── 营养食疗/
│   ├── 副业赚钱/
│   ├── 减肥/
│   ├── 自媒体/
│   └── _batch-summary.md
├── 02-formula/                   ← Skill 4 公式库
│   ├── formula-report.md
│   ├── pain-reclassified.md
│   ├── ab-titles.md
│   └── body-formula-v2.md
└── 03-rewrites/                  ← Skill 4 仿写
    ├── AI 副业/
    │   ├── v0.1-手写.md
    │   └── v0.4-auto-filled.md
    ├── 营养食疗/
    ├── 副业赚钱/
    ├── 减肥/
    └── 自媒体/
```

---

## 📝 文件格式

每个 vault 文件都含 **YAML frontmatter**：

```yaml
---
type: pain-mining          # viral/pain/summary/formula/rewrite
keyword: AI 副业            # 关键词 (viral/pain/rewrite 才有)
date: 2026-06-09
source: xhs-pain-miner     # 来源
total_pains: 32            # 统计
trigger: V                 # 行动触发 (v0.2+)
tags: [小红书, 痛点, AI副业]
---
```

末尾自动追加 **相关关键词 wikilinks**：

```markdown
## 🔗 相关关键词

- 当前关键词: **AI 副业**
- [[营养食疗]]
- [[副业赚钱]]
- [[减肥]]
- [[自媒体]]
```

---

## ⚡ 增量同步

- 比较 source / target 的 mtime
- 目标比源新 → 跳过（**不重写未变更文件**）
- 源比目标新 → 重新写

可以**安全多次运行**。改完 Skill 4 输出再跑一次 sync，只会更新的部分。

---

## 🎯 索引页 00-index.md

- 5 关键词速览表（viral/pains/v0.1/v0.4 都有 ✅/—）
- 01-raw 链接（按关键词分组）
- 02-formula 4 个公式文档链接
- 03-rewrites 5 关键词 × 2 版本链接
- 一键跳转 [[wikilinks]]

---

## 🛠️ 高级用法

### 只同步某 section

（v0.2 候选，加 `--section 01-raw` filter）

### 加 Dataview 友好表格

每个 summary 都已用 markdown 表格，可直接用 Dataview 插件查询：

```dataview
TABLE keyword, total_pains, total_comments
FROM "小红书爆款引擎/01-raw"
```

### 配合 Obsidian 插件

- **Dataview**: 表格化展示
- **Graph View**: 看 [[wikilinks]] 关系网
- **Templater**: 用 00-index.md 当模板
- **Tag Pane**: 按 tag 过滤

---

## ⚠️ 已知限制

1. **JSON → MD 转换只对 viral/pain**：其他类型直接复制源文件
2. **wikilink 简单替换**：不解析代码块内的关键词（极偶尔可能误命中）
3. **5 关键词硬编码**：新关键词需改 `KEYWORDS` 列表
4. **没 Obsidian API 调用**：纯文件操作（不依赖 Obsidian 在跑）

---

## 🗺️ 版本演进

- **v0.1** (2026-06-09) — **本版本**：扫产出 → 写 vault + YAML + wikilinks
- **v0.2** (候选) — 加 `--section` filter + 自动重跑 Skill 1-4
- **v0.3** (候选) — 接 Obsidian Local REST API（直接 vault 内编辑）
- **v0.4** (候选) — 加 daily-note 自动汇总当天新增
