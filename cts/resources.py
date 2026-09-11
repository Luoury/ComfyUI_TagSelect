# -*- coding: utf-8 -*-
"""资源路径与用户数据目录解析（兼容 PyInstaller 打包后的运行环境）。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "ComfyUI_TagSelect"


def _base_dir() -> Path:
    """只读资源根目录。

    - 开发环境：仓库根目录（本文件的上一级）
    - PyInstaller 单文件模式：sys._MEIPASS（临时解包目录）
    - PyInstaller 单目录模式：可执行文件所在目录
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def app_dir() -> Path:
    """程序所在目录（用于 portable.txt / userdata，单文件模式下不是临时目录）。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _base_dir()
ASSETS_DIR = Path(os.environ["TAGSELECT_ASSETS_DIR"]) if os.environ.get("TAGSELECT_ASSETS_DIR") else BASE_DIR / "assets"
DATA_DIR = ASSETS_DIR / "data"
WALLPAPER_DIR = ASSETS_DIR / "wallpapers"
ICON_DIR = ASSETS_DIR / "icons"


def user_data_dir() -> Path:
    """可写的用户数据目录（设置 / 自定义标签 / 自定义预设）。

    支持"便携模式"：若程序目录下存在 portable.txt，则数据写在程序目录的 userdata/ 里。
    """
    if os.environ.get("TAGSELECT_DATA_DIR"):
        path = Path(os.environ["TAGSELECT_DATA_DIR"])
    elif (app_dir() / "portable.txt").exists():
        path = app_dir() / "userdata"
    elif sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = Path(base) / APP_NAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        path = Path(base) / APP_NAME
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        path = Path.home() / ("." + APP_NAME.lower())
        path.mkdir(parents=True, exist_ok=True)
    return path


def asset(*parts: str) -> Path:
    return ASSETS_DIR.joinpath(*parts)


def wallpaper_files() -> list[tuple[str, Path]]:
    """返回 [(显示名, 路径), ...]，按固定顺序（默认壁纸排最前）。"""
    order = [
        ("miku_meteor", "星空流星 · 默认"),
        ("miku_starry", "闪耀舞台"),
        ("miku_snow_castle", "雪之城"),
        ("miku_birthday", "Happy Birthday"),
        ("miku_sunflower", "向日葵"),
    ]
    out: list[tuple[str, Path]] = []
    for stem, label in order:
        path = WALLPAPER_DIR / f"{stem}.jpg"
        if path.exists():
            out.append((label, path))
    # 兜底：目录里其它图片也列出来
    if WALLPAPER_DIR.exists():
        known = {p for _, p in out}
        for p in sorted(WALLPAPER_DIR.glob("*")):
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"} and p not in known:
                out.append((p.stem, p))
    return out
