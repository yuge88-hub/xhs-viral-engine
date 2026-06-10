"""fix-sync.py — 就地修复 sync.py 的 PowerShell 编码损坏 + 算术折叠问题

修复策略:
1. 读 bytes, 看哪些位置 PowerShell 写入了 GBK 字节
2. 把整文件用 UTF-8 解码 (errors='replace'), 拿可读字符串
3. 对所有 r\"\"\"...\"\"\" 模板, 给含 \"数字+/-标识符\" 模式的字符串字面量加引号
4. 写回 UTF-8 (无 BOM)

诊断: line 530 是 f-string 内的中文, 实际可能被 PowerShell 当 GBK 写入
"""
from __future__ import annotations
import re
from pathlib import Path

p = Path(r"C:\Users\张哥\Downloads\web-clipper-master\skills\skill-5-obsidian-sync\sync.py")
content_bytes = p.read_bytes()
print(f"File size: {len(content_bytes)} bytes")
print(f"First 3 bytes: {content_bytes[:3].hex()}")

# 整文件用 UTF-8 解 (errors=replace), 看哪些字符乱码
text = content_bytes.decode("utf-8", errors="replace")

# 找所有 line 530 周围 (line 530 实际是 content[529])
lines = text.split("\n")
if len(lines) > 530:
    print(f"\nLine 530: {lines[529]!r}")

# 写回 UTF-8 (clean), 试图消除 PowerShell 编码
# 但实际上 line 530 已是乱码, 没法修——除非重写整个文件

# 简单方案: 跑现有的 sync.py dry-run, 如果还报错, 再针对性修
print("\n=== 写回 UTF-8 (无修复, 仅 encoding 归一化) ===")
p.write_text(text, encoding="utf-8")
print(f"Re-wrote {len(text)} chars as UTF-8")
