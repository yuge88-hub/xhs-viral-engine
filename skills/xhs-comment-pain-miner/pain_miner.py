#!/usr/bin/env python3
"""xhs-comment-pain-miner — Skill 2: 评论区痛点挖掘

Pipeline:
  Skill 1 results JSON (note_id + title + url)
  → xhs comments <note_id> --all --json (拉全部评论 + 子评论)
  → 展平 + 规则分类 (pain / question / criticism / request / suggestion / praise)
  → 过滤太短评论 + 作者自己 (show_tags 包含 is_author)
  → 按 like_count 降序
  → 输出 JSON / Markdown

用法:
  python pain_miner.py --input <skill1-output.json> --output markdown
  python pain_miner.py --note-ids "id1,id2,id3" --min-likes 5 --output json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

XHS_BIN = r"C:\Users\张哥\.local\bin\xhs.exe"
COOKIE_PATH = Path(r"C:\Users\张哥\.xiaohongshu-cli\cookies.json")

# 分类规则 (基于关键词 + 标点)
# 顺序很重要: 命中前面的优先
CATEGORIES = [
    ("criticism", [
        r"假[的呢]?$", r"割韭菜", r"骗子", r"骗人", r"不靠谱", r"假的",
        r"纯广告", r"硬广", r"营销号", r"恰烂钱", r"智商税",
        r"求证[实]?", r"实锤", r"挂[一你他]",
    ]),
    ("request", [
        r"求[资教程料]", r"怎么找", r"哪里[有找买]", r"链接", r"求分享",
        r"有木有", r"有没", r"资源", r"求[一]?[个]?出处", r"原[出处文]",
        r"在哪[里]?买", r"tb[?]?搜[什么]", r"求带",
    ]),
    ("pain", [
        r"不会[做弄用]?", r"做不[出会了]", r"学不[会懂]", r"搞不定",
        r"试了[好几]?\d*[次天个]", r"失败[了过]?", r"没[效果成效用]",
        r"好难[啊哦]?", r"难[啊啊啊]?", r"崩溃", r"放弃",
        r"怎么破", r"求指点", r"求教", r"小白[求助]?",
        r"困扰", r"焦虑", r"烦[死人]?", r"卡[住了住]",
    ]),
    ("question", [
        r"^[怎么如何什那哪那][一-龥]*?[?？]",  # 中文章节问句开头
        r"是[不]?[是对]?\d*[错]?$", r"对吗[?？]?$",
        r"可[以]?不[可以]?[行]?", r"能[不]?[能行]?",
        r"[哪那][个些]?[比更好]?", r"哪种[好]?",
    ]),
    ("suggestion", [
        r"建议", r"希望", r"如果.*就[更好完美]",
        r"BGM[太]?[大]", r"字幕[太]?[小不清晰]",
        r"声音[太大清]",
    ]),
    ("praise", [
        r"^牛[比]?[!！]?$", r"nb[!！]?", r"厉害[了!！]?", r"学习[到]?[了]?",
        r"谢谢[分享]?", r"感谢[分]?享", r"思路[确实]?可[以行]",
        r"有用[！!]?", r"已[经]?收[藏]?[藏了]",
        r"讲的[很]?[好棒]", r"讲得[很]?[好清楚]",
    ]),
]


def classify(content: str) -> list[str]:
    """返回匹配到的所有类别 (一句评论可能多标签)"""
    c = content.strip()
    if not c or len(c) < 4:
        return ["noise"]
    if len(c) > 500:
        # 太长多半是科普文摘抄，跳过
        return ["noise"]
    labels = []
    for label, patterns in CATEGORIES:
        for p in patterns:
            if re.search(p, c, re.IGNORECASE):
                labels.append(label)
                break
    if not labels:
        return ["neutral"]
    return labels


def run_xhs_comments(note_id: str, xsec_token: str = "") -> dict | None:
    """拉单条 note 的全部评论. xhs-cli 0.8.9 强制要求 xsec_token (不然 api_error)."""
    if xsec_token:
        # 0.8.9 推荐: 传完整 URL (xsec_token 在 query 里)
        url = f"https://www.xiaohongshu.com/explore/{note_id}?xsec_token={xsec_token}"
        cmd = [XHS_BIN, "comments", url, "--all", "--json"]
    else:
        # 兜底 (会失败)
        cmd = [XHS_BIN, "comments", note_id, "--all", "--json"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=120)
    if r.returncode != 0:
        return None
    try:
        payload = json.loads(r.stdout)
        if not payload.get("ok"):
            err = payload.get("error", {})
            print(f"    ⚠ [{note_id}] api error: {err.get('code', '?')}: {err.get('message', '?')[:80]}",
                  file=sys.stderr)
            return None
        return payload
    except json.JSONDecodeError:
        return None


def run_xhs_web_comments(note_id: str, xsec_token: str = "") -> dict | None:
    """通过 DrissionPage 抓 note 页面的评论 DOM (bypass xhs comments API captcha).

    xhs comments API 限流极严, web 页面限流宽松很多. 优势:
      - 同一个 session 可以连续抓多条不触发 captcha
      - 数据完整: content / user / likes / IP / author / sub-comments 全有
    """
    if not xsec_token:
        print(f"    ⚠ [{note_id}] web 路径需要 xsec_token (从 scanner 的 results[xsec_token] 拿)", file=sys.stderr)
        return None
    try:
        from DrissionPage import ChromiumPage  # noqa: PLC0415
    except ImportError:
        print(f"    ⚠ DrissionPage not installed", file=sys.stderr)
        return None

    # 加载 cookies
    if not COOKIE_PATH.exists():
        return None
    raw = json.loads(COOKIE_PATH.read_text(encoding="utf-8"))
    cookies = {k: str(v) for k, v in raw.items() if k != "saved_at"}

    page = ChromiumPage()
    try:
        for k, v in cookies.items():
            try:
                page.set.cookies({"name": k, "value": v, "domain": ".xiaohongshu.com", "path": "/"})
            except Exception:
                pass
        # warmup
        page.get("https://www.xiaohongshu.com", timeout=15)
        import time as _t
        _t.sleep(1.2)
        # go to note page
        import urllib.parse as _u
        note_url = (
            f"https://www.xiaohongshu.com/explore/{note_id}"
            f"?xsec_token={_u.quote(xsec_token)}&xsec_source=pc_search"
        )
        page.get(note_url, timeout=20)
        _t.sleep(3.5)
        # 滚动触发懒加载
        for _ in range(3):
            page.scroll.to_bottom()
            _t.sleep(1.2)
        _t.sleep(1.0)

        # 检查是否 404
        if "error_code" in page.url or "页面不见" in (page.title or ""):
            print(f"    ⚠ [{note_id}] 404 (note 暂时无法访问)", file=sys.stderr)
            return None

        # 抓所有 .comment-item (含 sub)
        comments_json = page.run_js("""
            (() => {
                const out = [];
                document.querySelectorAll('.comment-item').forEach(item => {
                    const contentEl = item.querySelector('.note-text, [class*="note-text"]');
                    const content = contentEl ? contentEl.innerText.trim() : '';
                    const authorLink = item.querySelector('.author a.name, .author a[href*="/user/profile/"]');
                    const nickname = authorLink ? authorLink.innerText.trim() : '';
                    // 找 like 数: .like 里的数字
                    const likeEl = item.querySelector('.like, [class*="like-wrapper"]');
                    const likeText = likeEl ? likeEl.innerText.trim() : '';
                    let likes = 0;
                    const lm = likeText.match(/^(\\d+)/);
                    if (lm) likes = parseInt(lm[1]);
                    // 找 IP + 日期
                    const infoEl = item.querySelector('.info .date, .info');
                    const infoText = infoEl ? infoEl.innerText.trim() : '';
                    let ip_loc = '', date = '';
                    // 形如 "2024-06-27重庆" 或 "2024-06-27 重庆"
                    const dm = infoText.match(/(\\d{4}-\\d{2}-\\d{2})\\s*(.*)/);
                    if (dm) { date = dm[1]; ip_loc = dm[2].trim(); }
                    // is_author: 找 .labels 里含 "作者" 字样
                    const labels = item.querySelector('.labels');
                    const labelText = labels ? labels.innerText : '';
                    const is_author = labelText.includes('作者');
                    const is_sub = item.classList.contains('comment-item-sub');
                    out.push({
                        id: item.id || '',
                        content, nickname, likes, is_sub, is_author, ip_loc, date, label: labelText
                    });
                });
                return JSON.stringify(out);
            })()
        """, as_expr=True)
        if not comments_json:
            print(f"    ⚠ [{note_id}] web 抓取返回空", file=sys.stderr)
            return None
        comments = json.loads(comments_json)
        if not comments:
            print(f"    ⚠ [{note_id}] web 抓取 0 评论", file=sys.stderr)
            return None
        # 包成 xhs-cli 同款 schema
        return {
            "ok": True,
            "schema_version": "1",
            "data": {
                "user_id": "",
                "comments": [
                    {
                        "id": c["id"],
                        "content": c["content"],
                        "like_count": str(c["likes"]),
                        "ip_location": c["ip_loc"],
                        "sub_comment_count": "0",  # web 路径不拿子评论, 已经展平在主列表
                        "sub_comment_has_more": False,
                        "liked": False,
                        "show_tags": ["is_author"] if c["is_author"] else [],
                        "user_info": {
                            "user_id": "",
                            "nickname": c["nickname"],
                            "image": "",
                        },
                        "_is_sub_web": c["is_sub"],  # 标记 web 路径下的子评论
                    } for c in comments
                ],
            },
        }
    except Exception as e:
        print(f"    ⚠ [{note_id}] web 抓取异常: {str(e)[:100]}", file=sys.stderr)
        return None
    finally:
        try:
            page.quit()
        except Exception:
            pass


def detect_captcha(payload: dict | None) -> bool:
    """从 xhs-cli 返回里探测 captcha."""
    if not payload:
        return False
    if not payload.get("ok"):
        err = payload.get("error", {})
        return "captcha" in err.get("code", "").lower() or "verif" in err.get("code", "").lower()
    return False


def flatten_comments(data: dict) -> list[dict]:
    """展平 comments + sub_comments 成一条条评论"""
    out = []
    for c in (data.get("data") or {}).get("comments") or []:
        flat = _normalize_comment(c, is_sub=False)
        if flat:
            out.append(flat)
        for sc in c.get("sub_comments") or []:
            sub_flat = _normalize_comment(sc, is_sub=True)
            if sub_flat:
                out.append(sub_flat)
    return out


def _normalize_comment(c: dict, is_sub: bool) -> dict | None:
    content = (c.get("content") or "").strip()
    if not content:
        return None
    user = c.get("user_info") or {}
    try:
        likes = int(c.get("like_count") or 0)
    except (TypeError, ValueError):
        likes = 0
    show_tags = c.get("show_tags") or []
    is_author = "is_author" in show_tags
    return {
        "id": c.get("id", ""),
        "content": content,
        "likes": likes,
        "is_sub": is_sub,
        "is_author": is_author,
        "nickname": user.get("nickname", ""),
        "ip_location": c.get("ip_location", ""),
        "create_time": c.get("create_time", 0),
    }


def load_skill1_results(path: Path) -> list[dict]:
    """支持两种 input 格式: Skill 1 results JSON, 或 Skill 1 viral-table.md (粗略解析)"""
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        payload = json.loads(text)
        if isinstance(payload, dict) and "results" in payload:
            return payload["results"]
        if isinstance(payload, list):
            return payload
    elif path.suffix in (".md", ".markdown"):
        # markdown 格式: [link](https://www.xiaohongshu.com/explore/<note_id>?xsec_token=...)
        return [
            {"note_id": m.group(1), "title": line.lstrip("| ").split("|")[1].strip() if "|" in line else "", "url": m.group(0)}
            for line in text.splitlines()
            for m in [re.search(r"explore/([0-9a-f]{24})", line)]
            if m
        ]
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1] if "\n" in __doc__ else "")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", help="Skill 1 的结果 JSON / Markdown 路径")
    src.add_argument("--note-ids", help="逗号分隔的 note_id 列表 (手动指定)")
    ap.add_argument("--min-likes", type=int, default=0, help="评论最小点赞数 (0=全保留)")
    ap.add_argument("--min-content-len", type=int, default=6, help="评论最小字符数 (过滤太短)")
    ap.add_argument("--top-per-note", type=int, default=10, help="每条笔记保留前 N 痛点")
    ap.add_argument("--exclude-author", action="store_true", default=True, help="排除作者自己评论")
    ap.add_argument("--sleep", type=float, default=4.0, help="每条 note 间基础延迟 (秒)")
    ap.add_argument("--jitter", type=float, default=0.5, help="延迟随机抖动 (±秒)")
    ap.add_argument("--max-consecutive-captcha", type=int, default=2,
                    help="连续 captcha 多少次自动暂停 (避免被封号)")
    ap.add_argument("--use-web", action="store_true", default=True,
                    help="默认走 DrissionPage web 抓取 (限流宽松, 推荐)")
    ap.add_argument("--no-web", dest="use_web", action="store_false",
                    help="强制走 xhs-cli API (会触发 captcha)")
    ap.add_argument("--categories", default="pain,question,criticism,request,suggestion",
                    help="保留的类别 (逗号分隔, 默认不含 praise/neutral/noise)")
    ap.add_argument("--output", choices=["json", "markdown"], default="json")
    ap.add_argument("--out", default="-", help="落盘路径, '-' 表 stdout")
    args = ap.parse_args()

    # 1. load notes
    if args.input:
        notes = load_skill1_results(Path(args.input))
    else:
        notes = [{"note_id": nid.strip(), "title": "", "url": ""}
                 for nid in args.note_ids.split(",") if nid.strip()]
    if not notes:
        print("no notes loaded", file=sys.stderr)
        return 1
    print(f"[pain-miner] loaded {len(notes)} notes", file=sys.stderr)

    # 2. 保留的类别白名单
    keep = set(c.strip() for c in args.categories.split(",") if c.strip())

    # 3. 拉评论 + 分类 (带 captcha-aware 退避)
    t0 = time.time()
    per_note_results = []
    total_comments = 0
    total_pain = 0
    consecutive_captcha = 0
    for i, note in enumerate(notes, 1):
        nid = note.get("note_id", "")
        if not nid:
            continue
        print(f"  [{i}/{len(notes)}] {nid}: pulling comments…", file=sys.stderr)
        # xhs-cli 0.8.9 强制要求 xsec_token (从 Skill 1 normalize_note 拿)
        xsec = note.get("xsec_token", "")
        # 默认走 web 路径 (DrissionPage, 限流宽松), xhs-cli comments API 作 fallback
        if args.use_web:
            data = run_xhs_web_comments(nid, xsec_token=xsec)
        else:
            data = run_xhs_comments(nid, xsec_token=xsec)
        if not data and args.use_web:
            # web 失败兜底
            data = run_xhs_comments(nid, xsec_token=xsec)
        if not data:
            # 可能是 captcha 或 session 失效
            print(f"    ⚠ no data (captcha? session expired?)", file=sys.stderr)
            consecutive_captcha += 1
            if consecutive_captcha >= args.max_consecutive_captcha:
                print(f"\n[pain-miner] ABORT: 连续 {consecutive_captcha} 次失败, 触发限流熔断", file=sys.stderr)
                print(f"  建议: 等 10-30 分钟或重登 xhs login 后再试", file=sys.stderr)
                break
            # backoff: 失败一次, 多 sleep 一下
            time.sleep(args.sleep * 2)
            continue
        consecutive_captcha = 0  # 重置
        comments = flatten_comments(data)
        total_comments += len(comments)
        # 分类
        for c in comments:
            c["categories"] = classify(c["content"])
        # 过滤
        filtered = []
        for c in comments:
            if args.exclude_author and c["is_author"]:
                continue
            if len(c["content"]) < args.min_content_len:
                continue
            if c["likes"] < args.min_likes:
                continue
            # 类别过滤
            if not any(cat in keep for cat in c["categories"]):
                continue
            filtered.append(c)
        # 排序 + 截 Top N
        filtered.sort(key=lambda c: (c["likes"], len(c["content"])), reverse=True)
        top = filtered[:args.top_per_note]
        total_pain += len(top)
        per_note_results.append({
            "note_id": nid,
            "title": note.get("title", ""),
            "url": note.get("url", ""),
            "total_comments": len(comments),
            "kept_comments": len(filtered),
            "top_pains": top,
        })
        print(f"    {len(comments)} comments → {len(filtered)} kept → top {len(top)}", file=sys.stderr)

        # 随机延迟 (3-8s 推荐范围, 防 captcha)
        if i < len(notes):
            import random
            delay = args.sleep + random.uniform(-args.jitter, args.jitter)
            delay = max(0.5, delay)
            time.sleep(delay)

    # 4. 输出
    payload = {
        "skill": "xhs-comment-pain-miner",
        "version": "0.1.0",
        "input_notes": len(notes),
        "filters": {"min_likes": args.min_likes, "min_content_len": args.min_content_len,
                    "exclude_author": args.exclude_author, "categories": list(keep),
                    "top_per_note": args.top_per_note},
        "stats": {
            "total_comments": total_comments,
            "total_kept_pain": total_pain,
            "elapsed_sec": round(time.time() - t0, 1),
        },
        "per_note": per_note_results,
    }

    if args.output == "json":
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        text = render_markdown(payload)
    if args.out == "-":
        print(text)
    else:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"[pain-miner] wrote {args.out} ({total_pain} pain points)", file=sys.stderr)
    return 0


def render_markdown(p: dict) -> str:
    lines = [
        f"# 小红书评论区痛点挖掘",
        "",
        f"- 输入笔记: {p['input_notes']} 条",
        f"- 抓评论: {p['stats']['total_comments']} 条",
        f"- 命中痛点: **{p['stats']['total_kept_pain']}** 条",
        f"- 耗时: {p['stats']['elapsed_sec']}s",
        f"- 过滤: 点赞>={p['filters']['min_likes']}, 字符>={p['filters']['min_content_len']}, 排除作者, 类别={p['filters']['categories']}",
        "",
    ]
    for note in p["per_note"]:
        if not note["top_pains"]:
            continue
        title = (note["title"] or "").replace("|", "\\|")[:50]
        lines.append(f"## {title} (`{note['note_id'][:8]}…`)")
        lines.append("")
        lines.append(f"共 {note['total_comments']} 评论，命中 {note['kept_comments']} 条，Top {len(note['top_pains'])}：")
        lines.append("")
        for c in note["top_pains"]:
            cats = "/".join(c["categories"])
            content = c["content"].replace("|", "\\|").replace("\n", " ")
            sub_marker = "↪ " if c["is_sub"] else ""
            author_marker = " (作者)" if c["is_author"] else ""
            lines.append(f"- **{c['likes']}赞** {sub_marker}`[{cats}]` {content}{author_marker}")
            lines.append(f"  — @{c['nickname']} · {c['ip_location']}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
