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

def _blob(pts: list[tuple[float, float]]) -> QtGui.QPainterPath:
    """用三次贝塞尔把一串控制点连成平滑闭合曲线。"""
    path = QtGui.QPainterPath()
    n = len(pts)
    path.moveTo(*pts[0])
    for i in range(n):
        p0 = pts[(i - 1) % n]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6.0, p1[1] + (p2[1] - p0[1]) / 6.0)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6.0, p2[1] - (p3[1] - p1[1]) / 6.0)
        path.cubicTo(QtCore.QPointF(*c1), QtCore.QPointF(*c2), QtCore.QPointF(*p2))
    path.closeSubpath()
    return path

def draw_chibi(p: QtGui.QPainter, rect: QtCore.QRectF, blink: float = 0.0,
               sway: float = 0.0, alpha: float = 1.0) -> None:
    """画一只 Q 版初音未来。

    blink: 0=睁眼, 1=完全闭眼
    sway : -1..1 轻微摇摆（单位：逻辑像素）
    """
    p.save()
    p.setRenderHint(QtGui.QPainter.Antialiasing, True)
    if alpha < 1.0:
        p.setOpacity(alpha)
    _canvas(p, rect)
    p.translate(sway * 1.6, 0)

    # ---- 双马尾（在头后面）
    p.setPen(QtCore.Qt.NoPen)
    for direction in (-1, 1):
        grad = QtGui.QLinearGradient(50, 18, 50, 92)
        grad.setColorAt(0.0, QtGui.QColor(C_HAIR_LIGHT))
        grad.setColorAt(0.45, QtGui.QColor(C_HAIR))
        grad.setColorAt(1.0, QtGui.QColor(C_HAIR_DARK))
        p.setBrush(QtGui.QBrush(grad))
        tail = _blob([
            (50 + direction * 20, 24),
            (50 + direction * 42, 30),
            (50 + direction * 50, 58),
            (50 + direction * 40, 84),
            (50 + direction * 26, 74),
            (50 + direction * 20, 46),
        ])
        p.drawPath(tail)

    # ---- 身体
    p.setBrush(QtGui.QColor(C_CLOTH))
    body = _blob([(38, 74), (50, 70), (62, 74), (66, 96), (34, 96)])
    p.drawPath(body)
    # 领带
    p.setBrush(QtGui.QColor(theme.MIKU_CYAN))
    p.drawPolygon(QtCore.QPointF(50, 74), QtCore.QPointF(44, 78),
                  QtCore.QPointF(50, 92), QtCore.QPointF(56, 78))
    # 袖套
    p.setBrush(QtGui.QColor("#E8F7FF"))
    for direction in (-1, 1):
        p.drawEllipse(QtCore.QRectF(50 + direction * 20 - 6, 76, 12, 16))

    # ---- 头
    p.setPen(QtGui.QPen(QtGui.QColor(C_LINE), 1.1))
    grad = QtGui.QLinearGradient(50, 8, 50, 66)
    grad.setColorAt(0.0, QtGui.QColor("#FFF3EC"))
    grad.setColorAt(1.0, QtGui.QColor(C_SKIN))
    p.setBrush(QtGui.QBrush(grad))
    p.drawEllipse(QtCore.QRectF(24, 10, 52, 54))

    # ---- 刘海
    p.setPen(QtCore.Qt.NoPen)
    grad = QtGui.QLinearGradient(50, 6, 50, 44)
    grad.setColorAt(0.0, QtGui.QColor(C_HAIR_LIGHT))
    grad.setColorAt(1.0, QtGui.QColor(C_HAIR))
    p.setBrush(QtGui.QBrush(grad))
    bangs = _blob([(23, 34), (24, 14), (50, 4), (76, 14), (77, 34),
                   (68, 26), (56, 32), (44, 32), (32, 26)])
    p.drawPath(bangs)
    # 鬓发
    for direction in (-1, 1):
        p.setBrush(QtGui.QColor(C_HAIR_DARK))
        p.drawPolygon(QtCore.QPointF(50 + direction * 26, 26),
                      QtCore.QPointF(50 + direction * 29, 26),
                      QtCore.QPointF(50 + direction * 26, 58),
                      QtCore.QPointF(50 + direction * 21, 54))

    # ---- 发饰（方块发圈）
    p.setBrush(QtGui.QColor(C_TIE))
    for direction in (-1, 1):
        p.drawRoundedRect(QtCore.QRectF(50 + direction * 30 - 3.6, 26, 7.2, 7.2), 1.6, 1.6)

    # ---- 腮红
    p.setBrush(QtGui.QColor(255, 150, 170, 90))
    p.drawEllipse(QtCore.QRectF(29, 45, 11, 7))
    p.drawEllipse(QtCore.QRectF(60, 45, 11, 7))

    # ---- 眼睛
    eye_open = max(0.06, 1.0 - blink)
    for direction in (-1, 1):
        cx = 50 + direction * 13
        h = 15.0 * eye_open
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(C_EYE_DARK))
        p.drawEllipse(QtCore.QRectF(cx - 7.0, 42 - h / 2, 14.0, h))
        p.setBrush(QtGui.QColor(C_EYE))
        p.drawEllipse(QtCore.QRectF(cx - 5.4, 42 - h * 0.40, 10.8, h * 0.80))
        if eye_open > 0.35:
            p.setBrush(QtGui.QColor("#FFFFFF"))
            p.drawEllipse(QtCore.QRectF(cx - 2.6, 38.6, 4.6, 4.6))
            p.setBrush(QtGui.QColor(255, 255, 255, 190))
            p.drawEllipse(QtCore.QRectF(cx + 1.4, 45.0, 2.6, 2.6))
    # 睫毛/上眼线
    pen = QtGui.QPen(QtGui.QColor(C_LINE), 1.5)
    pen.setCapStyle(QtCore.Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(QtCore.Qt.NoBrush)
    for direction in (-1, 1):
        cx = 50 + direction * 13
        p.drawArc(QtCore.QRectF(cx - 7.6, 42 - 8.0 * eye_open, 15.2, 15.0 * eye_open),
                  20 * 16, 140 * 16)

    # ---- 嘴
    p.setPen(QtGui.QPen(QtGui.QColor(C_LINE), 1.3))
    p.drawArc(QtCore.QRectF(45, 51, 10, 8), 200 * 16, 140 * 16)

    p.restore()

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
