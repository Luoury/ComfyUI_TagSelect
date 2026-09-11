# -*- coding: utf-8 -*-
"""让命令行输出在 Windows 上也能正常打印中文。

Windows 的 stdout 默认是 cp1252 / gbk，直接 print 中文会抛 UnicodeEncodeError。
Python 3.7+ 提供 sys.stdout.reconfigure，这里统一处理一下。
"""

from __future__ import annotations

import sys


def force_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError, OSError):
            pass
