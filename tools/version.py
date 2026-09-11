#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打印 cts/__init__.py 里的 __version__（不带 v 前缀）。

CI 用它推导当前该发布到哪个 Release 标签，避免在 YAML 里写内联 Python
被 shell 的引号规则反复坑。

用法：
    python tools/version.py        # -> 0.10
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from _utf8 import force_utf8

force_utf8()

INIT = Path(__file__).resolve().parent.parent / "cts" / "__init__.py"
PATTERN = re.compile(r"""__version__\s*=\s*["']([^"']+)["']""")


def main() -> int:
    try:
        source = INIT.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"无法读取 {INIT}: {exc}", file=sys.stderr)
        return 1
    match = PATTERN.search(source)
    if not match:
        print(f"在 {INIT} 里找不到 __version__", file=sys.stderr)
        return 1
    print(match.group(1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
