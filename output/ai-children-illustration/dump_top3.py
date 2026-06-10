import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
import json
data = json.load(open("output/ai-children-illustration/scored.json", encoding="utf-8"))
for r in data["results"][:3]:
    q = r["quality"]
    print(f"{q['score']} | {r['note_id']} | {r['xsec_token']} | {r['title'][:40]}")
