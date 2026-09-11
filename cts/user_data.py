# -*- coding: utf-8 -*-
"""用户数据的读写：设置、自定义标签、自定义预设、常驻预设。"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from typing import Any

from .qtcompat import QtCore, Signal
from .resources import DATA_DIR, user_data_dir

SETTINGS_FILE = "settings.json"
CUSTOM_FILE = "custom_tags.json"
PRESETS_FILE = "user_presets.json"
BUILTIN_PRESETS = DATA_DIR / "presets.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "wallpaper": "",            # 空 = 使用默认壁纸
    "scrim": 0.52,              # 背景压暗程度 0~0.85
    "blur": 0.0,                # 背景模糊半径 px
    "r18": False,               # R18 开关，默认关闭
    "copy_format": "comma",     # comma | comma_space | space | newline | brace
    "font_scale": 1.0,
    "sidebar_collapsed": False,
    "last_page": "library",
    "show_counts": True,
    "confirm_clear": True,
    "chip_mode": "both",        # both | en | zh
    "window": None,             # [x, y, w, h]
}

COPY_FORMATS = [
    ("comma", "英文逗号  (a,b,c)"),
    ("comma_space", "逗号加空格  (a, b, c)"),
    ("space", "空格分隔  (a b c)"),
    ("newline", "每行一个"),
    ("brace", "花括号  ({a},{b})"),
]


def _atomic_write(path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _read_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return fallback


class UserData(QtCore.QObject):
    """用户数据的唯一入口。"""

    customChanged = Signal()
    presetsChanged = Signal()
    settingsChanged = Signal(str)

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.dir = user_data_dir()
        self.settings: dict[str, Any] = dict(DEFAULT_SETTINGS)
        self.custom_tags: list[dict] = []
        self.user_presets: list[dict] = []
        self.builtin_groups: list[dict] = []
        self.load()

    # ------------------------------------------------------------ 读写
    def load(self) -> None:
        s = _read_json(self.dir / SETTINGS_FILE, {})
        if isinstance(s, dict):
            self.settings.update(s)
        c = _read_json(self.dir / CUSTOM_FILE, [])
        if isinstance(c, list):
            self.custom_tags = [r for r in c if isinstance(r, dict) and r.get("en")]
        p = _read_json(self.dir / PRESETS_FILE, [])
        if isinstance(p, list):
            self.user_presets = [r for r in p if isinstance(r, dict) and r.get("name")]
        b = _read_json(BUILTIN_PRESETS, {})
        self.builtin_groups = b.get("groups", []) if isinstance(b, dict) else []

    def save_settings(self) -> None:
        _atomic_write(self.dir / SETTINGS_FILE, json.dumps(self.settings, ensure_ascii=False, indent=2))

    def save_custom(self) -> None:
        _atomic_write(self.dir / CUSTOM_FILE, json.dumps(self.custom_tags, ensure_ascii=False, indent=2))

    def save_presets(self) -> None:
        _atomic_write(self.dir / PRESETS_FILE, json.dumps(self.user_presets, ensure_ascii=False, indent=2))

    # ------------------------------------------------------------ 设置
    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, DEFAULT_SETTINGS.get(key, default))

    def set(self, key: str, value: Any, save: bool = True) -> None:
        if self.settings.get(key) == value:
            return
        self.settings[key] = value
        if save:
            self.save_settings()
        self.settingsChanged.emit(key)

    # ------------------------------------------------------------ 自定义标签
    def add_custom_tag(self, english: str, chinese: str = "", note: str = "",
                       group: str = "我的标签") -> dict | None:
        english = english.strip()
        if not english:
            return None
        for row in self.custom_tags:
            if row["en"].lower() == english.lower():
                row["zh"] = chinese.strip() or row.get("zh", "")
                row["note"] = note.strip() or row.get("note", "")
                row["group"] = group or "我的标签"
                self.save_custom()
                self.customChanged.emit()
                return row
        row = {
            "id": uuid.uuid4().hex[:12],
            "en": english,
            "zh": chinese.strip(),
            "note": note.strip(),
            "group": group or "我的标签",
        }
        self.custom_tags.append(row)
        self.save_custom()
        self.customChanged.emit()
        return row

    def remove_custom_tag(self, english: str) -> bool:
        before = len(self.custom_tags)
        self.custom_tags = [r for r in self.custom_tags if r["en"].lower() != english.lower()]
        if len(self.custom_tags) != before:
            self.save_custom()
            self.customChanged.emit()
            return True
        return False

    def update_custom_tag(self, old_en: str, english: str, chinese: str, note: str, group: str) -> None:
        for row in self.custom_tags:
            if row["en"].lower() == old_en.lower():
                row["en"] = english.strip() or row["en"]
                row["zh"] = chinese.strip()
                row["note"] = note.strip()
                row["group"] = group or "我的标签"
                break
        self.save_custom()
        self.customChanged.emit()

    def custom_groups(self) -> list[str]:
        out: list[str] = []
        for row in self.custom_tags:
            g = row.get("group") or "我的标签"
            if g not in out:
                out.append(g)
        return out

    # ------------------------------------------------------------ 预设
    def add_preset(self, name: str, tags: list[str], negative: list[str] | None = None,
                   desc: str = "", group: str = "我的预设") -> dict:
        name = name.strip() or "未命名预设"
        for row in self.user_presets:
            if row["name"] == name:
                row["tags"] = list(tags)
                row["negative"] = list(negative or [])
                row["desc"] = desc
                row["group"] = group
                self.save_presets()
                self.presetsChanged.emit()
                return row
        row = {
            "id": uuid.uuid4().hex[:12],
            "name": name,
            "desc": desc,
            "group": group or "我的预设",
            "tags": list(tags),
            "negative": list(negative or []),
        }
        self.user_presets.append(row)
        self.save_presets()
        self.presetsChanged.emit()
        return row

    def update_preset(self, pid: str, **fields: Any) -> None:
        for row in self.user_presets:
            if row.get("id") == pid:
                row.update({k: v for k, v in fields.items() if v is not None})
                break
        self.save_presets()
        self.presetsChanged.emit()

    def remove_preset(self, pid: str) -> None:
        self.user_presets = [r for r in self.user_presets if r.get("id") != pid]
        self.save_presets()
        self.presetsChanged.emit()

    def preset_by_id(self, pid: str) -> dict | None:
        for row in self.user_presets:
            if row.get("id") == pid:
                merged = dict(row)
                merged.setdefault("group", "我的预设")
                return merged
        for group in self.builtin_groups:
            for row in group.get("presets", []):
                if row.get("id") == pid:
                    merged = dict(row)
                    merged.setdefault("group", group.get("name", "常驻预设"))
                    return merged
        return None

    def is_builtin(self, pid: str) -> bool:
        for group in self.builtin_groups:
            for row in group.get("presets", []):
                if row.get("id") == pid:
                    return True
        return False

    def groups_with_presets(self) -> list[dict]:
        """用户的预设排在最前，其后是内置常驻预设分组。"""
        out: list[dict] = []
        if self.user_presets:
            out.append({
                "id": "mine",
                "name": "我的预设",
                "desc": "你保存的预设，点击即可把标签加入上方选择框。",
                "presets": self.user_presets,
                "user": True,
            })
        for group in self.builtin_groups:
            out.append({**group, "user": False})
        return out
