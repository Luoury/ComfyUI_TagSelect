# -*- coding: utf-8 -*-
"""标签胶囊的统一绘制逻辑（供单个控件与虚拟化画布共用）。"""

from __future__ import annotations

from ..qtcompat import QtCore, QtGui, text_width
from .. import icons, theme

PAD_H = 11
PAD_V = 6
GAP = 7


def fmt_count(n: int) -> str:
    n = int(n or 0)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}k"
    return str(n)


def chip_fonts(scale: float, compact: bool = False):
    base = 8.6 if compact else 9.4
    f_en = theme.font(int(round(base * scale)), 600)
    f_zh = theme.font(int(round((base - 1.0) * scale)), 400)
    f_badge = theme.font(int(round((base - 2.2) * scale)), 700)
    return f_en, f_zh, f_badge


def chip_height(scale: float, compact: bool = False) -> int:
    f_en, _, _ = chip_fonts(scale, compact)
    return QtGui.QFontMetrics(f_en).height() + int(PAD_V * 2 * scale) + 2


def chip_content_width(tag, mode: str, show_count: bool, scale: float,
                       selected: bool, removable: bool, compact: bool = False) -> int:
    f_en, f_zh, _ = chip_fonts(scale, compact)
    fm_en, fm_zh = QtGui.QFontMetrics(f_en), QtGui.QFontMetrics(f_zh)
    zh_first = mode == "zh"
    main = (tag.zh or tag.en) if zh_first else tag.en
    w = text_width(fm_zh if zh_first else fm_en, main)
    if mode == "both" and tag.zh:
        w += GAP + text_width(fm_zh, tag.zh)
    if show_count and tag.count:
        w += GAP + text_width(fm_zh, fmt_count(tag.count))
    # 始终预留对勾的位置，这样点击选中时胶囊尺寸不变、网格不会跳动
    w += int(13 * scale) + 5
    if removable:
        w += int(12 * scale) + 4
    if tag.r18:
        w += int(15 * scale) + 4
    return w


def chip_size(tag, mode: str = "both", show_count: bool = False, scale: float = 1.0,
              selected: bool = False, removable: bool = False,
              compact: bool = False) -> QtCore.QSize:
    w = chip_content_width(tag, mode, show_count, scale, selected, removable, compact)
    w += int(PAD_H * 2 * scale)
    h = chip_height(scale, compact)
    return QtCore.QSize(max(int(44 * scale), w), h)


def paint_chip(p: QtGui.QPainter, rect: QtCore.QRectF, tag, *, selected: bool = False,
               hover: bool = False, hover_close: bool = False, mode: str = "both",
               show_count: bool = False, scale: float = 1.0, removable: bool = False,
               compact: bool = False, dirty: bool = False) -> QtCore.QRect:
    """绘制一枚标签胶囊，返回移除按钮的矩形（不可移除时为空矩形）。"""
    p.setRenderHint(QtGui.QPainter.Antialiasing, True)
    p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
    r = QtCore.QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5)
    radius = theme.RADIUS_CHIP

    if selected:
        grad = QtGui.QLinearGradient(r.topLeft(), r.bottomRight())
        grad.setColorAt(0.0, QtGui.QColor(theme.SEL_BG_TOP))
        grad.setColorAt(1.0, QtGui.QColor(theme.SEL_BG_BOTTOM))
        p.setBrush(QtGui.QBrush(grad))
        p.setPen(QtGui.QPen(QtGui.QColor(theme.SEL_BORDER), 1.0))
        p.drawRoundedRect(r, radius, radius)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(255, 255, 255, 38))
        p.drawRoundedRect(QtCore.QRectF(r.left() + 1, r.top() + 1, r.width() - 2,
                                        r.height() * 0.44), radius - 1, radius - 1)
    else:
        bg = QtGui.QColor(255, 255, 255, 50) if hover else QtGui.QColor(226, 246, 255, 22)
        border = QtGui.QColor(theme.CHIP_BORDER_HOVER if hover else theme.CHIP_BORDER)
        p.setBrush(bg)
        p.setPen(QtGui.QPen(border, 1.0))
        p.drawRoundedRect(r, radius, radius)

    f_en, f_zh, f_badge = chip_fonts(scale, compact)
    fm_en, fm_zh = QtGui.QFontMetrics(f_en), QtGui.QFontMetrics(f_zh)

    x = r.left() + PAD_H * scale
    cy = r.center().y()

    if selected:
        box = int(12 * scale)
        icons.paint_glyph(p, "check", QtCore.QRectF(x, cy - box / 2, box, box), "#FFFFFF")
        x += box + 5

    if tag.r18:
        bw, bh = int(15 * scale), int(11 * scale)
        badge = QtCore.QRectF(x - 1, cy - bh / 2, bw, bh)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(255, 255, 255, 74) if selected
                   else QtGui.QColor(255, 92, 138, 215))
        p.drawRoundedRect(badge, 3, 3)
        p.setFont(f_badge)
        p.setPen(QtGui.QColor("#FFFFFF"))
        p.drawText(badge, QtCore.Qt.AlignCenter, "18")
        x += bw + 4

    zh_first = mode == "zh"
    main = (tag.zh or tag.en) if zh_first else tag.en
    p.setFont(f_zh if zh_first else f_en)
    p.setPen(QtGui.QColor(theme.SEL_TEXT if selected else theme.CHIP_TEXT))
    w_main = text_width(fm_zh if zh_first else fm_en, main)
    p.drawText(QtCore.QRectF(x, r.top(), w_main + 2, r.height()),
               QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, main)
    x += w_main + GAP

    if mode == "both" and tag.zh:
        p.setFont(f_zh)
        p.setPen(QtGui.QColor(theme.SEL_SUB if selected else theme.CHIP_SUB))
        p.drawText(QtCore.QRectF(x, r.top(), max(4.0, r.right() - x), r.height()),
                   QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, tag.zh)
        x += text_width(fm_zh, tag.zh) + GAP

    if show_count and tag.count:
        p.setFont(f_zh)
        p.setPen(QtGui.QColor(255, 255, 255, 184) if selected
                 else QtGui.QColor(theme.TEXT_FAINT))
        p.drawText(QtCore.QRectF(x, r.top(), 90, r.height()),
                   QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, fmt_count(tag.count))

    close_rect = QtCore.QRect()
    if removable:
        s = int(13 * scale)
        close_rect = QtCore.QRect(int(r.right() - s - 7 * scale),
                                  int(r.center().y() - s / 2), s, s)
        if hover_close:
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QColor(255, 107, 129, 235))
            p.drawEllipse(QtCore.QRectF(close_rect))
            col = "#FFFFFF"
        else:
            col = "rgba(255,255,255,0.78)" if selected else theme.TEXT_DIM
        icons.paint_glyph(p, "close", QtCore.QRectF(close_rect), col)

    if dirty:  # 自定义标签的角标
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(theme.MIKU_PINK))
        p.drawEllipse(QtCore.QRectF(r.right() - 7, r.top() + 3, 4.5, 4.5))

    return close_rect


def chip_tooltip(tag) -> str:
    bits = [f"<b>{tag.en}</b>"]
    if tag.zh:
        bits.append(tag.zh)
    if getattr(tag, "count", 0):
        bits.append(f"投稿量 {tag.count:,}")
    if getattr(tag, "r18", 0):
        bits.append("<span style='color:#FF8FA3'>R18</span>")
    if getattr(tag, "custom", False):
        bits.append("<i>自定义标签</i>")
    bits.append("<span style='color:#8FB4D6'>单击加入 · 再次单击移除</span>")
    return "<br>".join(bits)
