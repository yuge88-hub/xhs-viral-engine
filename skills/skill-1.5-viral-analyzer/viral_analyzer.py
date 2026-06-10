"""
viral_analyzer.py — Skill 1.5 viral-analyzer (4问+6维)

输入: note_id + xsec_token (+ 可选 author info)
工具: scrapling.StealthyFetcher (系统 Chrome + stealth, 不下 Chromium)
LLM:  DeepSeek API (分析 4 问 + 6 维)
输出: output/skill-1.5-viral-analyzer-v0.1/{note_id}-analysis.json + {note_id}-4问+6维.md

用法:
    python viral_analyzer.py --note-id 666c0258000000001c0207a2 --xsec-token ABmsNJn...

关键点:
- xhs 必须带 xsec_token, 否则 404
- scrapling 默认从 ~/.xiaohongshu-cli/cookies.json 读 cookies
- DeepSeek 走 env DEEPSEEK_API_KEY, 没 key 也能跑（只输出元数据，4问6维填空）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

# 防 PowerShell GBK 乱码
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# scrapling 抓 xhs note
try:
    from scrapling.fetchers import StealthyFetcher, StealthySession
except ImportError:
    print("ERROR: scrapling 没装。pip install scrapling", file=sys.stderr)
    sys.exit(1)

# 项目根
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "skill-1.5-viral-analyzer-v0.1"
COOKIES_PATH = Path.home() / ".xiaohongshu-cli" / "cookies.json"
CHROME_COOKIES_PATH = Path(__file__).parent / "cookies-chrome.json"  # 项目本地 Chrome 导出的


# ============================================================
# 抓 xhs note (scrapling + cookies)
# ============================================================

def load_cookies(extra_path: str = "") -> list[dict[str, Any]]:
    """读 xhs cookies, 返回 scrapling 格式 list[{name, value, domain, path, httpOnly, secure, sameSite}]

    优先级:
    1. --cookies-file 参数指定的文件
    2. 项目本地 cookies-chrome.json (Chrome Cookie-Editor 导出)
    3. ~/.xiaohongshu-cli/cookies.json (xhs-cli 扁平格式)

    支持 3 种输入格式:
    - Chrome list:  [{name, value, domain, path, httpOnly, secure, sameSite, ...}]
    - xhs-cli 扁平: {"a1": "value1", "web_session": "value2", ...}
    - xhs-cli 嵌套: {"a1": {"value": "v1", "domain": "..."}, ...}
    """
    candidates: list[Path] = []
    if extra_path:
        candidates.append(Path(extra_path))
    candidates.append(CHROME_COOKIES_PATH)
    candidates.append(COOKIES_PATH)

    for path in candidates:
        if not path.exists():
            continue
        try:
            # ⚠️ 用 utf-8-sig 兼容 PowerShell Set-Content -Encoding utf8 写的 BOM
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as e:
            print(f"WARN: 读 {path} 失败: {e}", file=sys.stderr)
            continue

        out = _parse_cookies(data)
        if out:
            print(f"  cookies 源: {path.name} ({len(out)} 个)")
            return out

    print(f"WARN: 没找到可用 cookies 文件, scrapling 会触发 login 重定向", file=sys.stderr)
    return []


def _parse_cookies(data: Any) -> list[dict[str, Any]]:
    """把 3 种输入格式统一转 scrapling list 格式"""
    out: list[dict[str, Any]] = []

    if isinstance(data, list):
        # Chrome Cookie-Editor 格式
        # 关键: Playwright 期望字段是 `expires` (Unix 秒), Chrome 用 `expirationDate`
        for c in data:
            if not isinstance(c, dict) or "name" not in c or "value" not in c:
                continue
            entry = {
                "name": c["name"],
                "value": c["value"],
                "domain": c.get("domain", ".xiaohongshu.com"),
                "path": c.get("path", "/"),
            }
            # expirationDate → expires (Playwright 字段名)
            if "expirationDate" in c and c["expirationDate"]:
                # Chrome 可能是 float (Unix 秒) 或 int, 统一成 int
                try:
                    entry["expires"] = int(float(c["expirationDate"]))
                except (ValueError, TypeError):
                    pass
            # session cookies: expirationDate=-1 或不存在, 不传 expires
            # httpOnly/secure/sameSite: 缺省不传, scrapling 走默认
            for k in ("httpOnly", "secure", "sameSite"):
                if c.get(k) is not None:
                    entry[k] = c[k]
            out.append(entry)
        return out

    if isinstance(data, dict):
        # xhs-cli 两种格式
        for name, info in data.items():
            if isinstance(info, str):
                value = info
            elif isinstance(info, dict) and "value" in info:
                value = info["value"]
            else:
                continue  # 元数据 (saved_at, loadts) 跳过
            out.append({
                "name": name,
                "value": value,
                "domain": ".xiaohongshu.com",
                "path": "/",
            })
        return out

    return []


def fetch_note_dom(note_id: str, xsec_token: str, cookies_file: str = "") -> str:
    """scrapling 抓 note 页面, 返回 HTML

    用 StealthySession 持久 context (注入 cookies 后 warmup 首页, 再抓 note).
    直接 StealthyFetcher.fetch() 会重置 context, cookies 注入被吃.
    """
    url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={quote(xsec_token)}&xsec_source=pc_search"

    cookies = load_cookies(cookies_file)
    print(f"  fetch: {url[:80]}...")
    print(f"  cookies: {len(cookies)} 个")

    with StealthySession(
        headless=True,
        real_chrome=True,  # 走系统 Chrome, 避免下 Chromium
        cookies=cookies,
        solve_cloudflare=True,
        block_webrtc=True,
        allow_webgl=True,
        # ⚠️ 不要 disable_resources=True — xhs 是 SPA, 没 JS bundle 不渲染
        wait=3000,
        network_idle=True,
        timeout=60000,  # 加到 60s, 等 SPA 渲染
        max_pages=2,  # 1 warmup + 1 note
        load_dom=True,  # 等 DOM ready
    ) as session:
        # 1. warmup 首页 — POSTMORTEM #3: xhs web 抓 note 必须先 warmup, 否则重定向
        print("  warmup 首页...")
        session.fetch("https://www.xiaohongshu.com", wait=2000, network_idle=True)

        # 2. 抓 note — 等更久, 让 SPA 完整渲染
        print("  抓 note (等 5s 让 SPA 渲染)...")
        page = session.fetch(url, wait=5000, network_idle=True)

    # ⚠️ POSTMORTEM v0.1 bug: `page.text` 在 xhs SPA 渲染时返回 0 字节 (因为 body text 走 JS 注入)
    # 正确路径: 用 `page.html_content` (1MB+ 完整 HTML, 包含 __INITIAL_STATE__ JSON)
    return page.html_content


# ============================================================
# 规则解析 DOM (提取元数据)
# ============================================================

def parse_xhs_count(s: str) -> int | None:
    """xhs 中文数字解析: '749' / '2.4万' / '10+' / '1万+' → int

    返回 None 解析失败。
    """
    if not s:
        return None
    s = s.strip().rstrip("+")
    m = re.match(r"^(\d+(?:\.\d+)?)\s*([万千]?)$", s)
    if not m:
        return None
    num = float(m.group(1))
    unit = m.group(2)
    if unit == "万":
        return int(num * 10000)
    if unit == "千":
        return int(num * 1000)
    return int(num)


def extract_meta(html: str, note_id: str, xsec_token: str) -> dict[str, Any]:
    """从 HTML 提标题/作者/正文/标签/数据/日期。

    xhs 是 SPA, 数据大多在 JSON state 里塞进 #__INITIAL_STATE__ 或 window.__INITIAL_SSR_STATE__。

    ⚠️ POSTMORTEM #27: xhs 数字带"万/千"中文单位 (e.g. "2.4万"), 用 parse_xhs_count() 解析, 不能直接 int()
    ⚠️ fans/follows 不在 note 页 HTML, 须另抓 user profile (留给 Skill 1 拿)
    """
    meta: dict[str, Any] = {
        "note_id": note_id,
        "url": f"https://www.xiaohongshu.com/explore/{note_id}",
        "xsec_token": xsec_token[:16] + "...",  # 不全存
    }

    # 1. 标题 (h1 或 og:title)
    title_match = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
    if not title_match:
        title_match = re.search(r'<title>([^<]+)</title>', html)
    meta["title"] = title_match.group(1) if title_match else None

    # 2. 描述 (og:description, 通常包含正文摘要)
    desc_match = re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', html)
    meta["description"] = desc_match.group(1) if desc_match else None

    # 3. 作者 (从 og:title 或 .author 提取)
    author_match = re.search(r'"nickname"\s*:\s*"([^"]+)"', html)
    meta["author"] = author_match.group(1) if author_match else None

    # 4. 数据 (likes/collects/comments)
    # xhs 返回的 likedCount/collectedCount 是字符串带中文单位 (e.g. "2万", "1.5万", "749")
    # commentCount 通常纯数字
    for field, pattern in [
        ("likes", r'"likedCount"\s*:\s*"([^"]+)"|"likes"\s*:\s*"([^"]+)"'),
        ("collects", r'"collectedCount"\s*:\s*"([^"]+)"|"collects"\s*:\s*"([^"]+)"'),
        ("comments", r'"commentCount"\s*:\s*"([^"]+)"|"commentCount"\s*:\s*(\d+)'),
    ]:
        m = re.search(pattern, html)
        raw = (m.group(1) or m.group(2)) if m else None
        meta[field] = parse_xhs_count(raw) if raw else None

    # 5. 粉丝数 (从 user 节点拿) — ⚠️ note 页 HTML 通常不含 user.fans, 留给 Skill 1
    fans_match = re.search(r'"fans"\s*:\s*"([^"]+)"|"fansCount"\s*:\s*"([^"]+)"', html)
    raw = (fans_match.group(1) or fans_match.group(2)) if fans_match else None
    meta["fans"] = parse_xhs_count(raw) if raw else None

    # 6. 发布日期 (xhs __INITIAL_STATE__ 里 lastUpdateTime / time, 毫秒时间戳)
    time_m = re.search(r'"lastUpdateTime"\s*:\s*(\d+|"(\d+)")|"time"\s*:\s*(\d{10,13})', html)
    if time_m:
        ts_str = time_m.group(1) or time_m.group(2) or time_m.group(3) or ""
        ts = int(ts_str.strip('"') or 0)
        if ts > 1_000_000_000_000:  # ms
            ts //= 1000
        if ts > 1_500_000_000:  # 2017-07 +，合理
            from datetime import datetime, timezone
            meta["publish_date"] = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        else:
            meta["publish_date"] = None
    else:
        meta["publish_date"] = None

    # 7. 标签 — 优先 og:keywords (逗号分隔), 兜底从正文中 #xxx 提取
    og_kw = re.search(r'<meta[^>]+name="keywords"[^>]+content="([^"]+)"', html)
    tags: list[str] = []
    if og_kw:
        for kw in og_kw.group(1).split(","):
            kw = kw.strip()
            if kw and not re.match(r"^[a-f0-9]{3,8}$", kw, re.IGNORECASE):  # 滤掉 hex colors (#fff, #f5f5f5)
                tags.append(kw)
    if not tags:
        # 兜底: 从 body 抽 #xxx
        body_text = meta.get("body") or meta.get("description") or ""
        for m in re.finditer(r"#(\w[\w一-龥]+)", body_text):
            t = m.group(1)
            if not re.match(r"^[a-f0-9]{3,8}$", t, re.IGNORECASE):
                tags.append(t)
    meta["tags"] = list(dict.fromkeys(tags))[:20]

    # 8. 正文 — 优先 og:description, 兜底 __INITIAL_STATE__ 的 desc
    if not meta.get("description"):
        body_match = re.search(r'"desc"\s*:\s*"([^"]{20,2000})"', html)
        meta["body"] = body_match.group(1) if body_match else None
    else:
        meta["body"] = meta["description"]

    return meta


# ============================================================
# DeepSeek LLM: 4 问 + 6 维
# ============================================================

DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"


def call_deepseek(prompt: str, system: str = "", max_tokens: int = 4000) -> str:
    """调 DeepSeek chat completion, 走 requests (无 SDK 依赖)"""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return ""  # 没 key 跳过, 让 caller fallback
    import requests

    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system} if system else {"role": "system", "content": "你是小红书爆款分析专家。"},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,  # 低温度, 稳定
    }
    try:
        r = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"WARN: DeepSeek 调用失败: {e}", file=sys.stderr)
        return ""


def build_4q6d_prompt(meta: dict[str, Any]) -> tuple[str, str]:
    """构造 4 问 + 6 维的 prompt"""
    system = "你是小红书爆款分析专家,擅长从单条笔记反推爆款规律。回答必须用中文,具体到原文引用。"

    user = f"""# 任务
分析下面这条小红书爆款笔记,严格按 4 问 + 6 维 输出。

# 笔记元数据
- 标题: {meta.get('title') or '?'}
- 作者: {meta.get('author') or '?'}
- 粉丝: {meta.get('fans') or '?'}
- 点赞: {meta.get('likes') or '?'}
- 收藏: {meta.get('collects') or '?'}
- 评论: {meta.get('comments') or '?'}
- 发布日期: {meta.get('publish_date') or '?'}
- 标签: {meta.get('tags') or []}
- 正文: {(meta.get('body') or '?')[:1500]}

# 4 问 (必答, 每问 1-3 句, 必须引用原文证据)

## 1. WHO — 谁在看?(人群画像)
从标签/正文/标题推断年龄、地域、认知、需求类型。必须附原文依据。

## 2. WHY CLICK — 为什么点开?
拆解标题/封面/选题,各 1 句话说明"哪个元素让人点开"。引用原文。

## 3. HOW FLOW — 内容怎么讲下去?
开头/中间/结尾分别怎么写?用 1-2 句话说清楚结构,引用原文。

## 4. WHERE LEAD — 用户被带去哪里?
最终 CTA 是什么(关注/收藏/购买/评论)?用证据说明。

# 6 维 (必答, 每维 2-4 句)

## 维度一:角色 DNA
作者用什么身份说话?第一人称频率?权威感怎么建立?叙事视角?引用原文 2 句作证据。

## 维度二:读者画像
年龄/地域/认知水平/核心需求(信息/情绪/工具/认知/娱乐),统计各类型占比。必附原文依据。

## 维度三:内容结构
逐段统计字数(表格:段落|字数|类型|与主题关系),提取开头规律/中段分布/收尾模式。

## 维度四:语言风格
用词层级(高频 3-5 词)、句式特征(短句比例/问句/排比)、修辞手法(比喻/排比/反问/夸张,各判断有/无+原文)、标点习惯(感叹号频率)。

## 维度五:约束规则
- 禁用词逆向(检查 15+ 常见套话是否缺席,如:颠覆/风口/赛道/治愈/内耗)
- 格式(小标题/加粗/列表/空行,有/无)
- 内容边界(回避什么)

## 维度六:工作流逻辑
信息源(个人经验/专业知识/外部数据)?开头与正文关系?哪些段落固定(每篇都有)?收尾有无固定表达?

# 输出格式
直接回答,不用 markdown 标题,每个维度用 `## 维度X` 分段。最后给一段 50 字内的"爆款核心要素"总结。
"""
    return system, user


def parse_4q6d(text: str) -> dict[str, Any]:
    """解析 LLM 输出回 4 问 + 6 维 dict"""
    result: dict[str, Any] = {
        "4_questions": {},
        "6_dimensions": {},
        "summary": "",
    }
    if not text:
        return result

    # 4 问
    q_patterns = [
        ("who", r"## 1\. WHO[^\n]*\n+(.*?)(?=## 2|$)", "人群画像"),
        ("why_click", r"## 2\. WHY CLICK[^\n]*\n+(.*?)(?=## 3|$)", "为什么点开"),
        ("how_flow", r"## 3\. HOW FLOW[^\n]*\n+(.*?)(?=## 4|$)", "内容结构"),
        ("where_lead", r"## 4\. WHERE LEAD[^\n]*\n+(.*?)(?=# 6 维|## 维度|$)", "CTA"),
    ]
    for key, pattern, label in q_patterns:
        m = re.search(pattern, text, re.DOTALL)
        result["4_questions"][key] = {
            "label": label,
            "content": m.group(1).strip() if m else "",
        }

    # 6 维
    d_patterns = [
        ("role_dna", r"## 维度一[^\n]*\n+(.*?)(?=## 维度二|$)"),
        ("reader_profile", r"## 维度二[^\n]*\n+(.*?)(?=## 维度三|$)"),
        ("content_structure", r"## 维度三[^\n]*\n+(.*?)(?=## 维度四|$)"),
        ("language_style", r"## 维度四[^\n]*\n+(.*?)(?=## 维度五|$)"),
        ("constraint_rules", r"## 维度五[^\n]*\n+(.*?)(?=## 维度六|$)"),
        ("workflow_logic", r"## 维度六[^\n]*\n+(.*?)(?=## 维度|# 总结|## 总结|$)"),
    ]
    for key, pattern in d_patterns:
        m = re.search(pattern, text, re.DOTALL)
        result["6_dimensions"][key] = m.group(1).strip() if m else ""

    # 总结
    summary_match = re.search(r"## 总结[^\n]*\n+(.*?)$|## 爆款核心要素[^\n]*\n+(.*?)$", text, re.DOTALL)
    if summary_match:
        result["summary"] = (summary_match.group(1) or summary_match.group(2) or "").strip()

    return result


# ============================================================
# 输出
# ============================================================

def write_markdown(out_path: Path, meta: dict, parsed: dict, raw_llm: str) -> None:
    """输出 4 问 + 6 维 markdown"""
    lines = [
        f"# 拆爆款: {meta.get('title', '?')}",
        "",
        f"> **note_id**: `{meta.get('note_id')}`  ",
        f"> **作者**: {meta.get('author', '?')}  ",
        f"> **粉丝/点赞/收藏/评论**: {meta.get('fans', '?')} / {meta.get('likes', '?')} / {meta.get('collects', '?')} / {meta.get('comments', '?')}  ",
        f"> **发布日期**: {meta.get('publish_date', '?')}  ",
        f"> **URL**: {meta.get('url')}",
        "",
        "---",
        "",
        "## 🎯 4 问框架",
        "",
    ]
    q_labels = {
        "who": "👥 WHO — 谁在看?",
        "why_click": "👆 WHY CLICK — 为什么点开?",
        "how_flow": "📖 HOW FLOW — 内容怎么讲?",
        "where_lead": "🏁 WHERE LEAD — 用户被带去哪里?",
    }
    for key, label in q_labels.items():
        q = parsed["4_questions"].get(key, {})
        lines.append(f"### {label}")
        lines.append("")
        lines.append(q.get("content", "_无_"))
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 🧬 6 维拆解")
    lines.append("")
    d_labels = {
        "role_dna": "维度一:角色 DNA",
        "reader_profile": "维度二:读者画像",
        "content_structure": "维度三:内容结构",
        "language_style": "维度四:语言风格",
        "constraint_rules": "维度五:约束规则",
        "workflow_logic": "维度六:工作流逻辑",
    }
    for key, label in d_labels.items():
        content = parsed["6_dimensions"].get(key, "")
        lines.append(f"### {label}")
        lines.append("")
        lines.append(content or "_无_")
        lines.append("")

    if parsed.get("summary"):
        lines.append("---")
        lines.append("")
        lines.append("## 💡 爆款核心要素")
        lines.append("")
        lines.append(parsed["summary"])
        lines.append("")

    if not raw_llm and not any(parsed["4_questions"].values()):
        lines.append("---")
        lines.append("")
        lines.append("> ⚠️ **DeepSeek API 未配置 / 调用失败** — 4 问 6 维为空。请设置 `$env:DEEPSEEK_API_KEY` 后重跑。")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_json(out_path: Path, meta: dict, parsed: dict, raw_llm: str) -> None:
    out = {
        "skill": "skill-1.5-viral-analyzer",
        "version": "0.1.0",
        "meta": meta,
        "4_questions": parsed["4_questions"],
        "6_dimensions": parsed["6_dimensions"],
        "summary": parsed.get("summary", ""),
        "raw_llm_output": raw_llm[:3000] if raw_llm else "",
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


# ============================================================
# Main
# ============================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Skill 1.5 viral-analyzer — 拆爆款 4 问 + 6 维",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--note-id", required=True, help="xhs note_id (24位 hex)")
    parser.add_argument("--xsec-token", required=True, help="xhs xsec_token (从 Skill 1 scanner 拿)")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR), help="输出目录")
    parser.add_argument("--skip-llm", action="store_true", help="跳过 DeepSeek, 只输出元数据")
    parser.add_argument("--cookies-file", default="", help="指定 cookies 文件 (Chrome Cookie-Editor 格式 / xhs-cli 格式)")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Skill 1.5 viral-analyzer v0.1.0 ===")
    print(f"note_id: {args.note_id}")
    print(f"out_dir: {out_dir}\n")

    # 1. 抓
    print(">>> Step 1: scrapling 抓 note 页面")
    try:
        html = fetch_note_dom(args.note_id, args.xsec_token, args.cookies_file)
    except Exception as e:
        print(f"ERROR: 抓取失败: {e}", file=sys.stderr)
        return 1

    # 2. 解析元数据
    print(">>> Step 2: 规则解析 DOM")
    meta = extract_meta(html, args.note_id, args.xsec_token)
    title_safe = meta.get("title") or "?"
    author_safe = meta.get("author") or "?"
    likes_safe = meta.get("likes") if meta.get("likes") is not None else "?"
    collects_safe = meta.get("collects") if meta.get("collects") is not None else "?"
    comments_safe = meta.get("comments") if meta.get("comments") is not None else "?"
    print(f"  标题: {title_safe[:60]}")
    print(f"  作者: {author_safe}")
    print(f"  点赞/收藏/评论: {likes_safe}/{collects_safe}/{comments_safe}")

    if not meta.get("title"):
        print("WARN: 没抓到标题, 可能是 login 重定向. 检查 cookies.", file=sys.stderr)

    # 3. LLM 4 问 + 6 维
    parsed = {"4_questions": {}, "6_dimensions": {}, "summary": ""}
    raw_llm = ""
    if not args.skip_llm and os.environ.get("DEEPSEEK_API_KEY"):
        print(">>> Step 3: DeepSeek LLM 跑 4 问 + 6 维")
        system, user = build_4q6d_prompt(meta)
        raw_llm = call_deepseek(user, system, max_tokens=4000)
        if raw_llm:
            parsed = parse_4q6d(raw_llm)
            print(f"  4 问填充: {sum(1 for v in parsed['4_questions'].values() if v.get('content'))}/4")
            print(f"  6 维填充: {sum(1 for v in parsed['6_dimensions'].values() if v)}/6")
        else:
            print("  LLM 返回空, 4 问 6 维留空")
    else:
        print(">>> Step 3: 跳过 LLM (无 DEEPSEEK_API_KEY 或 --skip-llm)")

    # 4. 输出
    print(">>> Step 4: 落盘")
    md_path = out_dir / f"{args.note_id}-4问+6维.md"
    json_path = out_dir / f"{args.note_id}-analysis.json"
    write_markdown(md_path, meta, parsed, raw_llm)
    write_json(json_path, meta, parsed, raw_llm)
    print(f"  ✓ {md_path}")
    print(f"  ✓ {json_path}")

    print(f"\n=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
