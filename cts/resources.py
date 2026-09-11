# -*- coding: utf-8 -*-
"""资源路径与用户数据目录解析（兼容 PyInstaller 打包后的运行环境）。

这里有个容易踩的坑：PyInstaller **单文件**模式运行时，资源根目录是
``sys._MEIPASS``（一个临时解包目录），每次启动重新解包、退出即删。
所以「用户可以放自己图片的目录」绝对不能放在那底下 —— 必须放在
持久可写的用户数据目录里（``user_wallpaper_dir()``）。
"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "ComfyUI_TagSelect"

WALLPAPER_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

# 打包自带壁纸的固定展示顺序
_BUILTIN_ORDER = [
    ("miku_meteor", "星空流星 · 默认"),
    ("miku_starry", "闪耀舞台"),
    ("miku_snow_castle", "雪之城"),
    ("miku_birthday", "Happy Birthday"),
    ("miku_sunflower", "向日葵"),
]

KEY_DEFAULT = ""          # 空 key = 程序生成的默认背景
_PREFIX_USER = "user:"
_PREFIX_BUILTIN = "builtin:"


def _base_dir() -> Path:
    """只读资源根目录。

    - 开发环境：仓库根目录（本文件的上一级）
    - PyInstaller 单文件模式：sys._MEIPASS（临时解包目录，**只读且易失**）
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
ASSETS_DIR = (Path(os.environ["TAGSELECT_ASSETS_DIR"])
              if os.environ.get("TAGSELECT_ASSETS_DIR") else BASE_DIR / "assets")
DATA_DIR = ASSETS_DIR / "data"
ICON_DIR = ASSETS_DIR / "icons"
MIKU_DIR = ASSETS_DIR / "miku"
# 兼容旧名字：打包自带的壁纸目录（只读）
WALLPAPER_DIR = ASSETS_DIR / "wallpapers"

# MIKU 立绘（已做成圆角贴纸）
MIKU_SPRITES = {
    "idle": "miku_idle.png",   # 初始状态
    "leek": "miku_leek.png",   # 咬着大葱
    "yell": "miku_yell.png",   # 眯眼大叫
}
DEFAULT_WALLPAPER_KEY = "builtin:miku_meteor.jpg"


def miku_sprite(state: str) -> Path | None:
    path = MIKU_DIR / MIKU_SPRITES.get(state, MIKU_SPRITES["idle"])
    return path if path.exists() else None


def user_data_dir() -> Path:
    """可写的用户数据目录（设置 / 自定义标签 / 自定义预设 / 用户壁纸）。

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


def bundled_wallpaper_dir() -> Path:
    """打包自带的壁纸目录（只读，单文件模式下位于临时解包目录）。"""
    return WALLPAPER_DIR


def user_wallpaper_dir() -> Path:
    """用户自己的壁纸目录 —— **持久可写**，不会因重启 exe 而丢失。

    单文件模式下这是 ``%APPDATA%\\ComfyUI_TagSelect\\wallpapers``（便携模式则
    在程序目录的 ``userdata/wallpapers``）。
    """
    path = user_data_dir() / "wallpapers"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return path


def asset(*parts: str) -> Path:
    return ASSETS_DIR.joinpath(*parts)


@dataclass(frozen=True)
class Wallpaper:
    """一张可选壁纸。

    key 是**稳定标识**（而不是绝对路径），设置里存的就是它 ——
    这样单文件 exe 换次启动、临时目录变了也不会失效。
    """

    key: str
    label: str
    path: Path
    user: bool = False


def _scan(directory: Path, prefix: str, user: bool) -> list[Wallpaper]:
    out: list[Wallpaper] = []
    if not directory.exists():
        return out
    for p in sorted(directory.iterdir(), key=lambda x: x.name.lower()):
        if not p.is_file() or p.suffix.lower() not in WALLPAPER_EXTS:
            continue
        out.append(Wallpaper(f"{prefix}{p.name}", p.stem, p, user=user))
    return out


def wallpaper_files() -> list[Wallpaper]:
    """返回所有可选壁纸：打包自带的在前，用户自己加的在后。"""
    out: list[Wallpaper] = []

    bundled = bundled_wallpaper_dir()
    if bundled.exists():
        known: set[Path] = set()
        for stem, label in _BUILTIN_ORDER:
            for ext in WALLPAPER_EXTS:
                path = bundled / f"{stem}{ext}"
                if path.exists():
                    out.append(Wallpaper(f"{_PREFIX_BUILTIN}{path.name}", label, path))
                    known.add(path)
                    break
        for item in _scan(bundled, _PREFIX_BUILTIN, user=False):
            if item.path not in known:
                out.append(item)

    out.extend(_scan(user_wallpaper_dir(), _PREFIX_USER, user=True))
    return out


def resolve_wallpaper(key: str) -> Path | None:
    """把设置里的 key 解析成实际路径；解析不到返回 None。"""
    key = (key or "").strip()
    if not key:
        return None

    if key.startswith(_PREFIX_USER):
        path = user_wallpaper_dir() / key[len(_PREFIX_USER):]
        return path if path.exists() else None

    if key.startswith(_PREFIX_BUILTIN):
        path = bundled_wallpaper_dir() / key[len(_PREFIX_BUILTIN):]
        return path if path.exists() else None

    # 兼容旧版本存的绝对路径
    legacy = Path(key)
    return legacy if legacy.exists() else None


def default_wallpaper() -> Wallpaper | None:
    """没有显式选择时用哪张：优先打包自带的第一张，否则用户目录的第一张。"""
    files = wallpaper_files()
    for item in files:
        if not item.user:
            return item
    return files[0] if files else None


def import_wallpaper(source: Path) -> Wallpaper | None:
    """把一张图片复制进用户壁纸目录，返回对应的 Wallpaper。"""
    source = Path(source)
    if not source.is_file() or source.suffix.lower() not in WALLPAPER_EXTS:
        return None
    target_dir = user_wallpaper_dir()
    target = target_dir / source.name
    stem, suffix, n = source.stem, source.suffix, 1
    while target.exists() and target.resolve() != source.resolve():
        target = target_dir / f"{stem}_{n}{suffix}"
        n += 1
    try:
        if target.resolve() != source.resolve():
            shutil.copy2(source, target)
    except OSError:
        return None
    return Wallpaper(f"{_PREFIX_USER}{target.name}", target.stem, target, user=True)
