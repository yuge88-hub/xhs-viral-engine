#!/usr/bin/env python3
"""xhs-trending-scanner — Skill 1: find low-follower viral notes on Xiaohongshu.

Pipeline:
  1. xhs search <kw> --json (CLI from xhs-cli-headless)
  2. Pre-filter: likes >= min_likes
  3. Dedupe by user_id
  4. Fetch fans per author (API -> playwright fallback)
  5. Final filter: fans < max_followers
  6. Emit JSON or Markdown

Usage:
  python scanner.py "AI 副业" --max-followers 3000 --min-likes 1000
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

XHS_BIN = os.environ.get("XHS_BIN", r"C:\Users\张哥\.local\bin\xhs.exe")
COOKIE_PATH = Path(os.environ.get("XHS_COOKIE_PATH", r"C:\Users\张哥\.xiaohongshu-cli\cookies.json"))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

# -------- core helpers --------

def run_xhs_search(keyword: str, sort: str, page: int) -> list[dict]:
    """Call `xhs search` and return the raw note items."""
    cmd = [XHS_BIN, "search", keyword, "--sort", sort, "--json", "--page", str(page)]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"xhs search failed: {r.stderr[:200]}")
    payload = json.loads(r.stdout)
    if not payload.get("ok"):
        raise RuntimeError(f"xhs search returned not-ok: {r.stdout[:200]}")
    return payload.get("data", {}).get("items", []) or []


def normalize_note(item: dict) -> dict | None:
    """Reduce a raw xhs search item to the fields we need."""
    card = item.get("note_card") or {}
    user = card.get("user") or {}
    inter = card.get("interact_info") or {}
    try:
        likes = int(inter.get("liked_count") or 0)
    except (TypeError, ValueError):
        likes = 0
    try:
        collects = int(inter.get("collected_count") or 0)
    except (TypeError, ValueError):
        collects = 0
    try:
        comments = int(inter.get("comment_count") or 0)
    except (TypeError, ValueError):
        comments = 0
    try:
        shares = int(inter.get("shared_count") or 0)
    except (TypeError, ValueError):
        shares = 0
    publish_time = ""
    for tag in (card.get("corner_tag_info") or []):
        if tag.get("type") == "publish_time":
            publish_time = tag.get("text", "")
            break
    if not user.get("user_id") or not item.get("id"):
        return None
    return {
        "note_id": item["id"],
        "xsec_token": item.get("xsec_token", ""),
        "title": card.get("display_title", ""),
        "user_id": user["user_id"],
        "nickname": user.get("nickname") or user.get("nick_name", ""),
        "avatar": user.get("avatar", ""),
        "user_xsec_token": user.get("xsec_token", ""),  # user 自己的 xsec_token (拼 profile URL 用)
        "likes": likes,
        "collects": collects,
        "comments": comments,
        "shares": shares,
        "publish_time": publish_time,
        "note_url": f"https://www.xiaohongshu.com/explore/{item['id']}?xsec_token={item.get('xsec_token','')}",
        "profile_url": f"https://www.xiaohongshu.com/user/profile/{user['user_id']}?xsec_token={user.get('xsec_token','')}&xsec_source=pc_search",
    }


def load_cookies() -> dict[str, str]:
    if not COOKIE_PATH.exists():
        return {}
    raw = json.loads(COOKIE_PATH.read_text(encoding="utf-8"))
    return {k: str(v) for k, v in raw.items() if k != "saved_at"}


# -------- fans fetch: API first, playwright fallback --------

def fetch_fans_api(user_id: str, cookies: dict) -> int | None:
    """Try the public xhs user-info API. Returns int fans or None on failure."""
    try:
        import requests  # noqa: PLC0415
    except ImportError:
        return None
    try:
        r = requests.get(
            "https://www.xiaohongshu.com/api/sns/web/v1/user/otherinfo",
            params={"target_user_id": user_id},
            cookies=cookies,
            headers={"User-Agent": UA, "Referer": "https://www.xiaohongshu.com/",
                     "Origin": "https://www.xiaohongshu.com"},
            timeout=10,
        )
        if r.status_code != 200:
            return None
        j = r.json()
        data = j.get("data") or {}
        fans = data.get("fans") or data.get("fans_total")
        return int(fans) if fans is not None else None
    except Exception:
        return None


def fetch_fans_playwright(user_id: str, cookies: dict, xsec_token: str = "") -> int | None:
    """Playwright 浏览器取作者粉丝数。

    路径: warmup 主页 → 直接进 profile URL (带 user 自己的 xsec_token) → DOM 找 .shows="粉丝"
    """
    if not user_id or not xsec_token:
        return None
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError:
        return None
    pw_cookies = [
        {"name": k, "value": v, "domain": ".xiaohongshu.com", "path": "/"}
        for k, v in cookies.items()
    ]
    import urllib.parse as _u
    profile_url = (
        f"https://www.xiaohongshu.com/user/profile/{user_id}"
        f"?xsec_token={_u.quote(xsec_token)}&xsec_source=pc_search"
    )
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch(headless=True, channel="chrome")
            except Exception:
                browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=UA)
            if pw_cookies:
                ctx.add_cookies(pw_cookies)
            page = ctx.new_page()
            try:
                page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(1000)
                page.goto(profile_url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(3000)
                text = page.evaluate("""
                    (() => {
                        const nodes = document.querySelectorAll('.shows');
                        for (const n of nodes) {
                            if ((n.textContent || '').trim() === '粉丝') {
                                const p = n.parentElement;
                                return p ? p.innerText : '';
                            }
                        }
                        return '';
                    })()
                """) or ""
            finally:
                browser.close()
            if not text:
                return None
            import re
            m = re.search(r"([\d.,]+)\s*([万wW]?)\+?", text)
            if not m:
                return None
            num = float(m.group(1).replace(",", ""))
            if m.group(2):
                num *= 10000
            return int(num)
    except Exception:
        return None


def fetch_fans(user_id: str, source: str, cookies: dict, xsec_token: str = "") -> tuple[int | None, str]:
    """Returns (fans, source_used). source_used ∈ {api, playwright, drissionpage, none}.

    xsec_token 必须是 user 自己的 (从 search 结果的 note_card.user.xsec_token 拿)。
    """
    if source in ("auto", "api"):
        fans = fetch_fans_api(user_id, cookies)
        if fans is not None:
            return fans, "api"
        if source == "api":
            return None, "none"
    if source in ("auto", "playwright"):
        fans = fetch_fans_playwright(user_id, cookies, xsec_token=xsec_token)
        if fans is not None:
            return fans, "playwright"
    if source in ("auto", "drissionpage"):
        fans = fetch_fans_drissionpage(user_id, cookies, xsec_token=xsec_token)
        if fans is not None:
            return fans, "drissionpage"
    return None, "none"


def fetch_fans_drissionpage(user_id: str, cookies: dict, xsec_token: str = "") -> int | None:
    """DrissionPage 浏览器取作者粉丝数。

    路径: warmup 主页 → 直接进 profile URL (带 user 自己的 xsec_token) → DOM 找 .shows="粉丝"

    关键: xsec_token 必须是 user 自己的 (从 search 结果的 note_card.user.xsec_token 拿)，
    不是 note 的。带对 token 后 profile 不会重定向，1 跳就行。
    """
    if not user_id or not xsec_token:
        return None
    try:
        from DrissionPage import ChromiumPage  # noqa: PLC0415
    except ImportError:
        return None
    try:
        page = ChromiumPage()
        try:
            for k, v in cookies.items():
                try:
                    page.set.cookies({"name": k, "value": str(v), "domain": ".xiaohongshu.com", "path": "/"})
                except Exception:
                    pass
            page.get("https://www.xiaohongshu.com", timeout=15)
            import time as _t
            _t.sleep(1.0)
            import urllib.parse as _u
            profile_url = (
                f"https://www.xiaohongshu.com/user/profile/{user_id}"
                f"?xsec_token={_u.quote(xsec_token)}&xsec_source=pc_search"
            )
            page.get(profile_url, timeout=20)
            _t.sleep(3.0)
            text = page.run_js("""
                (() => {
                    const nodes = document.querySelectorAll('.shows');
                    for (const n of nodes) {
                        if ((n.textContent || '').trim() === '粉丝') {
                            const p = n.parentElement;
                            return p ? p.innerText : '';
                        }
                    }
                    return '';
                })()
            """, as_expr=True) or ""
            if not text:
                return None
            import re as _r
            m = _r.search(r"([\d.,]+)\s*([万wW]?)\+?", text)
            if not m:
                return None
            num = float(m.group(1).replace(",", ""))
            if m.group(2):
                num *= 10000
            return int(num)
        finally:
            try:
                page.quit()
            except Exception:
                pass
    except Exception:
        return None


# -------- main --------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1] if "\n" in __doc__ else "")
    ap.add_argument("keyword", help="领域关键词，如 'AI 副业'")
    ap.add_argument("--max-followers", type=int, default=3000, help="作者粉丝上限")
    ap.add_argument("--min-likes", type=int, default=1000, help="笔记点赞下限")
    ap.add_argument("--sort", choices=["general", "popular", "latest"], default="popular")
    ap.add_argument("--pages", type=int, default=1, help="搜索页数（每页 ~20 条）")
    ap.add_argument("--require-fans", action="store_true",
                    help="强制取作者粉丝数并卡硬过滤 (默认关, MVP 模式只按 likes 排序, 避免触发 xhs captcha)")
    ap.add_argument("--fan-source", choices=["auto", "api", "playwright", "drissionpage"],
                    default="auto", help="粉丝数获取方式 (仅 --require-fans 开启时有效)")
    ap.add_argument("--output", choices=["json", "markdown"], default="json")
    ap.add_argument("--out", default="-", help="落盘路径，'-' 表 stdout")
    args = ap.parse_args()

    t0 = time.time()
    # 1. search
    raw_notes: list[dict] = []
    for page in range(1, args.pages + 1):
        raw_notes.extend(run_xhs_search(args.keyword, args.sort, page))
    normalized = [n for n in (normalize_note(it) for it in raw_notes) if n]
    # dedupe by note_id (search may return dupes)
    seen = set()
    unique_notes = []
    for n in normalized:
        if n["note_id"] in seen:
            continue
        seen.add(n["note_id"])
        unique_notes.append(n)

    # 2. pre-filter
    pre = [n for n in unique_notes if n["likes"] >= args.min_likes]

    # 3. dedupe authors (keep first note context per user_id for drissionpage path)
    author_first_note: dict[str, dict] = {}
    for n in pre:
        if n["user_id"] not in author_first_note:
            author_first_note[n["user_id"]] = n
    author_ids = list(author_first_note.keys())

    # 4. fetch fans (only if --require-fans)
    fans_map: dict[str, int | None] = {}
    fan_source_map: dict[str, str] = {}
    if args.require_fans:
        cookies = load_cookies()
        print(f"[scanner] 候选作者 {len(author_ids)} 个，开始取粉丝数…", file=sys.stderr)
        for i, uid in enumerate(author_ids, 1):
            ctx = author_first_note[uid]
            f, src = fetch_fans(uid, args.fan_source, cookies,
                                 xsec_token=ctx["user_xsec_token"])
            fans_map[uid] = f
            fan_source_map[uid] = src
            if f is not None:
                print(f"  [{i}/{len(author_ids)}] {uid}: {f} 粉丝 ({src})", file=sys.stderr)
            else:
                print(f"  [{i}/{len(author_ids)}] {uid}: ⚠ 取不到粉丝数 (跳过)", file=sys.stderr)
    else:
        print(f"[scanner] MVP 模式：跳过粉丝数抓取 (加 --require-fans 开启)", file=sys.stderr)

    # 5. final filter & build results
    results: list[dict] = []
    for n in pre:
        fans = fans_map.get(n["user_id"]) if args.require_fans else None
        if args.require_fans:
            if fans is None:
                continue  # 数据缺失，宁缺毋滥
            if fans >= args.max_followers:
                continue
            score = round(n["likes"] / (fans + 1), 2)
        else:
            fans = None
            score = float(n["likes"])  # MVP: 直接按 likes 排序
        results.append({
            "note_id": n["note_id"],
            "xsec_token": n["xsec_token"],  # note 自己的 xsec_token (xhs comments 强制要)
            "title": n["title"],
            "url": n["note_url"],
            "publish_time": n["publish_time"],
            "author": {
                "user_id": n["user_id"],
                "nickname": n["nickname"],
                "fans": fans,
                "fan_source": fan_source_map.get(n["user_id"]) if args.require_fans else None,
                "profile_url": n["profile_url"],
            },
            "metrics": {
                "likes": n["likes"],
                "collects": n["collects"],
                "comments": n["comments"],
                "shares": n["shares"],
            },
            "viral_score": score,
        })
    results.sort(key=lambda r: r["viral_score"], reverse=True)

    payload = {
        "skill": "xhs-trending-scanner",
        "version": "0.2.0",
        "keyword": args.keyword,
        "filter": {"max_followers": args.max_followers, "min_likes": args.min_likes,
                   "require_fans": args.require_fans, "fan_source": args.fan_source},
        "scanned_notes": len(unique_notes),
        "pre_filter_pass": len(pre),
        "unique_authors": len(author_ids),
        "fetched_fans": sum(1 for v in fans_map.values() if v is not None) if args.require_fans else 0,
        "viral_count": len(results),
        "elapsed_sec": round(time.time() - t0, 1),
        "results": results,
    }

    if args.output == "json":
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        text = render_markdown(payload)

    if args.out == "-":
        print(text)
    else:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"[scanner] wrote {args.out} ({len(results)} results)", file=sys.stderr)
    return 0


def render_markdown(p: dict) -> str:
    is_full = p["filter"].get("require_fans")
    lines = [
        f"# 小红书热门笔记 · {p['keyword']}",
        "",
        f"- 扫描笔记: **{p['scanned_notes']}** 条",
        f"- 候选作者: {p['unique_authors']} 个",
        f"- 命中结果: **{p['viral_count']}** 条",
        f"- 模式: {'完整版 (粉丝<{}, 点赞>={})'.format(p['filter']['max_followers'], p['filter']['min_likes']) if is_full else 'MVP (仅按点赞排序, 跳过粉丝数)'}",
        f"- 耗时: {p['elapsed_sec']}s",
        "",
    ]
    if is_full:
        lines += [
            "| viral | 点赞 | 收藏 | 评论 | 粉丝 | 标题 | 作者 | 链接 |",
            "|---:|---:|---:|---:|---:|---|---|---|",
        ]
    else:
        lines += [
            "| 排序分 | 点赞 | 收藏 | 评论 | 标题 | 作者 | 链接 |",
            "|---:|---:|---:|---:|---|---|---|",
        ]
    for r in p["results"]:
        title = (r["title"] or "").replace("|", "\\|")[:50]
        author = r["author"]["nickname"].replace("|", "\\|")
        if is_full:
            lines.append(
                f"| {r['viral_score']} | {r['metrics']['likes']} | {r['metrics']['collects']} "
                f"| {r['metrics']['comments']} | {r['author']['fans']} | {title} | {author} "
                f"| [link]({r['url']}) |"
            )
        else:
            lines.append(
                f"| {r['viral_score']} | {r['metrics']['likes']} | {r['metrics']['collects']} "
                f"| {r['metrics']['comments']} | {title} | {author} | [link]({r['url']}) |"
            )
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
