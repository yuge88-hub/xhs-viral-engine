import re
p = "output/children-height/write_intel_report_v2.py"
data = open(p, "r", encoding="utf-8").read()
# 把所有中文双引号 「 」 全替换为 「」
data2 = data.replace("“", "「").replace("”", "」")
# 同时如果有「 单边也转 (保险)
open(p, "w", encoding="utf-8").write(data2)
print("replaced")
