"""
cover_analyzer.py — Skill 1.5 封面分析 (screenshot + 视觉元素 + 文字位置)

输入: note_id + xsec_token
工具: scrapling.StealthyFetcher + screenshot (or DOM 解析)
输出: output/skill-1.5-viral-analyzer-v0.1/{note_id}-cover.png + {note_id}-cover.json

关注点:
- 封面图 (screenshot 第一屏)
- 视觉元素: 主色调 / 文字位置 / 信息密度 / 留白
- 简单 OCR (用 LLM 视觉能力 or 跳过 - 标注 TODO)

关键: xhs 视频笔记的封面通常是视频首帧,图文笔记是第一张图。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

import requests  # noqa: F401  --  备用, 实际在函数内按需 import

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

try:
    from scrapling.fetchers import StealthySession
except ImportError:
    print("ERROR: scrapling 没装。pip install scrapling", file=sys.stderr)
    sys.exit(1)

# 复用 viral_analyzer 的 cookies loader
sys.path.insert(0, str(Path(__file__).parent))
from viral_analyzer import load_cookies  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "skill-1.5-viral-analyzer-v0.1"


# ============================================================
# 抓封面图 URL (从 xhs note DOM 拿 og:image 或第一张图)
# ============================================================

def fetch_cover_url(html: str) -> list[str]:
    """从 xhs note HTML 提封面图 URL

    优先级:
    1. og:image (视频/图封面, xhs 用 name= 不是 property=)
    2. window.__INITIAL_STATE__.note.noteDetailMap[<id>].note.imageList[].urlPre (含 \\u002F 转义)
    3. imageList[].url (非空时)
    """
    urls: list[str] = []
    # 1. og:image (兼容 property= 和 name=)
    m = re.search(r'<meta[^>]+(?:property|name)="og:image"[^>]+content="([^"]+)"', html)
    if m:
        urls.append(m.group(1))
    # 2. imageList[].urlPre (xhs 默认, 带 / 转义)
    for m in re.finditer(r'"urlPre"\s*:\s*"(https?:[^"]+?)(?:!\w+)?(?:_webp|_jpg)?', html):
        raw = m.group(1).replace("\\u002F", "/").replace("\\/", "/")
        if "xhs" in raw and raw not in urls:
            urls.append(raw)
        if len(urls) >= 5:
            break
    # 3. imageList[].url 兜底
    if len(urls) < 2:
        for m in re.finditer(r'"url"\s*:\s*"(https?://sns-webpic[^"]+?)(?:!\w+)?(?:_webp|_jpg)?"', html):
            raw = m.group(1).replace("\\u002F", "/").replace("\\/", "/")
            if raw not in urls:
                urls.append(raw)
            if len(urls) >= 5:
                break
    return urls


def download_cover(url: str, out_path: Path) -> bool:
    """下载封面图 (用 requests, 不走浏览器)"""
    # 加 referer 防 xhs 403
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.xiaohongshu.com/",
    }
    try:
        r = requests.get(url, headers=headers, timeout=30, stream=True)
        r.raise_for_status()
        out_path.write_bytes(r.content)
        return True
    except Exception as e:
        print(f"WARN: 下载封面失败: {e}", file=sys.stderr)
        return False


# ============================================================
# 视觉元素分析 (规则 + LLM)
# ============================================================

def analyze_cover_rules(cover_path: Path) -> dict[str, Any]:
    """规则分析: 文件大小 / 尺寸 / 主色调 (用 PIL)

    没有 PIL 就降级到只输出文件元信息。
    """
    result: dict[str, Any] = {
        "file_size_kb": 0,
        "width": None,
        "height": None,
        "aspect_ratio": None,
        "dominant_color": None,
        "is_landscape": None,
    }
    if not cover_path.exists():
        return result

    result["file_size_kb"] = round(cover_path.stat().st_size / 1024, 1)

    try:
        from PIL import Image
    except ImportError:
        return result

    try:
        img = Image.open(cover_path)
        w, h = img.size
        result["width"] = w
        result["height"] = h
        result["aspect_ratio"] = round(w / h, 2) if h else None
        result["is_landscape"] = w > h

        # 主色调: 缩到 100x100, 取最常见 RGB
        small = img.convert("RGB").resize((100, 100))
        colors = small.getcolors(10000) or []
        if colors:
            colors.sort(key=lambda x: -x[0])
            top = colors[0][1]
            result["dominant_color"] = f"rgb({top[0]},{top[1]},{top[2]})"
            result["dominant_color_hex"] = "#{:02x}{:02x}{:02x}".format(*top)
    except Exception as e:
        print(f"WARN: PIL 分析失败: {e}", file=sys.stderr)

    return result


def analyze_cover_llm(meta: dict[str, Any], cover_path: Path) -> dict[str, Any]:
    """LLM 视觉分析: 信息密度 / 留白 / 重点区域 / 文字位置

    没用 GPT-4V 这种贵模型, 而是用文本描述 + 元数据推断, 因为:
    - DeepSeek 还没出 vision 模型
    - xhs 封面都是小红书模板化风格, 文字位置规律
    """
    # 走 DeepSeek 文本 prompt
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        return {"note": "DeepSeek API 未配置, 跳过 LLM 视觉分析"}

    # xhs 封面规律 (用规则先填, LLM 微调)
    title = meta.get("title", "")
    tags = meta.get("tags", [])

    # 文字位置判断: 标题长度 / emoji 数
    has_emoji = bool(re.search(r"[\U0001F300-\U0001F9FF🔥💰💡✨]", title))
    long_title = len(title) > 15

    prompt = f"""# 任务
分析这条小红书爆款笔记的封面。给你元数据,你推断封面的视觉风格。

# 元数据
- 标题: {title}
- 标签: {tags}
- 主色调: {meta.get('dominant_color', '?')}
- 宽高比: {meta.get('aspect_ratio', '?')}
- 横向: {meta.get('is_landscape', '?')}

# 推断 (每项 1 句话)
1. 封面类型 (图文大字 / 视频首帧 / 多图拼图 / 纯文字 / 真人出镜)
2. 标题文字位置 (顶部 / 中部 / 底部 / 覆盖全图)
3. 文字颜色 (高对比白底黑 / 黑底白 / 彩色)
4. 信息密度 (高:多行字+emoji / 中:2-3 行 / 低:1 句主打)
5. 是否真人出镜 (基于标签和标题语气推断)
6. 重点区域 (1 句话: 视觉第一眼落点)

# 输出
只回答 6 条, 不要 markdown 标题, 简短。
"""
    try:
        r = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"),
                "messages": [
                    {"role": "system", "content": "你是小红书封面视觉分析专家。"},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 500,
                "temperature": 0.3,
            },
            timeout=60,
        )
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"]
        # 简单按行解析 (LLM 输出是 6 条短句)
        lines = [ln.strip() for ln in text.strip().split("\n") if ln.strip()][:6]
        keys = ["cover_type", "title_position", "text_color", "info_density", "has_person", "focal_point"]
        return {k: (lines[i] if i < len(lines) else "") for i, k in enumerate(keys)}
    except Exception as e:
        return {"error": f"LLM 调用失败: {e}"}


# ============================================================
# Main
# ============================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Skill 1.5 cover-analyzer — 拆爆款封面")
    parser.add_argument("--note-id", required=True)
    parser.add_argument("--xsec-token", required=True)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--cookies-file", default="", help="指定 cookies 文件 (Chrome Cookie-Editor 格式)")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Skill 1.5 cover-analyzer v0.1.0 ===")
    print(f"note_id: {args.note_id}\n")

    # 1. 抓 note HTML 找封面 URL
    print(">>> Step 1: 抓 note 找封面 URL")
    url = f"https://www.xiaohongshu.com/explore/{args.note_id}?xsec_token={quote(args.xsec_token)}&xsec_source=pc_search"
    cookies = load_cookies(args.cookies_file)
    try:
        with StealthySession(
            headless=True, real_chrome=True, cookies=cookies,
            solve_cloudflare=True, block_webrtc=True,
            # ⚠️ POSTMORTEM v0.1.1: disable_resources=True + network_idle=True 死循环 (xhs SPA 需 stylesheet)
            disable_resources=False,
            wait=3000, network_idle=True, timeout=60000, max_pages=2, load_dom=True,
        ) as session:
            print("  warmup 首页...")
            session.fetch("https://www.xiaohongshu.com", wait=2000, network_idle=True)
            print("  抓 note...")
            page = session.fetch(url, wait=5000, network_idle=True)
        # ⚠️ 同 viral_analyzer.py: 用 html_content, page.text 在 xhs SPA = 0 字节
        html = page.html_content
    except Exception as e:
        print(f"ERROR: 抓取失败: {e}", file=sys.stderr)
        return 1

    cover_urls = fetch_cover_url(html)
    print(f"  找到 {len(cover_urls)} 个候选封面 URL")
    if not cover_urls:
        print("ERROR: 没找到封面图 URL, 跳过", file=sys.stderr)
        return 1

    # 2. 下载封面
    cover_path = out_dir / f"{args.note_id}-cover.png"
    cover_url = cover_urls[0]
    print(f">>> Step 2: 下载封面 {cover_url[:80]}...")
    if not download_cover(cover_url, cover_path):
        print("ERROR: 下载失败", file=sys.stderr)
        return 1
    print(f"  ✓ {cover_path} ({cover_path.stat().st_size // 1024} KB)")

    # 3. 规则分析
    print(">>> Step 3: 规则分析 (PIL 主色调+尺寸)")
    rules = analyze_cover_rules(cover_path)
    print(f"  尺寸: {rules.get('width')}x{rules.get('height')}, 主色: {rules.get('dominant_color_hex', '?')}")

    # 4. LLM 视觉推断
    print(">>> Step 4: LLM 视觉推断")
    llm_result = {}
    if not args.skip_llm:
        # 拼接规则结果给 LLM
        meta_for_llm = {**rules, "title": "?", "tags": []}
        # 试着从 HTML 抽标题
        title_m = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html)
        if title_m:
            meta_for_llm["title"] = title_m.group(1)
        tags_m = re.findall(r'#(\w[\w一-龥]+)', html)
        meta_for_llm["tags"] = list(dict.fromkeys(tags_m))[:20]
        llm_result = analyze_cover_llm(meta_for_llm, cover_path)
        print(f"  封面类型: {llm_result.get('cover_type', '?')[:60]}")

    # 5. 输出
    print(">>> Step 5: 落盘")
    cover_json = {
        "skill": "skill-1.5-cover-analyzer",
        "version": "0.1.0",
        "note_id": args.note_id,
        "cover_url": cover_url,
        # ⚠️ BUGFIX (POSTMORTEM #29): out_dir 在 PROJECT_ROOT 外时 relative_to 抛 ValueError
        # fallback: 走绝对路径 (Obsidian 同步时 Obsidian vault 通常在 web-clipper-master 外)
        "cover_local": str(cover_path.relative_to(PROJECT_ROOT)) if str(cover_path).startswith(str(PROJECT_ROOT)) else str(cover_path),
        "rules": rules,
        "llm_visual": llm_result,
    }
    out_json = out_dir / f"{args.note_id}-cover.json"
    out_json.write_text(json.dumps(cover_json, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  ✓ {out_json}")

    print(f"\n=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
