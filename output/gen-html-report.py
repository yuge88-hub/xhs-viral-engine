"""
gen_html_report.py — 5 个爆款账号的深色 dashboard HTML 报告

参考截图风格: 深蓝渐变 + 玻璃拟态 + 青绿渐变强调
单文件 HTML, 离线可开, 无外部依赖

数据源:
  - output/batch-full-5kw/viral-AI_副业.json   (19 条爆款)
  - output/skill-1.5-viral-analyzer-v0.1/{id}-analysis.json × 5
  - output/skill-1.5-viral-analyzer-v0.1/{id}-cover.json × 5
  - output/skill-4-reverse-prompts-v0.5/{id}-reverse-prompt.md × 5
  - output/batch-full-5kw/pain-miner-AI_副业.json

输出: output/AI_副业_爆款情报报告_v0.1.html
"""
from __future__ import annotations

import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = PROJECT_ROOT / "output" / "skill-1.5-viral-analyzer-v0.1"
REVERSE_DIR = PROJECT_ROOT / "output" / "skill-4-reverse-prompts-v0.5"
VIRAL_JSON = PROJECT_ROOT / "output" / "batch-full-5kw" / "viral-AI_副业.json"
PAIN_JSON = PROJECT_ROOT / "output" / "batch-full-5kw" / "pain-miner-AI_副业.json"
OUTPUT_HTML = PROJECT_ROOT / "output" / "AI_副业_爆款情报报告_v0.1.html"

# 5 个跑通拆解的爆款
NOTE_IDS = [
    "666c0258000000001c0207a2",  # 陶陶AI灵感库
    "66f8fa58000000001902e7f6",  # Sylis聊创业
    "6a168b8a000000003501caf4",  # 糕冷晓墨Ai日记
    "671f297d000000001600c2d3",  # 火光AI
    "6a0fe1c3000000003701f732",  # 野路子Robin
]


def load(p: Path) -> dict | list:
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8-sig"))


def fmt(n: int) -> str:
    if n is None:
        return "?"
    if n >= 10000:
        return f"{n / 10000:.1f}万"
    return str(n)


def esc(s: str) -> str:
    return html.escape(s or "")


# ============================================================
# 收集数据
# ============================================================

def collect() -> dict:
    viral_all = load(VIRAL_JSON)
    pain_all = load(PAIN_JSON)

    # 5 个拆解
    notes = []
    for nid in NOTE_IDS:
        a = load(ANALYSIS_DIR / f"{nid}-analysis.json")
        c = load(ANALYSIS_DIR / f"{nid}-cover.json")
        r = load(REVERSE_DIR / f"{nid}-reverse-prompt.json")
        if a:
            notes.append({
                "id": nid,
                "meta": a.get("meta", {}),
                "cover": c,
                "reverse": r,
            })

    # 5 个作者的样本笔记 (从 viral JSON 找)
    author_samples = {}
    for n in viral_all:
        if not isinstance(n, dict):
            continue
        a = n.get("author", {})
        uid = a.get("user_id")
        nid = n.get("note_id")
        if uid in [x["meta"].get("author") for x in notes] and uid not in author_samples:
            author_samples[uid] = {
                "title": n.get("title", ""),
                "url": n.get("url", ""),
                "metrics": n.get("metrics", {}),
                "publish_time": n.get("publish_time", ""),
            }
        # 也通过 nickname 匹配
        for x in notes:
            if a.get("nickname") == x["meta"].get("author") and a.get("user_id") not in author_samples:
                author_samples[a.get("user_id")] = {
                    "title": n.get("title", ""),
                    "url": n.get("url", ""),
                    "metrics": n.get("metrics", {}),
                    "publish_time": n.get("publish_time", ""),
                }

    # 痛点
    pains = []
    if isinstance(pain_all, list):
        pains = sorted(pain_all, key=lambda p: p.get("likes", 0) or 0, reverse=True)
    elif isinstance(pain_all, dict):
        pains = pain_all.get("pains") or pain_all.get("data") or []

    return {
        "viral_all": viral_all if isinstance(viral_all, list) else [],
        "notes": notes,
        "author_samples": author_samples,
        "pains": pains,
    }


# ============================================================
# HTML 模板
# ============================================================

CSS = r"""
:root {
  --bg-1: #0a0e27;
  --bg-2: #131938;
  --card: rgba(255, 255, 255, 0.04);
  --card-border: rgba(255, 255, 255, 0.08);
  --text: #e8eaf0;
  --text-dim: #9ba0b8;
  --accent-1: #6ee7b7;
  --accent-2: #5eb3ff;
  --accent-3: #c084fc;
  --warn: #fbbf24;
  --bad: #f87171;
  --bar-1: #6ee7b7;
  --bar-2: #5eb3ff;
  --bar-3: #c084fc;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif;
  background: linear-gradient(135deg, var(--bg-1) 0%, var(--bg-2) 100%);
  color: var(--text);
  min-height: 100vh;
  padding: 32px 24px;
  font-size: 14px;
  line-height: 1.5;
}
.watermark {
  position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background-image: radial-gradient(circle at 20% 30%, rgba(110, 231, 183, 0.04) 0%, transparent 40%),
                    radial-gradient(circle at 80% 70%, rgba(94, 179, 255, 0.04) 0%, transparent 40%);
}
.wrap { max-width: 1400px; margin: 0 auto; position: relative; z-index: 1; }

/* Hero */
.hero {
  background: linear-gradient(135deg, rgba(110, 231, 183, 0.08) 0%, rgba(94, 179, 255, 0.04) 100%);
  border: 1px solid var(--card-border);
  border-radius: 16px;
  padding: 32px 36px;
  margin-bottom: 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}
.hero-tag {
  font-size: 11px; letter-spacing: 0.18em; color: var(--accent-1);
  text-transform: uppercase; font-weight: 600; margin-bottom: 8px;
}
.hero h1 { font-size: 36px; font-weight: 700; margin-bottom: 8px; }
.hero .sub { color: var(--text-dim); font-size: 15px; }
.hero .top-num {
  font-size: 56px; font-weight: 800;
  background: linear-gradient(135deg, var(--accent-1) 0%, var(--accent-2) 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1;
}
.hero .top-label { color: var(--text-dim); font-size: 12px; text-align: center; margin-top: 4px; }

/* KPI Row */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.kpi {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 12px;
  padding: 20px 24px;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}
.kpi-label { color: var(--text-dim); font-size: 12px; margin-bottom: 8px; }
.kpi-num {
  font-size: 32px; font-weight: 700;
  background: linear-gradient(135deg, var(--accent-1), var(--accent-2));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 6px;
}
.kpi-source { color: var(--text-dim); font-size: 12px; }
.kpi-source b { color: var(--text); font-weight: 600; }

/* Two-col layout */
.two-col {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
.panel {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 12px;
  padding: 24px;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}
.panel-h {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 18px;
}
.panel-h h2 { font-size: 16px; font-weight: 600; }
.panel-h .hint { color: var(--text-dim); font-size: 12px; }

/* Bar chart (Top 8) */
.bars { display: flex; flex-direction: column; gap: 10px; }
.bar-row { display: grid; grid-template-columns: minmax(0, 1fr) 3fr 60px; gap: 10px; align-items: center; }
.bar-title { color: var(--text); font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bar-track { background: rgba(255, 255, 255, 0.05); height: 14px; border-radius: 4px; overflow: hidden; }
.bar-fill {
  height: 100%; border-radius: 4px;
  background: linear-gradient(90deg, var(--bar-1) 0%, var(--bar-2) 60%, var(--bar-3) 100%);
}
.bar-num { text-align: right; color: var(--text-dim); font-size: 12px; font-variant-numeric: tabular-nums; }

/* Donut */
.donut-wrap { display: flex; align-items: center; gap: 24px; justify-content: center; padding: 20px 0; }
.donut {
  width: 140px; height: 140px; border-radius: 50%;
  background: conic-gradient(var(--accent-1) 0% 40%, var(--accent-2) 40% 100%);
  position: relative;
  display: flex; align-items: center; justify-content: center;
}
.donut::before {
  content: ""; position: absolute; inset: 22px;
  background: var(--bg-1); border-radius: 50%;
}
.donut-center { position: relative; text-align: center; z-index: 1; }
.donut-num { font-size: 22px; font-weight: 700; }
.donut-label { color: var(--text-dim); font-size: 11px; }
.donut-legend { display: flex; flex-direction: column; gap: 8px; }
.donut-legend-item { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.dot { width: 10px; height: 10px; border-radius: 50%; }

/* Hero note */
.hero-note {
  background: linear-gradient(135deg, rgba(110, 231, 183, 0.06), rgba(192, 132, 252, 0.04));
  border: 1px solid rgba(110, 231, 183, 0.2);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 16px;
}
.hero-note-tag { color: var(--accent-1); font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; font-weight: 600; margin-bottom: 4px; }
.hero-note-title { font-size: 18px; font-weight: 600; margin-bottom: 6px; }
.hero-note-meta { color: var(--text-dim); font-size: 12px; }

/* Author cards */
.authors-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.author-card {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 12px;
  padding: 18px 20px;
}
.author-head { display: flex; gap: 12px; margin-bottom: 12px; }
.author-avatar {
  width: 44px; height: 44px; border-radius: 50%;
  background: linear-gradient(135deg, var(--accent-1), var(--accent-3));
  display: flex; align-items: center; justify-content: center;
  color: var(--bg-1); font-weight: 700; font-size: 16px;
  flex-shrink: 0;
}
.author-name { font-weight: 600; margin-bottom: 2px; }
.author-id { color: var(--text-dim); font-size: 11px; }
.author-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 12px; }
.author-stat { background: rgba(255, 255, 255, 0.04); border-radius: 6px; padding: 8px 10px; }
.author-stat-num { font-size: 14px; font-weight: 600; }
.author-stat-label { color: var(--text-dim); font-size: 10px; margin-top: 2px; }
.author-samples { color: var(--text-dim); font-size: 11px; margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--card-border); }
.author-samples li { list-style: none; padding: 3px 0; }

/* Pain grid */
.pain-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.pain-card {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid var(--card-border);
  border-radius: 8px;
  padding: 12px 14px;
}
.pain-text { font-size: 13px; margin-bottom: 6px; line-height: 1.45; }
.pain-source { color: var(--text-dim); font-size: 11px; display: flex; align-items: center; gap: 6px; }
.pain-source::before { content: "来源:"; color: var(--accent-1); }

/* Reverse prompt section */
.reverse-block {
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 12px;
}
.reverse-block h3 {
  font-size: 14px; font-weight: 600;
  color: var(--accent-1);
  margin-bottom: 10px;
  display: flex; align-items: center; gap: 8px;
}
.reverse-block h3::before {
  content: ""; display: inline-block;
  width: 4px; height: 14px; border-radius: 2px;
  background: linear-gradient(180deg, var(--accent-1), var(--accent-2));
}
.reverse-block .meta-line {
  color: var(--text-dim); font-size: 12px; margin-bottom: 12px;
}
.reverse-block ul { list-style: none; }
.reverse-block li {
  padding: 6px 0;
  border-bottom: 1px dashed rgba(255, 255, 255, 0.05);
  font-size: 13px;
}
.reverse-block li:last-child { border-bottom: none; }
.reverse-block li b { color: var(--accent-2); margin-right: 8px; }

/* Footer */
.foot {
  text-align: center; color: var(--text-dim); font-size: 12px;
  padding: 24px 0; margin-top: 16px;
}
.foot a { color: var(--accent-1); text-decoration: none; }
"""

HTML_TPL = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AI 副业 · 小红书爆款情报报告</title>
<style>{css}</style>
</head>
<body>
<div class="watermark"></div>
<div class="wrap">
  <div class="hero">
    <div>
      <div class="hero-tag">XHS CONTENT INTELLIGENCE</div>
      <h1>{keyword} · 小红书内容情报报告</h1>
      <div class="sub">爆款样本、互动结构、评论需求和对标账号的可视化情报面板</div>
    </div>
    <div>
      <div class="top-num">{top_n}</div>
      <div class="top-label">Top Samples</div>
    </div>
  </div>

  <div class="kpi-row">
    {kpi_cards}
  </div>

  <div class="two-col">
    <div class="panel">
      <div class="panel-h">
        <h2>互动热度柱状图</h2>
        <span class="hint">Top 8</span>
      </div>
      <div class="bars">{bars}</div>
    </div>
    <div class="panel">
      <div class="panel-h">
        <h2>内容类型占比</h2>
        <span class="hint">视频 vs 图文</span>
      </div>
      <div class="donut-wrap">
        <div class="donut"><div class="donut-center"><div class="donut-num">{total_notes}</div><div class="donut-label">总笔记</div></div></div>
        <div class="donut-legend">
          <div class="donut-legend-item"><span class="dot" style="background:var(--accent-1)"></span> 视频 {n_video}</div>
          <div class="donut-legend-item"><span class="dot" style="background:var(--accent-2)"></span> 图文 {n_image}</div>
        </div>
      </div>
    </div>
  </div>

  <div class="hero-note">
    <div class="hero-note-tag">最高热度样本 · Hero Note</div>
    <div class="hero-note-title">{hero_title}</div>
    <div class="hero-note-meta">{hero_meta}</div>
  </div>

  <div class="panel">
    <div class="panel-h">
      <h2>对标账号渲染</h2>
      <span class="hint">用户信息 + 用户笔记</span>
    </div>
    <div class="authors-grid">{author_cards}</div>
  </div>

  <div class="panel" style="margin-top:16px;">
    <div class="panel-h">
      <h2>评论需求摘录</h2>
      <span class="hint">评论 + 来源笔记</span>
    </div>
    <div class="pain-grid">{pain_cards}</div>
  </div>

  <div class="panel" style="margin-top:16px;">
    <div class="panel-h">
      <h2>5 段式仿写 prompt (核心结论)</h2>
      <span class="hint">Skill 4 v0.5 reverse_prompt</span>
    </div>
    {reverse_blocks}
  </div>

  <div class="foot">
    Generated by Skill 1.5 + Skill 4 v0.5 · 2026-06-09 · 数据来源: xhs-trending-scanner → viral-analyzer → reverse-prompt
  </div>
</div>
</body>
</html>
"""


def render_kpi(label: str, num: str, source: str) -> str:
    return (
        f'<div class="kpi">'
        f'<div class="kpi-label">{esc(label)}</div>'
        f'<div class="kpi-num">{esc(num)}</div>'
        f'<div class="kpi-source">Top 来源: <b>{esc(source)}</b></div>'
        f'</div>'
    )


def render_bar(title: str, value: int, max_value: int) -> str:
    pct = (value / max_value * 100) if max_value else 0
    return (
        f'<div class="bar-row">'
        f'<div class="bar-title">{esc(title)}</div>'
        f'<div class="bar-track"><div class="bar-fill" style="width:{pct:.1f}%"></div></div>'
        f'<div class="bar-num">{fmt(value)}</div>'
        f'</div>'
    )


def render_author_card(meta: dict) -> str:
    name = meta.get("author", "?")
    initials = name[:1] if name else "?"
    likes = meta.get("likes", 0) or 0
    collects = meta.get("collects", 0) or 0
    comments = meta.get("comments", 0) or 0
    title = meta.get("title", "")
    publish = meta.get("publish_date", "")
    return f"""
    <div class="author-card">
      <div class="author-head">
        <div class="author-avatar">{esc(initials)}</div>
        <div>
          <div class="author-name">{esc(name)}</div>
          <div class="author-id">粉丝 ? · 发布 {esc(str(publish))}</div>
        </div>
      </div>
      <div class="author-stats">
        <div class="author-stat"><div class="author-stat-num">{fmt(likes)}</div><div class="author-stat-label">点赞</div></div>
        <div class="author-stat"><div class="author-stat-num">{fmt(collects)}</div><div class="author-stat-label">收藏</div></div>
        <div class="author-stat"><div class="author-stat-num">{fmt(comments)}</div><div class="author-stat-label">评论</div></div>
      </div>
      <ul class="author-samples">
        <li>📌 {esc(title[:60])}</li>
      </ul>
    </div>
    """


def render_pain(text: str, likes: int, source: str) -> str:
    return (
        f'<div class="pain-card">'
        f'<div class="pain-text">{esc(text[:120])}</div>'
        f'<div class="pain-source">{likes} 赞 · {esc(source[:50])}</div>'
        f'</div>'
    )


def render_reverse_block(meta: dict, rev: dict) -> str:
    title = meta.get("title", "?")[:60]
    auth = meta.get("author", "?")
    likes = fmt(meta.get("likes", 0) or 0)
    sections = rev.get("sections", {})
    items_html = ""
    for key, sec in sections.items():
        items_html += f"<li><b>{esc(sec.get('label', key))}</b></li>"
        for label, value in sec.get("items", []):
            val_short = (str(value) or "").replace("\n", " ")[:80]
            items_html += f"<li>&nbsp;&nbsp;· {esc(label)}: {esc(val_short)}</li>"
    return f"""
    <div class="reverse-block">
      <h3>{esc(auth)} · {esc(title)}</h3>
      <div class="meta-line">点赞 {likes} · 已生成 5 段式 prompt (output/skill-4-reverse-prompts-v0.5/)</div>
      <ul>{items_html}</ul>
    </div>
    """


def main() -> int:
    print("=== 生成 HTML 情报报告 ===\n")
    data = collect()
    notes = data["notes"]
    pains = data["pains"]
    viral_all = data["viral_all"]

    if not notes:
        print("ERROR: 没有可用的拆解数据, 跑 batch-analyze.py")
        return 1

    # KPI 数字 (viral_all 元素是 {"metrics": {...}, "author": {...}}, 没 meta 字段)
    def _m(n, k):
        return (n.get("metrics", {}).get(k, 0) or 0) if isinstance(n, dict) else 0
    total_likes = sum(_m(n, "likes") for n in viral_all) if viral_all else 0
    total_collects = sum(_m(n, "collects") for n in viral_all) if viral_all else 0
    total_comments = sum(_m(n, "comments") for n in viral_all) if viral_all else 0
    top_sample = notes[0]  # 排序过, likes 最高
    top_meta = top_sample["meta"]
    top_kw = "AI 副业"

    kpi_cards = "\n".join([
        render_kpi("总互动热度", fmt(total_likes + total_collects + total_comments), top_meta.get("title", "?")[:30]),
        render_kpi("点赞", fmt(total_likes), top_meta.get("title", "?")[:30]),
        render_kpi("收藏", fmt(total_collects), top_meta.get("title", "?")[:30]),
        render_kpi("评论", fmt(total_comments), top_meta.get("title", "?")[:30]),
    ])

    # Top 8 柱状图 (按 likes 排序 viral)
    top8 = sorted(viral_all, key=lambda n: n.get("metrics", {}).get("likes", 0) or 0, reverse=True)[:8]
    max_likes = max((n.get("metrics", {}).get("likes", 0) or 0) for n in top8) if top8 else 1
    bars = "\n".join(render_bar(n.get("title", "?"), n.get("metrics", {}).get("likes", 0) or 0, max_likes) for n in top8)

    # 视频 vs 图文 (从 imageList 数推断 — 我们没存 type, 用启发式)
    # 简化: 都按"图文"算 (xhs 大部分是图文)
    n_image = len(viral_all)
    n_video = 0
    total_notes = n_image + n_video

    # Hero note
    hero_title = top_meta.get("title", "?")
    hero_meta = f"作者: {top_meta.get('author', '?')} · 点赞 {fmt(top_meta.get('likes', 0))} · 收藏 {fmt(top_meta.get('collects', 0))} · 评论 {fmt(top_meta.get('comments', 0))} · 发布 {top_meta.get('publish_date', '?')}"

    # 对标账号 (5 个)
    author_cards = "\n".join(render_author_card(n["meta"]) for n in notes)

    # 评论需求摘录 (12 条)
    top_pains = pains[:12]
    pain_cards = "\n".join(
        render_pain(
            p.get("text") or p.get("content") or "",
            p.get("likes", 0) or 0,
            (p.get("note_title") or p.get("source") or p.get("from") or "?")
        )
        for p in top_pains
    )

    # 5 段 prompt 块
    reverse_blocks = "\n".join(render_reverse_block(n["meta"], n.get("reverse") or {}) for n in notes)

    html_doc = HTML_TPL.format(
        css=CSS,
        keyword=esc(top_kw),
        top_n=len(notes),
        kpi_cards=kpi_cards,
        bars=bars,
        total_notes=total_notes,
        n_image=n_image,
        n_video=n_video,
        hero_title=esc(hero_title),
        hero_meta=esc(hero_meta),
        author_cards=author_cards,
        pain_cards=pain_cards,
        reverse_blocks=reverse_blocks,
    )

    OUTPUT_HTML.write_text(html_doc, encoding="utf-8")
    print(f"\n[OK] HTML 报告: {OUTPUT_HTML}")
    print(f"  ({len(html_doc) // 1024} KB)")
    print(f"  打开: start \"{OUTPUT_HTML}\"")
    return 0


if __name__ == "__main__":
    sys.exit(main())
