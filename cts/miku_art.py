# -*- coding: utf-8 -*-
"""初音未来小彩蛋的矢量绘制：Q 版未来、大葱、音符 Logo。

所有图形都在 100×100 的逻辑坐标系里绘制，再由调用方缩放到目标矩形。
"""

from __future__ import annotations

from .qtcompat import QtCore, QtGui
from . import theme

C_SKIN = "#FFE3D6"
C_SKIN_SHADE = "#F5C6B4"
C_HAIR = "#4FD8CE"
C_HAIR_DARK = "#2AA9A6"
C_HAIR_LIGHT = "#9DF1E8"
C_EYE = "#28B6C9"
C_EYE_DARK = "#12505F"
C_TIE = "#FF5C8A"
C_CLOTH = "#22304A"
C_LINE = "#1B2A40"

def _canvas(p: QtGui.QPainter, rect: QtCore.QRectF) -> None:
    """把 100×100 逻辑坐标映射到 rect。"""
    s = min(rect.width(), rect.height()) / 100.0
    p.translate(rect.center())
    p.scale(s, s)
    p.translate(-50, -50)

def draw_leek(p: QtGui.QPainter, rect: QtCore.QRectF, angle: float = 0.0) -> None:
    """画一根大葱（初音未来的应援物）。"""
    p.save()
    p.setRenderHint(QtGui.QPainter.Antialiasing, True)
    _canvas(p, rect)
    p.translate(50, 50)
    p.rotate(angle)
    p.translate(-50, -50)

    p.setPen(QtCore.Qt.NoPen)
    # 白色葱白
    grad = QtGui.QLinearGradient(0, 60, 0, 96)
    grad.setColorAt(0.0, QtGui.QColor("#F4FFF9"))
    grad.setColorAt(1.0, QtGui.QColor("#CDE9DA"))
    p.setBrush(QtGui.QBrush(grad))
    p.drawRoundedRect(QtCore.QRectF(38, 58, 24, 38), 10, 10)
    # 绿色葱叶
    for angle_leaf in (-26, -8, 10, 28):
        p.save()
        p.translate(50, 60)
        p.rotate(angle_leaf)
        grad = QtGui.QLinearGradient(0, 0, 0, -52)
        grad.setColorAt(0.0, QtGui.QColor("#5FCB6A"))
        grad.setColorAt(1.0, QtGui.QColor("#1F8F45"))
        p.setBrush(QtGui.QBrush(grad))
        p.drawRoundedRect(QtCore.QRectF(-6.5, -52, 13, 56), 6.5, 6.5)
        p.restore()
    p.restore()

def draw_logo(p: QtGui.QPainter, rect: QtCore.QRectF, glow: bool = True) -> None:
    """圆形 Logo：青色渐变 + 音符 + "39"。"""
    p.save()
    p.setRenderHint(QtGui.QPainter.Antialiasing, True)
    s = min(rect.width(), rect.height())
    box = QtCore.QRectF(rect.center().x() - s / 2, rect.center().y() - s / 2, s, s)

    if glow:
        p.setPen(QtCore.Qt.NoPen)
        for i in range(5, 0, -1):
            p.setBrush(QtGui.QColor(57, 197, 187, int(11 * (6 - i) / 5)))
            p.drawEllipse(box.adjusted(-i * s * 0.06, -i * s * 0.06, i * s * 0.06, i * s * 0.06))

    grad = QtGui.QLinearGradient(box.topLeft(), box.bottomRight())
    grad.setColorAt(0.0, QtGui.QColor(theme.MIKU_BLUE))
    grad.setColorAt(1.0, QtGui.QColor(theme.MIKU_CYAN))
    p.setBrush(QtGui.QBrush(grad))
    p.setPen(QtGui.QPen(QtGui.QColor(200, 250, 255, 160), max(1.0, s * 0.035)))
    p.drawEllipse(box.adjusted(s * 0.03, s * 0.03, -s * 0.03, -s * 0.03))

    # 音符
    from . import icons
    icons.paint_glyph(p, "note", box.adjusted(s * 0.16, s * 0.16, -s * 0.16, -s * 0.16), "#FFFFFF")
    p.restore()
