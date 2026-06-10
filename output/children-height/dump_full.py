import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
import json
d = json.load(open("output/children-height/scanner-full.json", encoding="utf-8"))
print(f"viral_count: {d['viral_count']}")
print(f"unique_authors: {d['unique_authors']}")
print(f"fetched_fans: {d['fetched_fans']}")
print()
print("=== 13 条素人爆款 (Top by viral_score) ===")
for r in d["results"][:13]:
    f = r["author"]["fans"]
    nick = r["author"]["nickname"]
    title = r["title"][:40]
    print(f"viral={r['viral_score']:>8.2f} | fans={f:>6,} | {nick:20s} | {title}")
