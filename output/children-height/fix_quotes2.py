import re
p = "output/children-height/write_intel_report_v2.py"
data = open(p, "r", encoding="utf-8").read()
# 找出含双引号 " 嵌在中文里的行
for i, line in enumerate(data.split("\n"), 1):
    if '""' in line or '"' in line:
        # 跳过纯注释 / import / 字符串定义
        if line.strip().startswith("#") or line.strip().startswith('"""') or line.strip().startswith("'''"):
            continue
        # 找内嵌的英文双引号 (在中文上下文里, 前后都不是字符串边界)
        # 用 heuristic: 看 " 前后字符是不是 ASCII (字符串边界)/ 非 ASCII (嵌在中文里)
        for j, ch in enumerate(line):
            if ch == '"':
                prev_ch = line[j-1] if j > 0 else ""
                next_ch = line[j+1] if j+1 < len(line) else ""
                # 如果前一个或后一个是中文/中文标点, 那这就是中文里的"嵌双引号" → 改「」/「」
                if '一' <= prev_ch <= '鿿' or '一' <= next_ch <= '鿿' or prev_ch in '，。；：、！？）】》':
                    print(f"line {i} pos {j}: {line[max(0,j-10):j+10]!r}")
                    break
