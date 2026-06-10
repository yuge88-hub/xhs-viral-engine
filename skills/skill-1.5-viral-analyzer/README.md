# Skill 1.5: viral-analyzer (v0.1.0)

**微技能**：拆爆款——给一条 viral note，输出 **4 问 + 6 维 + 4 标准对标 + 封面分析**。
> 解决原问题：Skill 1 找爆款 → Skill 4 仿写，**中间没有"为什么爆"的分析**——太浅。

---

## 🎯 角色定位

```
Skill 1 (scanner)            Skill 1.5 (analyzer)        Skill 4 (rewriter)
   找爆款                        拆爆款                        仿写
   ↓                              ↓                            ↓
viral.json                  4问+6维+对标+封面         (用 1.5 输出当风格锚点)
   note_id+title+likes        analysis.json                v0.5 reverse_prompt
   +xsec_token                04-benchmarks/               v0.3 rewriter (套骨架)
                              05-reverse-prompts/
```

---

## 🛠️ 4 个脚本

| 脚本 | 输入 | 输出 | 用什么 |
|---|---|---|---|
| `viral_analyzer.py` | note_id + xsec_token | `{note_id}-4问+6维.md` + `.json` | scrapling StealthyFetcher + DeepSeek LLM |
| `cover_analyzer.py` | note_id + xsec_token | `{note_id}-cover.png` + `{note_id}-cover.json` | scrapling screenshot + 视觉规则 + LLM |
| `benchmark_check.py` | viral_analyzer 输出 + author info | `{note_id}-benchmark.json` | 规则评分（粉丝/结构）+ LLM（人群/目标） |
| `reverse_prompt.py` (Phase B) | viral_analyzer + pain-miner | `{note_id}-reverse-prompt.md` | 6 维逆推模板 + DeepSeek |

---

## 🚀 快速使用

### 1. 拆一条爆款（viral_analyzer）

```powershell
cd "C:\Users\张哥\Downloads\web-clipper-master"
$env:DEEPSEEK_API_KEY="sk-..."
python skills\skill-1.5-viral-analyzer\viral_analyzer.py `
  --note-id "666c0258000000001c0207a2" `
  --xsec-token "ABmsNJnNxN-2NfCfXI_mnrzTiuFXKmmJKbpLzIcUo3Xh4="
```

输出：
```
output/skill-1.5-viral-analyzer-v0.1/
├── 666c0258000000001c0207a2-4问+6维.md
├── 666c0258000000001c0207a2-analysis.json
└── (cover/benchmark 后续跑)
```

### 2. 封面分析

```powershell
python skills\skill-1.5-viral-analyzer\cover_analyzer.py `
  --note-id "666c0258000000001c0207a2" `
  --xsec-token "ABmsNJnNxN-2NfCfXI_mnrzTiuFXKmmJKbpLzIcUo3Xh4="
```

### 3. 4 标准对标评估

```powershell
python skills\skill-1.5-viral-analyzer\benchmark_check.py `
  --note-id "666c0258000000001c0207a2"
```

### 4. 端到端（4 个脚本都跑）

```powershell
python skills\skill-1.5-viral-analyzer\run_all.py `
  --note-id "666c0258000000001c0207a2" `
  --xsec-token "ABmsNJnNxN-2NfCfXI_mnrzTiuFXKmmJKbpLzIcUo3Xh4="
```

---

## 📋 输出 Schema (4问+6维)

```yaml
meta:
  note_id: 666c0258000000001c0207a2
  title: 用AI做儿童绘本🔥涨粉8W
  author: 陶陶AI灵感库
  fans: 80000
  likes: 20000
  collects: 24000
  comments: 749
  publish_date: 2024-06-14
  url: https://...

4问:
  who: 25-35岁宝妈/AI 副业新手（看 IP 分布 + 评论画像推断）
  why_click: 标题"AI + 涨粉 8W + 教程" 3 重爆点 + 封面"涨粉 8W" 大字
  how_flow: 视频开头自我介绍 → 痛点共鸣 → 工具清单 → 步骤演示 → 引导关注
  where_lead: 评论里集中"求工具/求教程" → 目标:涨粉 + 私域引流

6维:
  role_dna: AI 副业实战导师，第一人称亲历，权威来自"亲自跑通 8W 粉"
  reader_profile: 25-35 女性副业新手，痛点"想做但不会"，需求:工具获取型
  content_structure: 总字数 200 字内, 5 段（钩子/痛点/工具/演示/CTA）, 单段 ≤50 字
  language_style: 短句+感叹号+emoji, 口语化, 修辞:反问+排比, 标点:感叹号高频
  constraint_rules: 禁用词:颠覆/风口/赛道; 格式:无小标题/bullet/加粗
  workflow_logic: 视频截图+语音+字幕, 固定段落:自我介绍+结尾引导
```

---

## ⚠️ 限制

1. **必须有效 cookies** —— scrapling 不带 cookies 抓 xhs 会重定向 login
2. **必须 xsec_token** —— URL 不带直接 404
3. **DeepSeek API 限流** —— 批量跑加 `--sleep 0.5`
4. **OCR 暂不实现** —— cover_analyzer 只做视觉元素（颜色/构图/文字位置），不做字符识别

---

## 🗺️ 版本演进

- **v0.1.0** (2026-06-09) — **本版**：4 问 + 6 维 + 4 标准 + 封面（4 个脚本）
- **v0.2.0** (候选) — 加 OCR 识别封面文字（用 paddleocr 或 EasyOCR）
- **v0.3.0** (候选) — 加批量模式（输入 note_id 列表）
- **v1.0.0** (候选) — 整体接入 Skill 4 v0.5 reverse_prompt 做闭环
