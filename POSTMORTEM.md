# POSTMORTEM.md — 小红书自动化全栈：复盘 + 防坑手册

> **目的**：把这次 6 小时 实跑中踩过的 **20+ 个坑** + 修复记录下来。**任何后续跑这一套都先读这个文件**。
> 结构：先看「TL;DR 一句话教训」→「Setup Checklist」→「故障速查表」→「详细问题」。

---

## 🩹 TL;DR（一句话教训）

1. **xhs comments API 永远 captcha 限流** → 默认走 DrissionPage web 抓 `.comment-item` DOM
2. **xhs-cli `run_js` 静默返回 None** → 加 `as_expr=True` 走 `Runtime.evaluate`
3. **DrissionPage 首次启动会下 130MB Chromium** → `set_browser_path(SYSTEM_CHROME_PATH)` 用系统 Chrome
4. **xhs profile 直访 URL 被反爬重定向** → 用 user.xsec_token 拼 profile URL
5. **xhs `search-user` API 永远 fans_total=0** → 那个值是反爬默认值，弃用
6. **xhs-cli `Captcha triggered` WARNING 经常误报** → 信任实际 JSON `ok` 字段，忽略 stderr
7. **xhs 限流分接口** → search 通了 comments 仍可能 captcha，单独处理
8. **scanner.py 必须把 xsec_token 暴露为顶层字段** → pain-miner 要直接读
9. **xhs comments API 强制 xsec_token** → 用完整 URL `?xsec_token=...` 传
10. **batch 跑 captcha 串全场** → per-keyword 隔离
11. **uv tool uninstall 按可执行名** → 卸载包名错的会干掉 shim
12. **PowerShell GBK 终端乱码** → 写文件 (UTF-8 OK) + Python sys.stdout 强制 UTF-8
13. **xhs 用户 cookies 必须含 a1+web_session+webId 三个必需** → 其它推荐 (gid/websectiga/sec_poison_id/xsecappid) 加上更稳
14. **xhs 重登 QR 看 PNG 文件** → 不要看终端（GBK 乱码），用 `--qr-output FILE`
15. **scrapling `page.text` 在 xhs SPA 返 0 字节** → 用 `page.html_content`（1MB+ 完整 HTML 含 `__INITIAL_STATE__` JSON）— Skill 1.5 v0.1.1 修复
16. **PowerShell `Set-Content -Encoding utf8` 写 JSON 带 BOM** → Python 读用 `encoding="utf-8-sig"` 剥 BOM（v0.1.2 修复）
17. **xhs `likedCount`/`collectedCount` 是字符串带中文单位** `"2万"`/`"1.5万"`/`"10+"` → 用 `parse_xhs_count()` 解析, 不能 `int()`（v0.1.3 修复）
18. **xhs 封面 og:image 用 `name=` 不是 `property=`; imageList 用 `urlPre` 带 `/` 转义** → cover_analyzer regex 双兼容（v0.1.1 修复）
19. **scrapling `disable_resources=True` + `network_idle=True` 在 xhs SPA 死循环** → 改 `disable_resources=False`（xhs 需要 stylesheet 渲染）（v0.1.2 修复）
20. **`build_4q6d_prompt` 用 `meta.get('body', '?')[:1500]` 遇 None 崩** → 改 `or '?'` 兜底（v0.1.4 修复）
21. **DeepSeek 模型名 `deepseek-flash` 不存在返 400** → 用 `deepseek-chat`（直答）或 `deepseek-v4-flash`（reasoning）（v0.6 修复）
30. **`cover_analyzer.py` 第 297 行用 `cover_path.relative_to(PROJECT_ROOT)` 强约束 out-dir 必须在项目根下** → out-dir 在 `Downloads\output\...`（web-clipper-master 同级）时抛 `ValueError: ... is not in the subpath of ...` → 加 `try/except` + `str(cover_path).startswith(str(PROJECT_ROOT))` fallback 到绝对路径（v0.1.0 端到端验证时发现）
31. **Python 字符串内嵌中文双引号 `"..."` 触发 SyntaxError** → Python 看到第一个 `"` 就当字符串结束 → 改用 `「」` 或单引号（v0.1.0 account_analyzer 实跑时发现）
32. **中文双引号 SyntaxError 第二次触发**（topic_generator.py line 270）→ 同 #31 根因 → 同修法。**教训**: 写 f-string 时**默认**用 `「」` 替代 `""`，省得再触发
33. **编码 (POSTMORTEM #17) 反复在 #25/#26 出现**（每个脚本手写 `sys.stdout.reconfigure(encoding="utf-8")` 容易漏）→ 用户反馈"一直没迭代到基域" → **升级为项目级基线**：
   - `skills/_bootstrap/console_utf8.py` 一行 `from skills._bootstrap import *` 即激活 (幂等, 修 stdout/stderr/PYTHONIOENCODING/Windows console codepage)
   - `skills/sitecustomize.py` + `PYTHONPATH=skills` 让任何子 Python 进程自动 UTF-8
   - **新基线**: 任何 xhs skill 脚本**第一行** 必加 import — 不再手写 3 行 reconfigure
   - **验证**: `$env:PYTHONPATH="skills;..." ; python -c "from skills._bootstrap import *; print(sys.stdout.encoding)"` → `utf-8`

---

## 🛠️ Setup Checklist（全新环境 5 分钟 setup）

```powershell
# 1. 装 xhs-cli-headless (覆盖 xiaohongshu-cli)
uv tool install --force "git+https://github.com/kyalpha313/xhs-cli-headless"
uv tool uninstall xiaohongshu-cli  # 干掉旧包冲突 (按 xhs.exe shim 名卸载)

# 2. 验证
xhs --version  # 应该 0.8.9+

# 3. 装 playwright chromium (用国内镜像加速)
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://npmmirror.com/mirrors/playwright"
python -m playwright install chromium

# 4. 装 DrissionPage (skill 1/2/3 都用)
pip install DrissionPage
# (注: 已装在系统 Python, 装在 user 环境的 Python 也行)

# 5. 导 cookies 登录
# Chrome 装 Cookie-Editor 扩展 → xiaohongshu.com → 导出 JSON → 存为 cookies.json
xhs auth import --file cookies.json
xhs auth doctor  # 验证 login_status: valid

# 6. 验证 captcha 状态
xhs search "AI 副业" --sort popular --json  # 应有输出
xhs comments <note_id> --json              # 大概率 captcha (改 web 路径)
```

---

## 🚨 故障速查表（症状 → 立刻做什么）

| 症状 | 立即做什么 |
|---|---|
| `xhs search` 返回 `not_authenticated` | 重新 `xhs auth import --file cookies.json`（cookie 死了） |
| `xhs search` 返回 `Captcha required: type=216` | 等 5-30 min 自动解，或 `xhs login` 重登 |
| `xhs search` 返回 `Captcha required: type=unknown` | captcha 限流更严，等 30-60 min |
| `xhs comments` 永远 captcha（即使 search 通） | **绕开 API，改 web 路径**（见 §9） |
| `xhs --version` 是 0.6.4 | `uv tool install --force git+https://github.com/kyalpha313/xhs-cli-headless` |
| 多个 uv tool 都有 `xhs` shim | `uv tool uninstall xiaohongshu-cli`（按 shim 名） |
| DrissionPage 首次启动 5+ 分钟没反应 | 改 `set_browser_path(SYSTEM_CHROME_PATH)` |
| `page.run_js("1+1")` 返回 None | 加 `as_expr=True` 参数 |
| Chrome 跑 playwright 报 port 被占 | `Get-Process chrome \| Stop-Process -Force` 后重启 |
| 抽到粉丝数但全是 0 | 别信 `xhs search-user`，改 web 抓 `.shows="粉丝"` |
| `xhs status` OK 但搜不到东西 | 检查 `xhs auth doctor` 的 recommended_action |
| pain-miner 抓不到 xsec_token | scanner.py 修复: `results.append` 加 `"xsec_token": n["xsec_token"]` |
| xhs comments 报 "Could not resolve xsec_token" | 改用完整 URL `?xsec_token=...` 或 `--xsec-token` flag |
| batch 跑 1 个关键词后整场 captcha | 用 per-keyword 隔离 (skill 3 已内置) |
| 客户端乱码但文件正常 | 写到文件，PowerShell 不用看 |
| **Python 脚本 print emoji 在 Windows GBK 终端崩溃** | **脚本顶部加 `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`**（POSTMORTEM #17 升级版）|
| **API key 写进代码被 commit** | **永远走环境变量 + `.env` 文件 + `.gitignore` 排除**（POSTMORTEM #21）|
| **auto_fill API 返回的 [TODO: ...] 没填满** | 1) prompt 显式说"包括标题部分"; 2) body_skeleton 取到 ## 📝 标题; 3) head 不含 标题 section |
| **scrapling `page.text` 在 xhs 返 0 字节, 抓不到标题/作者/点赞** | 用 `page.html_content`（1MB+ 完整 HTML, 含 `__INITIAL_STATE__` JSON）— 不是 `text`（POSTMORTEM #25）|
| **PowerShell `Set-Content -Encoding utf8` 写 cookie 文件带 BOM, Python json.loads 失败** | 用 `encoding="utf-8-sig"` 读 cookies, 自动剥 BOM（POSTMORTEM #26）|
| **xhs `likedCount":"2万"` 用 `int()` 失败 (返 0)** | 用 `parse_xhs_count()` 解析"2万"→20000, "1.5万"→15000（POSTMORTEM #27）|
| **scrapling `disable_resources=True` + `network_idle=True` 在 xhs SPA 死循环** | 改 `disable_resources=False`（POSTMORTEM #28）|
| **DeepSeek 模型名 `deepseek-flash` 不存在返 400 Bad Request** | 用 `deepseek-chat`（自动 alias 到 v4-flash 直答）或 `deepseek-v4-flash`（reasoning）（POSTMORTEM #29）|
| **`cover_analyzer.py` 端到端跑抛 `ValueError: ... is not in the subpath of ...`** | out-dir 在 PROJECT_ROOT 外时 `cover_path.relative_to(PROJECT_ROOT)` 抛错 → 加 `try/except` + `str(cover_path).startswith(str(PROJECT_ROOT))` fallback（POSTMORTEM #30）|
| **Python f-string 嵌中文双引号 `"..."` 报 SyntaxError** | Python 把第一个 `"` 当字符串结束符 → 改用 `「」` 或单引号 `‘…’`（POSTMORTEM #31）|
| **中文双引号 SyntaxError 第二次触发**（topic_generator.py）| 写 f-string 默认用 `「」` 而不是 `""`（POSTMORTEM #32）|

---

## 📚 详细问题库

### 1. xhs-cli 升级冲突

**症状**：`uv tool install xhs-cli-headless` 后 `xhs --version` 还是 0.6.4

**根因**：旧 `xiaohongshu-cli 0.6.4` 装的 `xhs.exe` shim 还占着，新装虽成功但 shim 路径冲突。

**修复**：
```powershell
uv tool install --force "git+https://github.com/kyalpha313/xhs-cli-headless"
uv tool uninstall xiaohongshu-cli  # ⚠️ 按可执行名卸载，不是包名
```

**教训**：`uv tool uninstall` 卸载的是**可执行文件**（如 `xhs.exe`），不是 `package` 名。先 `uv tool list` 看哪个 package 提供了这个 shim。

---

### 2. xhs session 死掉

**症状**：`xhs search` 返回 `not_authenticated` / `Session expired`

**根因**：xhs 服务端把 cookies 标 invalid（多因 captcha 触发后服务端主动 kill session）

**修复**：
```powershell
# 方式 1: 重新导 cookies (Chrome 里还登着的话)
# Chrome 装 Cookie-Editor 扩展 → xhs.com → 导出 JSON
xhs auth import --file cookies.json
xhs auth doctor  # 看 recommended_action

# 方式 2: 重新 QR 登录 (如果 Chrome 也登不上了)
xhs login --qr-output C:\path\qr.png  # 保存 PNG
# 扫图后自动恢复
```

**教训**：captcha 触发 1 次后，**xhs 会主动 invalid 当前 session 的全部 cookies**。所以"captcha 限流"的恢复时间比"session 死亡"短得多（前者 5-30 min，后者可能要重登）。

---

### 3. xhs QR 登录在 PowerShell 显示乱码

**症状**：`xhs login` 终端打印的 QR 是 `鈻堚枅鈻堚枅` 这种方块字符，扫不上

**根因**：PowerShell 默认 codepage 是 GBK，xhs-cli 用 Unicode box-drawing 字符画 QR，GBK 解析不了

**修复**：
```powershell
xhs login --qr-output C:\path\qr.png  # 存成 PNG
# 然后用 Read 工具显示图片
```

**教训**：**永远用文件方式**保存 QR，不要试图在终端看。`--qr-output FILE` 是 xhs-cli 0.8.9 的官方修复。

---

### 4. Cookie-Editor 导出格式

**症状**：导出的 cookies.json 导入后 `xhs auth doctor` 报"缺必需 cookies"

**根因**：xhs-cli's `_normalize_cookie_map` 接受 3 种格式：
- `[{"name": "a1", "value": "...", "domain": ".xiaohongshu.com", ...}]` ← Cookie-Editor 导出
- `{"a1": "...", "web_session": "..."}` ← xhs-cli 默认格式
- markdown 链接形式（skill 自己解析）

**必需 cookies**：
- `a1`（设备指纹）
- `web_session`（短 token）
- `id_token`（OAuth）

**推荐 cookies**（加上更稳）：
- `gid`, `websectiga`, `sec_poison_id`, `xsecappid`

**修复**：Cookie-Editor 选 "JSON" 格式导出即可。xhs-cli 自动解析。

---

### 5. xhs-cli `Captcha triggered` WARNING 误报

**症状**：
```
WARNING:xhs_cli.client:Captcha triggered (count=1)
{ "ok": false, "error": { "code": "verification_required" } }
```
但有时：
```
WARNING:xhs_cli.client:Captcha triggered (count=1)
{ "ok": true, "data": {...} }   ← 实际成功！
```

**根因**：xhs-cli 内部限流计数器和实际 API 响应是**分离的**。限流触发后请求还会发，但有时会碰巧不被拦。

**修复**：**永远信任实际 JSON**。代码里：
```python
if not payload.get("ok"):  # 看 ok 字段，不看 stderr WARNING
    err = payload.get("error", {})
    ...
```

**教训**：xhs-cli 的 stderr 警告是**限流检测器**的内部状态，不是实际响应。**生产代码只看 JSON**。

---

### 6. DrissionPage `run_js` 静默返回 None

**症状**：
```python
page.run_js("1+1")  # 返回 None（不是 2）
page.run_js("document.body.innerText")  # 返回 None
```

**根因**：DrissionPage 4.1.1.2 的 `run_js` 默认走 `Runtime.callFunctionOn`，把 JS 包成 `function(){...}` 后调用。在**某些页面上下文**（Vue/React SPA）会静默返回 undefined → Python 看到 None。

**修复**：加 `as_expr=True` 走 `Runtime.evaluate`：
```python
page.run_js("1+1", as_expr=True)  # 2
page.run_js("document.body.innerText", as_expr=True)  # 真实 text
```

**教训**：**所有 DrissionPage 4.1.1.2 的 `run_js` 调用都加 `as_expr=True`**。这是这个版本的默认 bug，下版本可能修但不能赌。

**调试技巧**：如果 page.title 正常但所有 JS 都 None，就是这个 bug。

---

### 7. DrissionPage 首次启动卡 5+ 分钟

**症状**：第一次 `ChromiumPage()` 卡住，进程不退出

**根因**：DrissionPage 找 `PATH` 上的 `chrome` 找不到，默认去下 130MB Chromium

**修复**：
```python
from DrissionPage import ChromiumOptions
opts = ChromiumOptions()
opts.set_browser_path(r"C:\Users\张哥\AppData\Local\Google\Chrome\Application\chrome.exe")
page = ChromiumPage(opts)
```

**教训**：**永远用系统 Chrome**，别让 DrissionPage 下 Chromium。`set_browser_path` 是 v4.0+ 必加项。

---

### 8. Chrome 僵尸进程占端口 9222

**症状**：
```
playwright._impl._errors.Error: BrowserType.launch: Executable doesn't exist at ...
```
或
```
Error: listen EADDRINUSE :::9222
```

**根因**：之前 Playwright / DrissionPage 启动的 Chrome 没正常退出，留下 21+ 个 zombie 进程

**修复**：
```powershell
Get-Process chrome -ErrorAction SilentlyContinue | Stop-Process -Force
```

**教训**：跑 browser 自动化前**先清进程**。DrissionPage / Playwright 的 launch 异常退出时 Chrome 不会自尽。

---

### 9. xhs profile URL 重定向 captcha / search

**症状**：
```python
page.get("https://www.xiaohongshu.com/user/profile/5c519dad000000001202ca0d")
# → 自动重定向到 https://www.xiaohongshu.com/explore
# → 不显示用户主页
```

**根因**：xhs 反爬对**没有 xsec_token 的 profile URL** 直接重定向到 /explore，强制走搜索流量

**修复**：URL 必须拼 user.xsec_token：
```python
profile_url = f"https://www.xiaohongshu.com/user/profile/{user_id}?xsec_token={user_xsec_token}&xsec_source=pc_search"
page.get(profile_url)
```

**user.xsec_token** 从 search 结果的 `note_card.user.xsec_token` 拿（**不是 note 的 xsec_token**！）

**教训**：
- 任何 xhs URL 都带 `xsec_token` query
- 一定要从搜索结果里的 user/node 对象的 xsec_token 拿
- 两个 token 别混用（note 的 vs user 的）

---

### 10. xhs `search-user` API fans_total 永远 0

**症状**：
```json
"fans_total": 0  // 100K 粉的账号也返回 0
```

**根因**：xhs 反爬默认把 `fans_total` 字段清 0

**修复**：**别用 xhs search-user**，改 web 抓 `.shows="粉丝"`：
```javascript
const nodes = document.querySelectorAll('.shows');
for (const n of nodes) {
  if (n.textContent.trim() === '粉丝') {
    return n.parentElement.innerText;  // "1万+\n粉丝"
  }
}
```

**教训**：xhs 的 `0` 经常是反爬默认值，不是真实数据。验证方法是看用户其他公开信息是否也是 0。

---

### 11. xhs `user/otherinfo` API 返 500

**症状**：
```json
{ "ok": false, "data": null, "msg": "create invoker failed, service: jarvis-gateway-default" }
```

**根因**：xhs 服务端 jarvis-gateway 限流 user info 接口

**修复**：**不用这个 API**，改 web 抓 .shows="粉丝"（见 §10）

---

### 12. xhs comments API 永远 captcha（最大坑）

**症状**：
```powershell
xhs comments <note_id> --all --json
# → Captcha required: type=unknown
# 哪怕只跑 1 次也 captcha
```

**根因**：xhs comments API 是**最严的限流接口**，触发 captcha 后整个 session 都要重登

**重大发现**：xhs **web 页面限流比 API 宽松 10x+**！同样 session：
- xhs search API: 87 笔记 0 captcha
- xhs comments API: 1 次就 captcha
- xhs web /explore/<id>: 87 笔记 0 captcha

**修复**：走 web 抓 `.comment-item` DOM：
```python
page.get("https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xt}&xsec_source=pc_search")
page.wait_for_timeout(3500)
# 滚动加载所有评论
for _ in range(3):
    page.scroll.to_bottom()
    page.wait_for_timeout(1200)
# 抓 DOM
items = page.run_js("document.querySelectorAll('.comment-item').length", as_expr=True)
# 每个 .comment-item 含 content / author / like / ip / is_author / is_sub
```

**教训**：**xhs 限流规则：API 严，web 宽**。任何高频操作都优先 web。

---

### 13. scanner.py 不暴露 xsec_token 字段（破坏下游）

**症状**：`xhs comments` 报 "Could not resolve xsec_token for comments"

**根因**：scanner.py 的 `results.append()` 没把 xsec_token 暴露为顶层字段（虽然嵌在 url 里）

**修复**：在 results.append 加：
```python
results.append({
    "note_id": n["note_id"],
    "xsec_token": n["xsec_token"],  # ← 加上这一行
    ...
})
```

**教训**：**字段隔离**：重要 token/ID 必须独立字段，不能藏在 URL 字符串里。下游用 URL 解析代码脆弱。

---

### 14. xhs comments API 强制 xsec_token

**症状**：
```json
{ "ok": false, "error": { "message": "Could not resolve xsec_token for comments" } }
```

**根因**：xhs-cli 0.8.9 强制要求 xsec_token（不管是 ID 还是 URL 形式）

**修复**：传完整 URL：
```python
cmd = [XHS_BIN, "comments", f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xt}", "--all", "--json"]
```

或者用 `--xsec-token` flag：
```python
cmd = [XHS_BIN, "comments", note_id, "--xsec-token", xt, "--all", "--json"]
```

**教训**：**xhs-cli 0.8.9 任何需要 xsec_token 的命令都明确传**（不要靠它"自动找"）。

---

### 15. pain-miner 报 "xsec_token missing" 后还是 captcha

**症状**：传了 xsec_token，还是 captcha

**根因**：xhs comments API 限流太严，**第一次调用就 captcha**

**修复**：**整个弃用 xhs comments API**，改用 DrissionPage 抓 web（见 §12）

---

### 16. batch pipeline captcha 串全场

**症状**：batch 跑 1 关键词 captcha 后，所有后续关键词的 pain-miner 都失败

**根因**：xhs comments API captcha 是 session 级的，整场共用一个 session

**修复**：per-keyword 隔离 pain-miner：
```python
# 不要一锅炖
for keyword, payload in scanner_results:
    # 每个 keyword 独立 subprocess
    p = run_pain_miner_for_keyword(keyword, ...)  # 独立
```

**教训**：**captcha 隔离原则**：任何"批处理 + API 调用"都按 chunk 隔离，1 个 chunk 失败不能影响其他 chunk。

---

### 17. PowerShell 中文乱码

**症状**：
```
[batch] loaded 8 notes
note: '正在努力的人 - 小红书'  # 这是 title，但中文乱码显示成正常字符（GBK 解码 Unicode 失败时的"空"）
```

**根因**：PowerShell 默认 codepage 是 cp936 (GBK)，Python 默认 stdout 也是 GBK

**修复 A**（写文件）：
```python
# 文件永远是 UTF-8 OK
Path(out).write_text(text, encoding="utf-8")
```

**修复 B**（终端显示）：
```powershell
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
python script.py
```

**修复 C**（Python 脚本自身）：
```python
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
```

**教训**：**不要在 PowerShell 终端看 Python 输出**，写到文件然后用 Read 工具看。

---

### 18. scanner 修复后**必须重跑**才能有 xsec_token 字段

**症状**：scanner.py 修复后，老的 ai-fuyue-full-v4.json 还是没 xsec_token

**根因**：scanner 输出是**一次性产物**，修复代码不修复 JSON 文件

**修复**：每次修复 scanner 后，重跑 scanner 拿新输出：
```powershell
python scanner.py "AI 副业" --min-likes 500 --output json --out "fresh.json"
```

**教训**：**不要用旧的输出文件验证新代码**。修复后第一个动作是**重跑**。

---

### 19. Chrome Cookie 抽取时 Chrome 占文件锁

**症状**：
```python
browser_cookie3.chrome()  # 失败
# shadowcopy.exceptions.RequiresAdminError: This operation requires admin
```

**根因**：Chrome 进程占用 Cookies SQLite 文件，无法 shadow copy

**修复 A**：关 Chrome 5 秒抽：
```powershell
Get-Process chrome | Stop-Process -Force
python -c "import browser_cookie3; print(len(list(browser_cookie3.chrome(domain_name='xiaohongshu.com'))))"
Start-Process chrome  # 立即重启
```

**修复 B**（用户手动）：Chrome 装 Cookie-Editor 扩展，导 JSON

**教训**：浏览器 cookies 抽取都要**关浏览器**或**用扩展**。**永远不要用 browser_cookie3 当 Chrome 在跑时**。

---

### 20. DrissionPage `as_expr=True` 不被记起来的连锁问题

**症状**：scanner 粉丝抓取、pain-miner web 抓取都用 `as_expr=True`，但**记不清哪些函数加了哪些没加**

**根因**：多次 debug 期间部分函数加了 `as_expr=True`，部分没加，行为不一致

**修复**：在团队文档（这里）写明**所有 DrissionPage `run_js` 调用都加 `as_expr=True`**

**教训**：约定优于配置。**所有 browser 自动化代码用统一 wrapper**：
```python
def safe_js(page, script):
    return page.run_js(script, as_expr=True)
```

---

### 21. API key 写进代码 / 提交 / 复制粘贴

**症状**：在 chat 里贴 `sk-xxx...` 给 AI，AI 直接 hardcode 到 .py 文件，git commit 后 key 泄露

**根因**：图省事 + 不知道 API key 该怎么管

**修复**（4 件套）：
1. **环境变量**：API key 永远走 `os.environ.get("DEEPSEEK_API_KEY")`，不写死
2. **`.env` 文件**：本地开发用 `.env` 存真 key（`DEEPSEEK_API_KEY=sk-...`），**不进 git**
3. **`.env.example` 模板**：commit 进 git 的占位文件（`DEEPSEEK_API_KEY=sk-your-key-here`）
4. **`.gitignore` 加 `.env` 和 `*.filled.md`**（避免误提交生成的仿写）

**正确的 API key 链条**：
```
用户 shell: $env:DEEPSEEK_API_KEY="sk-..."
        ↓
Python: os.environ.get("DEEPSEEK_API_KEY")
        ↓
HTTP: Authorization: Bearer sk-...
```

**绝不做**：
- ❌ 把 `sk-xxx` 写进 `auto_fill.py`
- ❌ 把 `.env` commit 到 git
- ❌ 在 PowerShell 长期保存 `setx DEEPSEEK_API_KEY "sk-..."`（会进注册表）
- ❌ 把 API key 截图 / 复制粘贴到公开地方

**安全的临时使用**（仅当前 session）：
```powershell
$env:DEEPSEEK_API_KEY="sk-xxx..."  # 只在当前 PowerShell 窗口有效
python auto_fill.py --batch ...
```
关掉 PowerShell 就消失。

**教训**：**任何 API key 都走 env var + .env + .gitignore 三件套**。这是最低成本的"防泄露"。


**症状**：scanner 粉丝抓取、pain-miner web 抓取都用 `as_expr=True`，但**记不清哪些函数加了哪些没加**

**根因**：多次 debug 期间部分函数加了 `as_expr=True`，部分没加，行为不一致

**修复**：在团队文档（这里）写明**所有 DrissionPage `run_js` 调用都加 `as_expr=True`**

**教训**：约定优于配置。**所有 browser 自动化代码用统一 wrapper**：
```python
def safe_js(page, script):
    return page.run_js(script, as_expr=True)
```

---

## 🚀 Setup 速查

### 工具版本（截至 2026-06-09）

| 工具 | 版本 | 安装 |
|---|---|---|
| xhs-cli-headless | 0.8.9 | `uv tool install --force git+https://github.com/kyalpha313/xhs-cli-headless` |
| DrissionPage | 4.1.1.2 | `pip install DrissionPage`（系统 Python 已装） |
| playwright | 1.59.0 | `python -m playwright install chromium` |
| Python | 3.14 | 系统 |

### 关键路径

```
C:\Users\张哥\.local\bin\xhs.exe                         ← xhs CLI
C:\Users\张哥\.xiaohongshu-cli\cookies.json              ← 登录态
C:\Users\张哥\AppData\Local\Google\Chrome\Application\chrome.exe  ← 系统 Chrome
C:\Users\张哥\Downloads\web-clipper-master\              ← 项目
├── STATUS.md                                            ← 任务连续性
├── POSTMORTEM.md                                        ← 本文
├── skills/
│   ├── xhs-trending-scanner/                            ← Skill 1
│   ├── xhs-comment-pain-miner/                          ← Skill 2
│   └── batch-keyword-pipeline/                          ← Skill 3
└── output/                                              ← 输出
```

---

## 🎯 关键数字（性能基线）

| 任务 | 时间 | 输出 |
|---|---|---|
| 1 关键词 MVP 搜索 | 1.6s | 20 notes |
| 1 关键词完整模式（带粉丝） | 100s | 9 viral notes with fans |
| 1 关键词 pain-miner (web, 18 notes) | 395s | 47 pains |
| 5 关键词 batch（含 pain-miner） | 2024s (~34min) | 87 viral + 159 pains |
| xhs 评论 web 抓取 | ~22s/条 | 19-39 评论 |
| DrissionPage 启动（首次） | 1.8s | — |

---

## 📊 已知性能瓶颈

| 瓶颈 | 现状 | 优化方向 |
|---|---|---|
| batch 顺序跑 30+ 分钟 | 现状 | 并发跑 (但 captcha 风险) |
| pain-miner 22s/条（DrissionPage 启动 + 滚动 + 抓取） | 现状 | 复用单个 DrissionPage 实例 |
| 规则分类 70% 准确率 | 现状 | Skill 4 用 LLM 二次清洗 |
| xhs web 抓评论有限速（虽比 API 宽） | 现状 | 不可知 |

---

## 🔮 后续工作

### Skill 4 (LLM 重构) — 下一步

- **推荐方案**：用我（Claude Sonnet 4.x）+ mimeng-writer 风格
- 输入：Skill 1+2 输出的 viral + pains
- 输出：爆款公式（标题反推、开头 hook、内容结构、CTA、3 个仿写骨架）
- 成本：0（已付 Claude 订阅）
- 启动：5 分钟

### Skill 5 (Obsidian 同步)

- 输入：batch 输出（viral + pains）
- 输出：vault/小红书爆款/{date}/{keyword}.md
- 工具：mimeng-writer（文档结构）+ Python 文件系统操作

### 长期优化

- **并发 batch**：多账号轮换 + IP 池（但 captcha 风险）
- **LLM 二次清洗**：用我跑 95% 准确率重分类痛点
- **Lark 集成**：把痛点自动同步到飞书表格
- **A/B 测试**：用 Skill 4 生成的 3 个标题仿写，自动发布到 xhs 测试点击率
