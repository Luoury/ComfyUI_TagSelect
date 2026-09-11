#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""产物冒烟测试：启动打包好的可执行文件，确认它能正常跑起来而不是秒退。

用法（在仓库根目录）：
    python tools/smoke_test.py dist/ComfyUI_TagSelect.exe
    python tools/smoke_test.py dist/ComfyUI_TagSelect          # Linux / macOS

原理：用离屏 Qt 平台启动，等若干秒后检查进程是否还活着。
秒退通常意味着缺数据文件、缺 Qt 插件或依赖没打全。
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


from _utf8 import force_utf8

force_utf8()

ROOT = Path(__file__).resolve().parent.parent
WAIT_SECONDS = float(os.environ.get("SMOKE_WAIT", "14"))


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if target is None:
        for cand in ("dist/ComfyUI_TagSelect.exe", "dist/ComfyUI_TagSelect",
                     "dist/ComfyUI_TagSelect/ComfyUI_TagSelect.exe",
                     "dist/ComfyUI_TagSelect/ComfyUI_TagSelect"):
            if (ROOT / cand).exists():
                target = ROOT / cand
                break
    if target is None or not target.exists():
        print(f"[失败] 找不到可执行文件：{target}")
        return 1
    target = target.resolve()

    size_mb = target.stat().st_size / 1024 / 1024
    min_mb = float(os.environ.get("SMOKE_MIN_MB", "5"))
    print(f"目标      : {target}")
    print(f"体积      : {size_mb:.1f} MB")
    if size_mb < min_mb:
        print(f"[失败] 体积小于 {min_mb:.1f} MB，几乎肯定没把依赖打进去")
        return 1

    data_dir = Path(tempfile.mkdtemp(prefix="tagselect-smoke-"))
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["TAGSELECT_DATA_DIR"] = str(data_dir)
    env.pop("TAGSELECT_ASSETS_DIR", None)  # 强制使用打包内的资源

    print(f"环境      : QT_QPA_PLATFORM=offscreen, TAGSELECT_DATA_DIR={data_dir}")
    print(f"等待 {WAIT_SECONDS:.0f} 秒，检查进程是否存活 ...")

    proc = subprocess.Popen([str(target)], env=env, cwd=str(target.parent),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")
    deadline = time.time() + WAIT_SECONDS
    while time.time() < deadline:
        if proc.poll() is not None:
            break
        time.sleep(0.25)

    alive = proc.poll() is None
    output = ""
    if alive:
        proc.terminate()
        try:
            output = proc.communicate(timeout=10)[0] or ""
        except subprocess.TimeoutExpired:
            proc.kill()
            output = proc.communicate()[0] or ""
    else:
        output = proc.communicate()[0] or ""

    if output.strip():
        print("--- 进程输出 ---")
        print("\n".join(output.strip().splitlines()[:25]))
        print("----------------")

    if alive:
        print(f"[通过] 进程存活超过 {WAIT_SECONDS:.0f} 秒，产物可用 ✓")
        return 0

    print(f"[失败] 进程提前退出，返回码 {proc.returncode}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
