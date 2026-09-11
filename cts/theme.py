# -*- coding: utf-8 -*-
"""初音未来主题：配色、字体、全局样式表。"""

from __future__ import annotations

from dataclasses import dataclass

from .qtcompat import QtGui

# ---------------------------------------------------------------- 配色
MIKU_CYAN = "#39C5BB"      # 初音未来官方应援色
MIKU_CYAN_LIGHT = "#6FE3DA"
MIKU_BLUE = "#2E8BFF"
MIKU_BLUE_DEEP = "#1B5FD0"
MIKU_PINK = "#FF6FA5"      # 点缀色（发饰/心形）

# 未选中标签
CHIP_BG = "rgba(226, 246, 255, 0.085)"
CHIP_BG_HOVER = "rgba(226, 246, 255, 0.17)"
CHIP_BORDER = "rgba(140, 220, 255, 0.26)"
CHIP_BORDER_HOVER = "rgba(110, 227, 218, 0.75)"
CHIP_TEXT = "#E4F4FF"
CHIP_SUB = "#8FB4D6"

# 选中标签（蓝色）
SEL_BG_TOP = "#2F8BFF"
SEL_BG_BOTTOM = "#39C5BB"
SEL_BORDER = "rgba(190, 250, 255, 0.85)"
SEL_TEXT = "#FFFFFF"
SEL_SUB = "rgba(255,255,255,0.80)"

GLASS_BG = "rgba(9, 20, 36, 0.62)"
GLASS_BG_STRONG = "rgba(7, 16, 30, 0.80)"
GLASS_BORDER = "rgba(120, 210, 255, 0.20)"
TEXT_MAIN = "#EAF6FF"
TEXT_DIM = "#9DBAD6"
TEXT_FAINT = "#6E8AA6"
DANGER = "#FF6B81"

RADIUS_CHIP = 11
RADIUS_CARD = 16
RADIUS_PILL = 14


@dataclass(frozen=True)
class Fonts:
    family: str
    mono: str


_CJK_CANDIDATES = [
    "Microsoft YaHei UI",
    "Microsoft YaHei",
    "PingFang SC",
    "Hiragino Sans GB",
    "Noto Sans CJK SC",
    "Source Han Sans SC",
    "Source Han Sans CN",
    "WenQuanYi Micro Hei",
    "SimHei",
]

_MONO_CANDIDATES = ["JetBrains Mono", "Cascadia Mono", "Consolas", "DejaVu Sans Mono", "Courier New"]


def _pick(candidates: list[str], fallback: str) -> str:
    families = set(QtGui.QFontDatabase().families())
    for name in candidates:
        if name in families:
            return name
    return fallback


def resolve_fonts() -> Fonts:
    return Fonts(family=_pick(_CJK_CANDIDATES, "Segoe UI"), mono=_pick(_MONO_CANDIDATES, "monospace"))


_FONTS: Fonts | None = None


def fonts() -> Fonts:
    global _FONTS
    if _FONTS is None:
        _FONTS = resolve_fonts()
    return _FONTS


def font(size: float, weight: int = 400, mono: bool = False) -> QtGui.QFont:
    """构造一个带正确 CJK 字体族的 QFont。

    size 允许传浮点，内部会取整；只区分"常规/加粗"两档，
    避免 Qt5 与 Qt6 在 QFont.setWeight 语义上的差异。
    """
    f = QtGui.QFont(fonts().mono if mono else fonts().family, int(round(size)))
    if weight >= 600:
        f.setBold(True)
    return f


def global_qss() -> str:
    """全局样式表：滚动条、工具提示、菜单、滑块等。"""
    fam = fonts().family
    return f"""
* {{ font-family: "{fam}"; }}

QToolTip {{
    background: rgba(8, 18, 32, 0.96);
    color: {TEXT_MAIN};
    border: 1px solid {GLASS_BORDER};
    border-radius: 8px;
    padding: 6px 9px;
}}

QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 2px 2px 2px 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(140, 220, 255, 0.30);
    border-radius: 5px; min-height: 34px;
}}
QScrollBar::handle:vertical:hover {{ background: {MIKU_CYAN}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

QScrollBar:horizontal {{
    background: transparent; height: 10px; margin: 0 2px 2px 2px;
}}
QScrollBar::handle:horizontal {{
    background: rgba(140, 220, 255, 0.30);
    border-radius: 5px; min-width: 34px;
}}
QScrollBar::handle:horizontal:hover {{ background: {MIKU_CYAN}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

QLineEdit {{
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid {CHIP_BORDER};
    border-radius: 12px;
    padding: 7px 12px;
    color: {TEXT_MAIN};
    selection-background-color: {MIKU_BLUE};
}}
QLineEdit:focus {{ border: 1px solid {MIKU_CYAN}; background: rgba(255, 255, 255, 0.10); }}
QLineEdit::placeholder {{ color: {TEXT_FAINT}; }}

QPlainTextEdit, QTextEdit {{
    background: rgba(6, 14, 26, 0.72);
    border: 1px solid {GLASS_BORDER};
    border-radius: 12px;
    color: {TEXT_MAIN};
    padding: 8px;
    selection-background-color: {MIKU_BLUE};
}}

QComboBox {{
    background: rgba(255, 255, 255, 0.07);
    border: 1px solid {CHIP_BORDER};
    border-radius: 10px; padding: 5px 10px; color: {TEXT_MAIN};
}}
QComboBox:hover {{ border: 1px solid {MIKU_CYAN}; }}
QComboBox QAbstractItemView {{
    background: #0B1626; color: {TEXT_MAIN};
    border: 1px solid {GLASS_BORDER};
    selection-background-color: {MIKU_BLUE_DEEP};
    outline: none;
}}
QComboBox::drop-down {{ border: none; width: 18px; }}

QMenu {{
    background: #0B1626; color: {TEXT_MAIN};
    border: 1px solid {GLASS_BORDER}; border-radius: 10px; padding: 5px;
}}
QMenu::item {{ padding: 6px 20px 6px 14px; border-radius: 7px; }}
QMenu::item:selected {{ background: {MIKU_BLUE_DEEP}; }}

QCheckBox {{ color: {TEXT_MAIN}; spacing: 8px; }}
QCheckBox::indicator {{
    width: 17px; height: 17px; border-radius: 5px;
    border: 1px solid {CHIP_BORDER}; background: rgba(255,255,255,0.07);
}}
QCheckBox::indicator:checked {{ background: {MIKU_CYAN}; border: 1px solid {MIKU_CYAN_LIGHT}; }}

QSlider::groove:horizontal {{ height: 5px; background: rgba(255,255,255,0.14); border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {MIKU_CYAN}; border-radius: 3px; }}
QSlider::handle:horizontal {{
    width: 14px; height: 14px; margin: -5px 0; border-radius: 7px;
    background: #FFFFFF; border: 2px solid {MIKU_CYAN};
}}

QMessageBox, QDialog {{ background: #0B1626; color: {TEXT_MAIN}; }}
QMessageBox QLabel {{ color: {TEXT_MAIN}; }}
QMessageBox QPushButton, QDialog QPushButton {{
    background: rgba(255,255,255,0.10); color: {TEXT_MAIN};
    border: 1px solid {CHIP_BORDER}; border-radius: 9px; padding: 6px 16px; min-width: 62px;
}}
QMessageBox QPushButton:hover, QDialog QPushButton:hover {{ background: {MIKU_BLUE_DEEP}; }}

QSplitter::handle {{ background: transparent; }}
"""
