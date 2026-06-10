# STATUS.md — 小红书全栈爆款笔记自动化引擎

> **任务连续性索引**：长任务的"现在在干啥、下一步干啥、阻塞点"全在这。
> **新对话/新窗口开头第一句话**："请读 STATUS.md 继续 Phase X" → 我立刻接着干。

> **📌 任何后续实跑前先读 [POSTMORTEM.md](POSTMORTEM.md)**：记录了 30+ 个踩过的坑和修复。
> **📐 架构/选型决策**：[ARCHITECTURE.md](ARCHITECTURE.md) — 5 个 Skill 的分层 + 选型理由
> **📝 代码规范**：[CONVENTIONS.md](CONVENTIONS.md) — 命名 / 目录 / 依赖约定

## 🛡️ 防丢机制（用户 2026-06-09 加的）

**问题**：context window 截断 / 多窗口状态隔离 → 之前做的东西"白做了"
**机制**：
- ✅ STATUS.md / ARCHITECTURE.md / CONVENTIONS.md 三件套已建
- ✅ 每 Phase 结束更新 STATUS
- ✅ TodoWrite 跟踪 > 3 步的任务
- ✅ 大输出重定向文件，对话只贴 head/tail
- ✅ **PostToolUse hook 自动提醒**（2026-06-09 19:53 加）: `.claude/settings.local.json` Edit|Write|MultiEdit 后 30 分钟未更新 STATUS.md 会注入提醒到上下文

**新窗口开场白模板**：
> "请读 `C:\Users\张哥\Downloads\web-clipper-master\STATUS.md` 继续 Phase X"

## 当前阶段：🔵 Phase J 进行中 (2026-06-10) — GitHub 发布 + LICENSE 协议切换

> **新窗口接手指南**: 上一轮 (Phase I) HANDOFF 在 [HANDOFF-2026-06-10a.md](HANDOFF-2026-06-10a.md)
> **本轮成果** (Phase J):
>   1. ✅ 远端仓库创建 + 首次 push (`c631e54`, 318 文件, 含 .gitignore 排除 web-clipper 衍生)
>   2. ✅ 代理从 7897 (Clash) 切换为 10808 (v2rayN/xray, 本机实际跑的)
>   3. ✅ LICENSE 改 MIT (原 DiamondYuan GPL 残留清理, 仓库已无 GPL 衍生代码, 合规可换)
>   4. ✅ README License 段对齐 MIT, 删 "web-clipper 原仓库代码不在本发布范围" 不实之词
>   5. ✅ amend + force push 收尾, 远端 SHA 验证一致
> **下一窗口可接**: 任务 19 (P0 重构) / Step ⑩ (生图 3:4 卡片, 全栈最后一项)
>
> **Phase I 成果** (上一轮): bugfix #41 验证 + Top 1/2 reverse_prompt 全填
> **Phase H 成果** (上上一轮): 3.0 报告 **17520 字符 / 423 行**, 比 2.0 多 **151%**

### Phase J 本轮 (2026-06-10) — GitHub 发布 + LICENSE 切换

- [x] **远端仓库**: `https://github.com/yuge88-hub/xhs-viral-engine.git` (空仓从 0 推到 318 文件)
- [x] **代理配置修正**: 本机跑的是 v2rayN/xray (端口 10808), 不是 Clash (7897) — `git config --global http(s).proxy` 已修正
- [x] **LICENSE 协议切换**: GPL-2.0-or-later → MIT
  - **法律检查**: 仓库内**无任何 web-clipper 衍生代码** (`.gitignore` 老早就把 `src/` `chrome/` `bin/` `script/` `.github/` `package.json` `pnpm-lock.yaml` `tsconfig.json` `vitest.config.ts` `global.d.ts` `*.eslintrc` `.prettierrc` `.yarnrc` 全排除)
  - **唯一遗留**: 根目录 `LICENSE` 文件内容是 DiamondYuan 的 GPL 协议 — 已覆盖为 MIT 全文
  - **结论**: 协议可合法切换为 MIT
- [x] **README 修正**: License 段从"私人项目不对外保证"改为"MIT License 欢迎分发", 删 web-clipper 不实之词
- [x] **amend + force push**: `35ed9ad` → `c631e54`, 把 LICENSE/README/.gitignore 改动合并进 initial commit
- [x] **验证**: `git ls-remote origin` → `c631e54e231ea1d29aca3f8da13057927ef8b4e5 refs/heads/main` ✓

### Phase H 本轮 (2026-06-10) — AI 知识库 Top 5 真拆 + 3.0 报告

- [x] **任务 17: 3.0 报告初版** (前台 ~5s, ¥0) → **14706 字符 / 337 行**
  - 复用 `output/ai-knowledge-base/run_top5_fix.py` (Phase G 已存产物)
  - 5 条 Skill 1.5 viral_analyzer (DeepSeek 4问+6维 LLM) + 5 条 pain-miner web 抓
  - 产物: `output/ai-knowledge-base/intelligence-report-v3-2026-06-10.md` (初版)
  - 脚本: `output/ai-knowledge-base/write_intel_report_v3.py` (可复用模板)
- [x] **任务 20: 补 cover + benchmark 5 条** (后台 ~2 min, 5×2 = 10 sub-skill, 全 rc=0)
  - 脚本: `output/ai-knowledge-base/run_top5_cover_bench.py` (5 条串行)
  - 5 张 cover.png (47-148 KB) + 5 份 cover.json (主色/尺寸/KB) + 5 份 benchmark.json (4 标准评分)
  - 重跑 v3 → 最终 **17520 字符 / 423 行** (比初版多 **19%**)
- [x] **最终 3.0 报告特性**:
  - **6 章**: Top 5 速查表 / Top 5 头部账号深拆 / 跨 5 条聚合 / 3 步仿写策略 / 2.0 vs 3.0 对比 / 覆盖完整度
  - **钩子公式 Top 5**: 反问警告 80% / 工具品牌 40% / 个人故事 20% / 场景应用 20% / Skill化封装 20%
  - **痛点 Top 10**: 累计 1190 赞, 17 条保留 — 631 赞「反 AI 识别」+ 240 赞「AI 学习了我们」占前 2
  - **痛点主题聚类**: 学习/教程 3 条 / 反 AI 识别 2 条 / 工作流 Skill 化 2 条 / 工具横评 1 条
  - **封面规律 (5/5 全填)**: 100% 3:4 (1080×1440), 主色 3 白 + 1 米 + 1 浅灰 — 浅底高对比是 AI 知识库视觉惯例
  - **benchmark 总评 (5/5 全填)**: 0.57-0.71 区间, **结构全 1.0** (4/4+6/6 满) / 素人 0.5 (粉丝数抓不到) / 人群 0.6-0.85 / 目标 0.3-0.6
  - **强推荐对标**: Top 2「慢慢有解」+ Top 5「知柿AI」= **0.71 总评**

### Phase H 关键发现 (Top 5 深拆)

1. **5/5 Top 都有完整 4问+6维 + cover + benchmark** (Skill 1.5 端到端 4 子技能全跑)
2. **反问警告是 Top 5 最高频钩子 (80%)** — Top 1「不同的 AI 竟然有不同的分工」+ Top 2「这几个词一出现,就暴露你在用 AI」都是
3. **Top 2 反 AI 识别就是 623 赞金句出处** — 631 + 240 = 871 赞同主题 → **反向选题金矿** (验证 Phase G 发现 #4)
4. **结构分全 1.0, 但目标分低 (0.3-0.6)** — Top 笔记只引导「收藏+评论」不引导「关注+购买」, 新号要补足
5. **3:4 浅底封面是 AI 知识库视觉惯例** — 5/5 全 3:4, 主色多为白/米色, 工具截图+文字即可

### Phase H 待办 (用户决定)

- [ ] **任务 19: P0 迭代** (架构审计建议, 半天) — 抽 `_bootstrap/llm_client.py` + `cookies_loader.py` (4 处 LLM 重复)
- [x] **任务 21** (2026-06-10): Top 1 + Top 2 reverse_prompt 出仿写模板 — `output/ai-knowledge-base/reverse-prompts/{note_id}-reverse-prompt.{md,json}`
  - Top 1 不劳而获一个亿 (689327c9...): 5/5 段全填 824 字符 (147+129+276+173+99), 4 KB md
  - Top 2 慢慢有解 (6a1e8193...): 5/5 段全填 742 字符 (96+199+212+173+62), 4 KB md
  - **核心产出**: 每条一段 ~1200 字符「一键复制版」prompt, 直接发 LLM 即可仿写
  - **耗时 / 成本**: ~2 min (前台) / ~¥0.01 (10 段 × deepseek-flash)
- [x] **bugfix #41** (2026-06-10): account_analyzer 不识别 `results` 字段 + total_acc=0 ZeroDivisionError — 已修, 跑 AI 知识库 scored-full.json 验证: 9 账号 / 9 爆款 / 77 viral_total / 报告 50 行全填 ✅
- [ ] **Step ⑩**: 生图 3:4 卡片 (全栈 90→100%, 未试)

### Phase G 本轮 (2026-06-09 22:25-22:32) — AI 知识库关键词全链路

- [x] **任务 15: pain-miner 9 条 AI 知识库 Top** (后台 ~2.5 min, exit 0)
  - 抓评论 135 条 → 24 痛点 (7/9 笔记有效, 2 条评论数过少)
  - **Top 1 痛点 (623 赞)**: 「在没有AI时我就经常用其中一些句式」— 反向选题金句
  - 产物: `output/ai-knowledge-base/pains.json` (14.7 KB)
- [x] **任务 16a: quality_scorer 评分 9 条** (前台 ~5s)
  - 🔥常规 4 / ⚡准 4 / 📊平平 1 / 💎真 0 (素人爆款常态)
  - 产物: `output/ai-knowledge-base/scored-full.json`
- [x] **任务 16b: account_analyzer 跳过** (v2 报告不用 ACCOUNTS, 是死代码 — 待 P2 修)
  - bugfix 候选 #41: account_analyzer 不识别 `results` 字段 + total_acc=0 ZeroDivisionError
- [x] **任务 16c+d: AI 知识库 2.0 报告** (¥0 成本)
  - **6969 字符 / 203 行** (儿童身高 v2 5666 字符 — 我们多了痛点章节)
  - 10 章全填: Why 2.0 / 整体分布 / Top 9 / 头部 5 拆 / 钩子频率 / 学习点 / 3 步法 / 1.0vs2.0 / 痛点 Top 10 / 完整度
  - **AI 知识库专属 HOOK_PATTERNS** (7 类): 工具品牌/数字承诺/个人故事/反问警告/Skill化封装/场景应用/FOMO
  - 钩子频率: 个人故事/工具品牌/Skill化 各 56%, 反问警告/场景应用 44%, 数字承诺 33%
  - 产物: `output/ai-knowledge-base/intelligence-report-v2-2026-06-09.md`
  - 脚本: `output/ai-knowledge-base/write_intel_report_v2.py` (可复用模板)

### Phase G 关键发现 (AI 知识库赛道)

1. **真素人爆款仅 9 条** (35 作者过滤后), 全 < 3000 粉 — 比儿童身高 (13 条) 少 31%
2. **Top 1 暴利**: 「不劳而获一个亿」457 粉 23,755 赞 (viral 51.87) — 反问/警告型, AI 分工梗
3. **AI 圈 3 大钩子**: 工具品牌 + 个人故事 + Skill化封装 (3 个钩子各 56% 命中率)
4. **痛点反向选题富矿**:
   - 「人类自有句式 ≠ AI 风格」(623 赞) → 反 AI 识别选题
   - 「DeepSeek 难用」(39 赞) → 工具对比选题
   - 「企业数据上 AI 隐私」(8+8 赞, 多条) → 本地大模型选题

### Phase G 待办 (用户决定)

- [ ] **任务 17: Skill 1.5 真拆 Top 5** (可选, ¥0.02 + ~10 min) — LLM 4问+6维深度拆 Top 5
  - 复用 `output/children-height/run_top5_fix.py` 改 keyword
  - 产物: 3.0 报告 (~15k 字符)
- [ ] **任务 18: Skill 3 batch-keyword-pipeline** — AI 知识库只 1 关键词, **不需要跑** Skill 3 编排
- [ ] **任务 19: P0 迭代** (架构审计建议, 半天) — 抽 `_bootstrap/llm_client.py` + `cookies_loader.py`

### Phase H 本轮收尾 (2026-06-10) ✅

- 用户选 **任务 17 = 直接做 3.0 报告**
- ✅ 14706 字符 / 337 行 3.0 报告生成, 复用 Phase G 跑过的 Top 5 产物 (viral_analyzer + pain-miner)
- ✅ 修一个 ad-hoc 报告生成脚本为可复用 `write_intel_report_v3.py`
- ✅ STATUS.md 更新为 Phase H 完成
- **下一窗口开场白**: `请读 C:\Users\张哥\Downloads\web-clipper-master\STATUS.md 继续 Phase I` (或选 任务 19/20/21/bugfix #41/Step ⑩)

---

## 历史阶段：✅ Phase A 端到端闭环 + 批量验证 (2026-06-09) — bugfix #30 已修

> **触发原因**：用户反馈 Skill 2/4 做的太浅——只挖评论+套公式，没研究"具体那条爆款为什么爆"。
> **新方法论**：4 问 (Who/Why/How/Where) + 6 维逆推 + 4 标准对标 + 封面分析。

### 进行中

- [x] **Phase A**: `skills/skill-1.5-viral-analyzer/` 4 个脚本 + 端到端封装 + smoke test 全过
  - [x] `viral_analyzer.py` **v0.1.3** ✅ 实跑: 标题/作者/点赞20000/收藏24000/评论749/发布日期 全填上
  - [x] `cover_analyzer.py` **v0.1.2** ✅ 实跑: 1080x1440 / 178KB / 主色 #e0e1c1
  - [x] `benchmark_check.py` **v0.1.0** ✅ 实跑: 4 标准评分 (LLM 跳过时返占位 0.5)
  - [x] `run_all.py` **v0.1.0** ✅ 端到端封装, 失败不阻断
  - [x] **4 个 bugfix 沿路** (POSTMORTEM #25-#28):
    - `page.text` → `page.html_content` (xhs SPA 0 字节)
    - PowerShell BOM → `utf-8-sig` 读
    - `likedCount":"2万"` → `parse_xhs_count()` 解析
    - `disable_resources=True` 死循环 → 改 False
  - [x] **安全加固**: cookies 移 home 目录 + `.gitignore` 加 `cookies-*.json` + `debug*.py`
  - [x] **端到端闭环** (2026-06-09 19:07): `run_all.py --note-id 666c0258... --skip-llm` 跑通
    - 3 步: viral/cover/benchmark (exit 0/1/0) → bugfix 后全 0
    - 5 产物: 4问+6维.md (0.9KB) + analysis.json (1.1KB) + cover.json (0.6KB) + cover.png (178KB) + benchmark.json (0.9KB)
    - **bugfix #30**: `cover_path.relative_to(PROJECT_ROOT)` 在 out-dir 在 PROJECT_ROOT 外时 ValueError → 加 try/except fallback
  - [x] **批量验证** (2026-06-09 19:13): 3 条新 note 走 `run_all.py` 端到端全过
    - **note**: 6a168b8a (AI 漫剧/15000赞) + 66f8fa58 (副业赚钱) + 671f297d (AI 教程) 来自 batch-full-5kw
    - **15 产物全生成**, 0 captcha, xsec_token 仍有效 (~50s/条)
    - **验证**: Skill 1.5 端到端对任意 note_id + token 通用
    - **xsec_token 来源**: scanner.py v0.4.0 顶层字段 `xsec_token` 是关键 (POSTMORTEM #8)
- [x] **Phase B**: `skills/skill-4-viral-rewriter/reverse_prompt.py` **v0.5.0** ✅
  - 5 段式 prompt 模板: Role / Audience / Topic / Structure / CTA
  - 接受 pain-miner JSON 作钩子
  - `--auto-fill` (DeepSeek) 可选 (需 API key)
  - 输出 `{note_id}-reverse-prompt.md` (留空待填) + `.json` (结构化给 Skill 5 sync)
- [x] **Phase C-Step ⑥ 补齐** (2026-06-09 20:41): `skills/xhs-comment-pain-miner/topic_generator.py` v0.1.0
  - **零抓取零 API 成本**: 反向聚合 5 个 pain-miner JSON 159 痛点 → 155 唯一 / 4 跨关键词通用
  - **报告字段**: 跨关键词通用痛点 (top 10) / 6 大分类分桶 / 按关键词分桶 / 蓝海互补性分析
  - **关键发现**: 跨关键词 Top 4 全是 AI 副业+副业赚钱双爆 (写作/外语/小说/公众号) → "通用方法论"类选题
  - **分类**: question 94 条 (22811 赞, 主流) / pain 45 条 (3264 赞) / request 10 条
  - **MVP 模式限制**: 选题质量依赖 pain-miner 标签质量, categories 是 LLM 自动打的
  - **bugfix #32**: 中文双引号第二次触 (#31 同类) → 同步改用「」
- [x] **Phase B 端到端解锁** (2026-06-09 20:43): `reverse_prompt.py --auto-fill`
  - **用户提供 DeepSeek API key** (写 `.env` + `.gitignore` + $env, 走 POSTMORTEM #21 安全实践)
  - **5/5 段全填** (role 56 / audience 157 / topic 121 / structure 319 / cta 53 字符)
  - **痛点钩子自动接入**: 2 条 (40赞"怎么做，求带" + 4赞"画面不连贯")
  - **产物**: `{note_id}-reverse-prompt.md` 3 KB (一键复制版完整 prompt) + `.json`
  - **解锁下个**: Skill 4 rewriter.py 仿写 (¥0.01/条) + Step ⑩ 生图卡片
- [x] **Phase C-Step ④ 补齐** (2026-06-09 20:36): `skills/xhs-trending-scanner/account_analyzer.py` v0.1.0
  - **零抓取零 API 成本**: 反向聚合 combined-viral.json 87 条 → 84 唯一账号
  - **报告字段**: 榜单 (top 20) / 爆款分布 / 跨关键词操盘手 / 头部长尾 / 单账号内容主题 / 自动洞察
  - **关键发现**: 81 账号 (96%) 只 1 爆款, 3 账号 2-3 爆款, 0 账号 4+ 爆款 → **长尾海量化**; Top 10% 账号贡献 41.5% viral_score
  - **跨关键词操盘手**: Sylis聊创业 (AI 副业+副业赚钱) / 周公何在 / 坎叔
  - **MVP 模式限制**: 无粉丝数, 只能做"内容策略维度"分析; 深度拆解需 `scanner --full` (有 captcha 风险)
  - **bugfix #31**: Python 字符串内嵌中文双引号 `"..."` 触发 SyntaxError → 改用「」
- [x] **🆕 Phase D: 编码基线重构** (2026-06-09 21:30) — 用户反馈"反复出问题没迭代到基域"
  - `skills/_bootstrap/console_utf8.py` + `__init__.py` — 任何 xhs skill 脚本第一行 `from skills._bootstrap import *` 即激活 UTF-8 (幂等, 修 stdout/stderr/PYTHONIOENCODING/Windows console codepage)
  - `skills/sitecustomize.py` — 加 `PYTHONPATH=skills` 让任何子 Python 进程自动 UTF-8
  - `quality_scorer.py` v0.1.0 — 第一个用基线的脚本
  - **CONVENTIONS #17 升级**: 从"每个脚本手写 3 行 reconfigure" → "基线 import 1 行"
  - **POSTMORTEM #33**: 编码基线重构全过程记录
  - **验证**: `python -c "from skills._bootstrap import *; print(sys.stdout.encoding)"` → `utf-8` ✅
- [x] **🆕 Phase E: 细分市场深挖 (用户原话: 换赛道到「儿童身高」)** (2026-06-09 21:25)
  - **AI 儿童绘本** (HANDOFF Phase C 任务 1-3): scanner 40 条 + quality_scorer (1💎/5🔥/23⚡/11📊) + Top 3 Skill 1.5 (15 产物) + reverse_prompt (3 模板) — 完整闭环
  - **🆕 儿童身高** (用户临时改方向, 2026-06-09 21:25): scanner 40 条 + quality_scorer (0💎/4🔥/11⚡/25📊) + account_analyzer (40 账号 / Top 4 集中度 44.2%) + 情报报告 (write_intel_report.py v0.1.0)
  - **跨赛道对比**: 儿童身高质量更参差 (0 真爆款 vs AI 儿童绘本 1 真爆款) → 选题空间更大, 但深度更难
  - **关键洞察 (儿童身高)**: 30 天内 29-36 天前内容是主力 (季节性: 暑假/三伏天) + 1 年+ 长尾 (儿童标准身高表 1029 天前仍 8947 赞)
  - **对标账号**: 阿文阿乐~ (二年级女儿142了) / 米米妈Lily (13岁168cm) / 晨熙妈妈 (儿童标准身高)
  - **下一步**: 选 Top 1-3 跑 Skill 1.5 端到端 (历史数据也是 "今天抓的", 但 content 旧)
- [x] **🆕 Phase F: 用户指出 Skill 1 定位跑偏 (2026-06-09 21:35) — 重要修正**
  - **用户原话**: "我看你跑的数据都是普通爆款, 不是对标账号" (Skill 1 README 第 3 行: 找「低粉爆款」粉丝<3000 且 点赞>1000)
  - **错误**: 我跑的是 MVP 模式 (没取粉丝数), 抓的是 40 条普通爆款 (35w 粉头部跟素人混在一起)
  - **修正**: scanner 完整模式 (`--require-fans --max-followers 3000`) → 30 作者 / **13 条真素人爆款** (< 3000 粉)
  - **Top 1 修正**: 阿文阿乐~ (95w 粉) → **我的兜里有颗糖 (50 粉 viral=77.73) 3964 赞** — 新号真正能学的
  - **报告 2.0 写完** (`write_intel_report_v2.py` v0.1.0, 5666 字符, 175 行):
    - 13 条 Top 列表 (含钩子分类: 数字+身份/惊叹+反问/季节节点/数据表型/方法干货/专家权威/紧迫感)
    - Top 5 头部账号画像 (粉赞比/标题/钩子/选题类型)
    - 7 类钩子频率 + 怎么用
    - 新号 0 粉「对标 3 步」(抄标题公式/抄内容形式/避开陷阱)
  - **耗时**: scanner 完整模式 ~5 min (30 作者 DrissionPage 0 captcha) / quality + account 0
  - **bugfix 沿路**: 中文双引号 SyntaxError (POSTMORTEM #31 又触发) → 改「」
- [x] **🆕 Phase F 完整闭环: Top 5 跑 1.5 + pain + 3.0 报告 (2026-06-09 22:15)** ⭐⭐
  - **用户原话**: "找到对标账户以后, 找出爆款文章, 标题+文章结构+封面+评论痛点"
  - **5 条 Top 素人爆款** (note_id + xsec_token 已就绪, 全 < 3000 粉):
    - R1 我的兜里有颗糖 (50粉, viral=77.73) / R2 美食宝妈vicky (120粉) / R3 粒粒 (61粉) / R4 小路上的墨迹 (113粉) / R5 美少女大佬 (116粉)
  - **`run_top5.py` 跑 4 步 × 5 条 = 20 产物** (`output/children-height/skill-1.5-top5/` + `pain-miner-top5/`):
    - viral/cover/benchmark rc=0 ✅ / pain_miner rc=2 ❌ (CLI 参数错, run_top5.py 用了 `--xsec-token --output-dir`, 但 pain_miner 接受 `--input --note-ids --out`)
    - 4 问+6 维空 ❌ (run_top5.py 用了 `--skip-llm`)
  - **`run_top5_fix.py` 修复 (2026-06-09 22:10)**: pain-miner 改 `--input <单 note JSON> + --out`, viral_analyzer 去掉 `--skip-llm`
    - 5/5 viral_analyzer (LLM DeepSeek) rc=0 ✅ → 4问 4/4 + 6维 6/6 全填
    - 5/5 pain_miner (web) rc=0 ✅ → 抓到 1-3 痛点/条 (Top 1: 291赞 "制造焦虑" / 180赞 "去年标准又降低" / 2赞 "四周岁117")
  - **benchmark 重跑** (LLM 填上后, 5 条 ~15s): 结构 0.0→1.0, 总评 0.4→0.6 (从"不建议对标"→"可参考")
  - **`write_intel_report_v3.py` 写完 (2026-06-09 22:15)**: 15,758 字符, 412 行 (≈ 2.8x 2.0)
    - 一、Top 5 速查表 (含主色+痛点数+4问+6维+benchmark)
    - 二、Top 5 头部账号深拆 (每个 ~50 行: 基本画像+4问+6维+封面+benchmark+痛点Top3)
    - 三、跨 5 条聚合 (钩子公式 Top 5 / 评论痛点类别+主题聚类 / 封面规律 / benchmark 趋势)
    - 四、3 步仿写策略 (3 标题模板 + 4 问+6 维 + 封面 3:4 暖色 + 避开陷阱 4 条)
    - 五、对比 2.0 vs 3.0 (8 倍 Top 5 信息量)
  - **关键洞察 (Top 1 LLM 拆)**: 全篇 18 字 (疑问句 9 + 主观评论 18), 评论区 854 条 = 点赞 22% → **短小 + 争议** 是素人爆款核心, **长文是反模式**
  - **耗时**: viral_analyzer 5×~30s=2.5 min, pain_miner 5×~17s=1.4 min, LLM 4问+6维 DeepSeek ~30s/条, 总 ~5 min
- [ ] **Phase C-Step ⑧ ① + Step ⑩ 生图**: 待用户决策 — 见下方"下一步"

### 实跑结果 (Phase A v0.1.3 + Phase B v0.5.0)

| 阶段 | 字段 | 结果 |
|---|---|---|
| 抓取 | HTTP | 200 (cookies 16 个生效) |
| 抓取 | html_content | 1018 KB |
| 标题 | og:title | "用AI做儿童绘本🔥涨粉8W - 小红书" |
| 作者 | nickname | "予哥" |
| 点赞 | parse_xhs_count("2万") | **20000** ✅ |
| 收藏 | parse_xhs_count("2.4万") | **24000** ✅ |
| 评论 | parse_xhs_count("749") | **749** ✅ |
| 发布 | time 戳 | **2024-06-14** |
| 标签 | og:keywords (10 个真 tag) | AI / AIGC / AI绘画 / 搞钱 / 副业 / 信息差 / 奇域AI / AI教程 / 儿童绘本 / 来聊聊你的副业 |
| 封面 | PIL 主色 | #e0e1c1 (1080x1440, 178KB) |
| benchmark | 4 标准 | 0.40 总评 (LLM 跳过) |
| reverse_prompt | 5 段模板 | 2000+ 字符 markdown, 9 个 `{{待填}}` 槽位 |

### 下一步（按优先级 — 待你选）

1. **跑 reverse_prompt.py --auto-fill** (需要 `$env:DEEPSEEK_API_KEY="sk-..."`) — 看 DeepSeek 填的 5 段质量
2. **跑 Skill 4 v0.5 端到端** (reverse_prompt → rewriter): 用填好的 prompt 仿写 1 条新笔记, 验证闭环
3. **Skill 5 v0.2 升级**: 加 `--section` filter + Obsidian Local REST API 可选集成
4. **批量跑 batch**: 用 Skill 1 scanner 找 5-10 条爆款, 全部走 1.5+4 pipeline, 出 N 套仿写
5. ~~**跑 `run_all.py` 端到端** (一次性串联 4 个脚本, 验证整体流程)~~ ✅ 已闭环 (bugfix #30 沿路)
6. ~~**Step ④ 拆解对标账号**~~ ✅ 已闭环（bugfix #31 沿路）
7. ~~**Step ⑥ 生成选题库**~~ ✅ 已闭环（bugfix #32 沿路）
8. **Step ⑧ 生成情报报告**（多 Skill 输出聚合）待做
9. **Step ① 找热门领域**（趋势识别 + 时间窗口对比）待做
10. **Step ⑩ 生图 3:4 卡片**（接"文生图" skill, 用户原始 10 步图的最后一环）待做

### 阻塞点

无。

### 已完成（最近一波）

- [x] **Phase C-Step ⑥ 生成选题库** (2026-06-09 20:41): `topic_generator.py` v0.1.0
  - **零抓取零 API 成本**: 反向聚合 5 个 pain-miner JSON 159 痛点 → 155 唯一 / 4 跨关键词通用
  - **报告**: 跨关键词痛点 Top 10 / 6 分类分桶 / 按关键词分桶 / 蓝海互补性分析
  - **关键发现**: 跨关键词 Top 4 全是 AI 副业+副业赚钱双爆 → 通用方法论类选题
  - **bugfix #32**: 中文双引号第二次触 (#31 同类) → 同步改用「」
- [x] **Phase B 端到端解锁** (2026-06-09 20:43): `reverse_prompt.py --auto-fill` + DeepSeek v4-flash
  - **用户提供 API key**: 写 `.env` + `.gitignore` + $env, POSTMORTEM #21 安全实践
  - **5/5 段全填**: role 56 / audience 157 / topic 121 / structure 319 / cta 53 字符
  - **痛点钩子自动接入**: 2 条 (40赞"怎么做，求带" + 4赞"画面不连贯")
  - **产物**: `{note_id}-reverse-prompt.md` 3 KB + `.json`
- [x] **Phase C-Step ④ 拆解对标账号** (2026-06-09 20:36): `account_analyzer.py` v0.1.0
  - **零抓取零 API 成本**: 反向聚合 combined-viral.json 87 条 → 84 唯一账号
  - **报告**: 榜单 / 爆款分布 / 跨关键词 / 头部长尾 / 单账号内容主题 / 自动洞察
  - **关键发现**: 81 账号 (96%) 只 1 爆款, **长尾海量化**; Top 10% 账号贡献 41.5% viral_score; 3 个跨关键词操盘手 (Sylis聊创业 / 周公何在 / 坎叔)
  - **bugfix #31**: Python f-string 嵌中文双引号 `"..."` 触发 SyntaxError → 改用「」
- [x] **PostToolUse hook 上线** (2026-06-09 19:53): 自动提醒更新 STATUS.md
  - `.claude/settings.local.json` PostToolUse matcher=`Edit|Write|MultiEdit`
  - `.claude/hooks/check_status_stale.py` 检查 STATUS mtime > 30min 注入提醒
  - **bugfix 沿路**: 加 `sys.stdout.reconfigure(encoding="utf-8")` (CONVENTIONS #17, hook stdout 走 UTF-8 否则 Claude Code 解析 JSON 失败)
  - **3 场景验证**: 5min 空输出 ✅ / 60min JSON reminder ✅ / 文件不存在空输出 ✅
  - **测试事故**: pipe-test 用了 `os.remove('STATUS.md')` 测"文件不存在"场景，**没恢复** → 写了个空文件 → 本 STATUS.md 是从对话上下文重建
- [x] **Phase A 批量验证 (2026-06-09 19:13)**: 3 条新 note 走 `run_all.py` 端到端全过
  - 6a168b8a (AI 漫剧/15000赞) + 66f8fa58 (副业赚钱) + 671f297d (AI 教程) 来自 batch-full-5kw
  - **15 产物全生成**, 0 captcha, xsec_token 仍有效 (~50s/条)
  - **验证**: Skill 1.5 端到端对任意 note_id + token 通用
- [x] **Phase A 端到端闭环 (2026-06-09 19:07)**：`run_all.py` 串联 3 脚本全过
  - **触发**: 实跑暴露 `cover_path.relative_to(PROJECT_ROOT)` 强约束 bug
  - **修复 #30**: `try/except` + `str(cover_path).startswith(str(PROJECT_ROOT))` fallback 到绝对路径
  - **5 产物**: 4问+6维.md (0.9KB) / analysis.json (1.1KB) / cover.json (0.6KB) / cover.png (178KB) / benchmark.json (0.9KB)
- [x] **Skill 5 (Obsidian 同步) v0.1.0**：`skills/skill-5-obsidian-sync/`
  - **sync.py**: 扫 Skill 1-4 产出 → 写 Obsidian vault (25 个文件)
  - **特性**: YAML frontmatter + [[wikilinks]] 双向链接 + 增量同步 + 00-index.md 索引
  - **vault 结构**: 01-raw (11) + 02-formula (4) + 03-rewrites (10) + 00-index
  - **首次 sync 完成**: `E:\xiaohongshu88\小红书爆款引擎\` (25/25 ✅)
  - **增量 sync 验证**: 重跑只写 1 个新文件, 24 个 up-to-date 跳过 (mtime 对比)
- [x] **Skill 4 (LLM 重构) v0.4.0**：`skills/skill-4-viral-rewriter/auto_fill.py`
  - **DeepSeek v4-flash API 联通**: 用 `DEEPSEEK_API_KEY` 环境变量 + `.env` 模板 + `.gitignore`
  - **批量填 5 个 demo**: 21k tokens / **¥0.01 总成本** (deepseek-flash 极便宜)
- [x] **Skill 4 (LLM 重构) v0.3.0**：`skills/skill-4-viral-rewriter/`
  - **`rewriter.py`** (v0.3.0): 输入痛点 → 输出可填空骨架 (5s/条)
  - **3 个 Body 模板** (A 反常识/B 分群/C 红利) + **5 类标题公式** (A-E)
  - **auto-detect 行动触发** (V/H/C/B/S, 启发式 ~70% 准确率)
  - **提速 6-12x**: v0.1 60min/条 → v0.2 30min/条 → v0.3 5-10min/条
- [x] **xhs-cli 升级**：`xiaohongshu-cli 0.6.4` → `xhs-cli-headless 0.8.9`（uv tool install --force）
- [x] **Skill 1**：`skills/xhs-trending-scanner/scanner.py` v0.4.0 — MVP + 完整双模式
- [x] **Skill 2**：`skills/xhs-comment-pain-miner/pain_miner.py` v0.2.0
  - **关键升级**: 默认走 DrissionPage web 抓取 (绕过 xhs comments API captcha)
  - xhs-cli comments API 限流太严, web 路径拿 `.comment-item` DOM
  - 0 captcha 触发, 47 痛点/395s
- [x] **Skill 3**：`skills/batch-keyword-pipeline/run.py` v0.2.0 — 编排器
  - per-keyword 隔离 (captcha 不串全场)
  - **实测完整跑通**: 5 关键词, 87 viral notes, 159 痛点, 2024s, 0 captcha
- [x] **关键发现**:
  - xhs web 限流比 API 宽松得多 (web 抓 87 notes 0 captcha, API 立刻被锁)
  - xhs-cli `Captcha triggered` WARNING 经常是**误报** (xhs read 实际返回 ok:true)
  - scanner.py 必须把 `xsec_token` 暴露为顶层字段 (xhs comments 强制要)
  - pain-miner 必须用完整 URL 形式传 xsec_token (URL 含中文时 cli 解析错)
  - DrissionPage 4.1.1.2 的 `run_js` 默认走 `Runtime.callFunctionOn` (坏), 必须加 `as_expr=True`

---

## ⚠️ 防丢机制注脚（本轮 2026-06-09 19:55 测试事故）

**承认错误**：pipe-test hook 脚本时用 `os.remove('STATUS.md')` 测"文件不存在"场景，**忘了在脚本最后恢复**——PowerShell 兜底 `New-Item -Force` 只建了空文件。
**修复**：本 STATUS.md 是基于对话上下文（之前 Read 1-340 完整内容 + 本轮所有 Edit）重建，**可能省略了命令速查、关键坑列表、待用户决策、关键发现（xhs captcha 7 招）**等参考段。
**补救**：下一轮对话开头让我读对话历史（你应该还保存着），我可以增量补全。
**教训**：测试时**不能删生产文件**——下次用 `.bak` 后缀而不是 `os.remove`。

### 阻塞点

无（全部解除）。

## 已实跑结果 (最新)

### batch-full-5kw (5 关键词 + pain-miner web 路径, 2024s, 0 captcha)

| 关键词 | viral notes | 痛点数 |
|---|---|---|
| AI 副业 | 18 | 32 |
| 营养食疗 | 17 | 30 |
| 副业赚钱 | 18 | 23 |
| 减肥 | 16 | 43 |
| 自媒体 | 18 | 31 |
| **合计** | **87** | **159** |

**Top 痛点样本** (高赞):
- 770 赞 [question] "不是你想象的那么简单" (教程来了)
- 535 赞 [pain/question] "切记，真能赚钱的不会和你说的" (副业)
- 95 赞 [pain] "摆摊也有..." (副业实战)
- 66 赞 [criticism] "做出来的前端确实可以...后端就是假的数据"
- 40 赞 [request] "怎么做，求带"

## 关键命令速查

```powershell
# Skill 1.5 端到端
cd "C:\Users\张哥\Downloads\web-clipper-master"
python skills\skill-1.5-viral-analyzer\run_all.py --note-id "<id>" --xsec-token "<tok>"

# xhs CLI
xhs search "关键词" --sort popular --json
xhs read <note_url>
xhs comments <note_id> --json
xhs whoami
```

## 待用户决策

- Skill 2-4 何时贴设计文档
- MVP 输出落到 Obsidian 哪个目录
- 完整模式触发 captcha 时是否用 `xhs login` headless 重置
- 是否需要批量跑多关键词（脚本化）
