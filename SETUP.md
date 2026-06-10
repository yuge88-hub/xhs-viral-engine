# 🛠 SETUP.md — 从零安装到第一份爆款报告

> **目标**: 跟着走 ~30 min, 你就有一份 5 个 Skill 全跑通的爆款情报报告。

---

## 📋 系统要求

| 项 | 要求 |
|---|---|
| OS | Windows 11 (本项目主要在 Windows 上跑通; macOS/Linux 理论可用但未测) |
| Shell | PowerShell 5.1+ (`$PSVersionTable.PSVersion`) |
| Python | **3.11+** (推荐 3.12) |
| 磁盘 | 至少 2 GB 可用 (DrissionPage + scrapling 各拉一份 Chromium) |
| 网络 | 能连国内 (DeepSeek API + 小红书) |

---

## 🪜 Step 1: 装 Python + 包管理

### 装 Python 3.12

```powershell
# 推荐用 uv (10x 更快)
winget install --id=astral-sh.uv -e

# 或用 conda
winget install --id=Anaconda.Miniconda3 -e
```

### 装 Python 依赖

```powershell
cd <项目根目录>
pip install -r requirements.txt

# 或用 uv (推荐, 30s 装完)
uv pip install -r requirements.txt
```

---

## 🪜 Step 2: 装小红书 CLI

```powershell
uv tool install xhs-cli-headless==0.8.9 --force

# 验证
xhs --version  # 应输出 0.8.9
```

> ⚠️ 用 `xhs-cli-headless` 不是 `xiaohongshu-cli` — 前者修复了 0.6.x 的 captcha 误报 bug (见 [POSTMORTEM.md](POSTMORTEM.md) #5)

---

## 🪜 Step 3: 登录小红书 (一次性, ~1 min)

```powershell
xhs login
# 扫码登录 (用小红书 App 扫弹出的二维码)
# 成功后 cookies 自动存到: ~/.config/xhs-cli/cookies.json (Linux/Mac) 或 %USERPROFILE%\.config\xhs-cli\cookies.json (Windows)

# 验证
xhs whoami
# 应返回:
# {"user_id": "xxx", "nickname": "你的昵称", "red_id": "xxx"}
```

如果登录失败,见 [POSTMORTEM.md](POSTMORTEM.md) "xhs login 7 招"。

---

## 🪜 Step 4: 配 DeepSeek API key (~2 min)

### 申请 key

1. 访问 https://platform.deepseek.com/api_keys
2. 注册 / 登录 (国内可用)
3. 充值 ¥10 (够跑 1000+ 条爆款拆解, deepseek-chat 极便宜)
4. 创建 API key, 复制 `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### 写到 `.env`

```powershell
# 复制模板
copy .env.example .env

# 编辑 .env, 用记事本或 VS Code 打开
# 把 sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx 替换成你刚复制的真 key
notepad .env
```

`.env` 内容应该长这样:
```
DEEPSEEK_API_KEY=sk-你的真key
DEEPSEEK_MODEL=deepseek-chat
```

### 验证

```powershell
# PowerShell 临时载入 .env 到当前 session
Get-Content .env | ForEach-Object {
  if ($_ -match '^([^=]+)=(.+)$') { Set-Item -Path "env:$($matches[1])" -Value $matches[2] }
}

# 验证
echo $env:DEEPSEEK_API_KEY
# 应输出 sk-... (不是 xxxxxxxx)
```

---

## 🪜 Step 5: 跑第一个关键词 (~5 min)

```powershell
# 选个你感兴趣的关键词, 比如 "AI 副业"
python skills\batch-keyword-pipeline\run.py `
  --keywords "AI 副业" `
  --min-likes 1000 `
  --pages 1 `
  --pain-min-likes 5

# 输出在 output/batch-YYYYMMDD-HHMMSS/
```

期间会看到:
```
>>> 跑关键词 1/1: AI 副业
  → scanner: 22 viral notes 抓到
  → pain_miner (web 路径): 31 痛点抓到
  ✓ 完成 (387s)

合并:
  → 22 viral notes
  → 31 痛点
  → 写 batch-summary.md / viral.md / pains.md / raw.json

=== Done ===
```

---

## 🪜 Step 6: (可选) 跑 Top 5 深度拆解

如果 Step 5 跑出几条爆款, 想深拆 Top 5:

```powershell
# 先确认 viral notes 有 xsec_token (扫一眼)
type output\batch-*\viral-AI*.json | Select-String "xsec_token" | Select-Object -First 1

# 然后参考 output/ai-knowledge-base/run_top5_fix.py 模板, 改 keyword 跑
# 每条 ~30s viral_analyzer + ~17s pain_miner + ~5s cover + ~5s benchmark = ~1 min/条
# 5 条 ~5 min, ~¥0.02
```

---

## 🪜 Step 7: (可选) 同步 Obsidian

```powershell
# 第一次 dry-run 看看会写啥
python skills\skill-5-obsidian-sync\sync.py `
  --vault "C:\Users\你\Documents\YourVault" `
  --dry-run

# 实际同步
python skills\skill-5-obsidian-sync\sync.py `
  --vault "C:\Users\你\Documents\YourVault"
```

vault 结构:
```
<vault>/小红书爆款引擎/
├── 00-index.md                ← 首页索引
├── 01-raw/                    ← Skill 1+2 原始数据
├── 02-formula/                ← Skill 4 公式库
└── 03-rewrites/               ← Skill 4 仿写
```

---

## 🆘 常见坑

| 现象 | 原因 | 修 |
|---|---|---|
| `xhs whoami` 401 | cookies 失效 | `xhs login` 重新登 |
| pain_miner captcha 频繁 | 没用 `--use-web` | Skill 2 v0.2.0 默认 web, 不会触发 |
| 中文乱码 | Windows GBK | 已经接 `skills._bootstrap` 自动 UTF-8 |
| `deepseek-flash` 400 | 模型名错 | 用 `deepseek-chat` 或 `deepseek-v4-flash` |
| `DEEPSEEK_API_KEY 未设置` | `.env` 没载入 | 看 Step 4 验证步骤 |

详细看 [POSTMORTEM.md](POSTMORTEM.md), 30+ 个坑全记。

---

## 🎓 进阶玩法

| 玩法 | 命令 |
|---|---|
| **跨 5 关键词跑批** | `python skills\batch-keyword-pipeline\run.py --keywords-file keywords.txt` |
| **只抓不拆**(省 API 钱) | `--no-pains` (不跑 Skill 2) |
| **完整模式**(取粉丝数) | `--full --min-likes 1000 --max-followers 3000` (有 captcha 风险) |
| **痛点→选题** | `python skills\xhs-comment-pain-miner\topic_generator.py --pain-dir output\batch-*` |
| **账号拆解** | `python skills\xhs-trending-scanner\account_analyzer.py --viral-json output\batch-*\combined-viral.json` |

---

## 📚 接下来读

- [README.md](README.md) — 全景介绍
- [TOOLS.md](TOOLS.md) — 每个工具(xhs-cli / DrissionPage / scrapling)干啥
- [STATUS.md](STATUS.md) — 项目当前进度 (Phase A-J)
- [POSTMORTEM.md](POSTMORTEM.md) — 30+ 踩坑全记录
- `skills/<name>/README.md` — 每个 Skill 的 API + 示例
