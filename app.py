#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ComfyUI_TagSelect —— 简约的 AI 生图 Tag 选择器（初音未来主题）。

用法：
    python app.py

打包成 Windows 单文件 exe：
    双击 build_exe.bat （或见 README.md）
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# 让脚本可以直接运行（无需安装）
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# 冻结后不要重复添加；同时保证工作目录稳定
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

from cts.app import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
