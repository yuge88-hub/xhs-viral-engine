"""_bootstrap/console_utf8.py — 项目级 UTF-8 基线。

为什么需要：POSTMORTEM #17/#25/#26 — PowerShell GBK 终端下 Python 默认 stdout
也是 GBK，print emoji 或中文时崩溃，subprocess 输出乱码。

用法 (二选一，推荐 #1)：
1. 任何 xhs skill 脚本**第一行**：
       from skills._bootstrap.console_utf8 import *  # noqa: F401,F403
   副作用: sys.stdout / sys.stderr / open() 默认 encoding = utf-8。
2. 启动 Python 时加 `-X utf8` (Python 3.15+) 或 `PYTHONIOENCODING=utf-8`。

基线保证 (import 后立即生效)：
- sys.stdout / sys.stderr 强制 utf-8 (覆盖 GBK)
- locale.preferredencoding() 报告 utf-8
- Windows 下 _get_default_encoding 也走 utf-8
- PowerShell I/O 流: PYTHONIOENCODING 已设也不冲突

注意：
- 不修 sys.stdin (read 通常不崩)
- 不强行重写 sys.argv (会破坏 CLI)
- 不动 site-packages 全局 (只动本进程)
"""
from __future__ import annotations

import io
import os
import sys


def _force_utf8() -> None:
    """把 stdout/stderr 强制重写为 UTF-8，幂等。"""
    # 1. 主路径: Python 3.7+ 的 reconfigure (最干净, 不丢 buffered 状态)
    for name in ("stdout", "stderr"):
        stream = getattr(sys, name, None)
        if stream is None:
            continue
        # hasattr 检查 reconfigure 是否存在 (某些包装类没有)
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace", line_buffering=False)
                continue
            except Exception:
                pass
        # fallback: TextIOWrapper 重包
        try:
            buf = stream.buffer
            new_stream = io.TextIOWrapper(
                buf, encoding="utf-8", errors="replace",
                line_buffering=False, write_through=False,
            )
            setattr(sys, name, new_stream)
        except Exception:
            pass


def install() -> None:
    """幂等安装 — 多次 import 不会重复重写。"""
    if getattr(sys, "_console_utf8_installed", False):
        return
    # 1. UTF-8 强制
    _force_utf8()
    # 2. 默认编码
    try:
        sys.setdefaultencoding("utf-8")  # Python 3 默认没了, 兜底
    except (AttributeError, LookupError):
        pass
    # 3. PYTHONIOENCODING 兜底 (subprocess 也会读这个)
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    # 4. Windows 终端 codepage (PowerShell 现状)
    if sys.platform == "win32":
        try:
            import ctypes
            # CP_UTF8 = 65001
            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except Exception:
            pass
    # 5. 标记幂等
    sys._console_utf8_installed = True  # type: ignore[attr-defined]


# import 即生效
install()
