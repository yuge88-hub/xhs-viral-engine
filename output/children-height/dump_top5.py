import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
import json
d = json.load(open("output/children-height/scanner-full.json", encoding="utf-8"))
# 按 viral_score 排序
results = sorted(d["results"], key=lambda r: r["viral_score"], reverse=True)
print("=== Top 5 素人爆款 (按 viral_score) ===")
for r in results[:5]:
    print(f"viral={r['viral_score']:.2f} | fans={r['author']['fans']:>4} | {r['note_id']} | {r['xsec_token']} | {r['title'][:30]}")
