#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""产物冒烟测试：启动打包好的可执行文件，确认它能正常跑起来而不是秒退。

用法（在仓库根目录）：
    python tools/smoke_test.py dist/ComfyUI_TagSelect.exe
    python tools/smoke_test.py dist/ComfyUI_TagSelect          # Linux / macOS

原理：用离屏 Qt 平台启动，等若干秒后检查进程是否还活着。
秒退通常意味着缺数据文件、缺 Qt 插件或依赖没打全。

实现上刻意做了三件防挂死的事：
  1. 子进程输出重定向到**临时文件**而不是管道 —— PyInstaller 单文件模式会派生子
     进程，管道句柄被子进程继承后，父进程即使被杀掉管道也不会 EOF，读取会永久
     阻塞（这个坑真的踩到了，第一次 CI 就卡在这）。
  2. 结束进程时连同整个进程树一起杀（Windows 用 taskkill /T，POSIX 用 killpg）。
  3. 任何等待都带超时，超时后不再做无超时的阻塞调用。
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from _utf8 import force_utf8

force_utf8()

ROOT = Path(__file__).resolve().parent.parent
WAIT_SECONDS = float(os.environ.get("SMOKE_WAIT", "14"))


def _kill_tree(proc: subprocess.Popen) -> None:
    """连同子进程一起结束（PyInstaller 单文件会派生子进程）。"""
    if proc.poll() is not None:
        return
    try:
        if sys.platform.startswith("win"):
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, timeout=20)
        else:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    try:
        proc.wait(timeout=15)
    except Exception:
        pass


def _find_target() -> Path | None:
    for cand in ("dist/ComfyUI_TagSelect.exe", "dist/ComfyUI_TagSelect",
                 "dist/ComfyUI_TagSelect/ComfyUI_TagSelect.exe",
                 "dist/ComfyUI_TagSelect/ComfyUI_TagSelect"):
        p = ROOT / cand
        if p.exists():
            return p
    return None


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    target = target or _find_target()
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

    workdir = Path(tempfile.mkdtemp(prefix="tagselect-smoke-"))
    logfile = workdir / "stdout.log"
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["TAGSELECT_DATA_DIR"] = str(workdir / "userdata")
    env.pop("TAGSELECT_ASSETS_DIR", None)  # 强制使用打包内的资源

    print("环境      : QT_QPA_PLATFORM=offscreen")
    print(f"等待 {WAIT_SECONDS:.0f} 秒，检查进程是否存活 ...")

    kwargs: dict = {}
    if not sys.platform.startswith("win"):
        kwargs["start_new_session"] = True  # 便于整组 kill

    with open(logfile, "wb") as sink:
        proc = subprocess.Popen([str(target)], env=env, cwd=str(target.parent),
                                stdout=sink, stderr=subprocess.STDOUT, **kwargs)
        deadline = time.time() + WAIT_SECONDS
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            time.sleep(0.25)
        alive = proc.poll() is None
        returncode = proc.returncode
        _kill_tree(proc)

    output = ""
    try:
        output = logfile.read_text(encoding="utf-8", errors="replace")
    except OSError:
        pass

    if output.strip():
        print("--- 进程输出 ---")
        print("\n".join(output.strip().splitlines()[:25]))
        print("----------------")

    if alive:
        print(f"[通过] 进程存活超过 {WAIT_SECONDS:.0f} 秒，产物可用 ✓")
        return 0

    print(f"[失败] 进程提前退出，返回码 {returncode}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
