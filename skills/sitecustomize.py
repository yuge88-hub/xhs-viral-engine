r"""sitecustomize.py — Python 启动时**自动**加载的入口。

为什么需要：subprocess.run 启子 Python 时，主进程的 PYTHONIOENCODING 不一定
传到子进程；PowerShell 启 Python 时 codepage 仍是 GBK。放 sitecustomize 让任何
子 Python 进程一启动就 UTF-8。

部署方式 (二选一)：
A. **推荐 — 通过 PYTHONPATH**：
       setx PYTHONPATH "C:\Users\张哥\Downloads\web-clipper-master\skills;%PYTHONPATH%"
   之后任何 `python` 命令都会自动 import 本文件。
B. **全局 site-packages**：
       cp skills/sitecustomize.py "C:\Users\张哥\AppData\Local\Programs\Python\Python314\Lib\site-packages\"
   影响所有项目, 不推荐。

当前激活方式：直接 install (副作用最小)。
"""
try:
    from _bootstrap.console_utf8 import install as _install_console_utf8
except ImportError:
    # 没在 PYTHONPATH 找到 _bootstrap, 静默跳过 (基线由 import 触发)
    pass
else:
    _install_console_utf8()
