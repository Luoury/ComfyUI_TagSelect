# -*- coding: utf-8 -*-
"""用 QPainter 手绘的线性图标，避免依赖任何图片资源或 emoji 字体。"""

from __future__ import annotations

from .qtcompat import QtCore, QtGui
from . import theme

_CACHE: dict[tuple, QtGui.QIcon] = {}


def _pen(p: QtGui.QPainter, color: str, w: float) -> None:
    pen = QtGui.QPen(QtGui.QColor(color))
    pen.setWidthF(w)
    pen.setCapStyle(QtCore.Qt.RoundCap)
    pen.setJoinStyle(QtCore.Qt.RoundJoin)
    p.setPen(pen)
    p.setBrush(QtCore.Qt.NoBrush)


def _paint(name: str, p: QtGui.QPainter, s: float, color: str) -> None:
    """在 s×s 的坐标系里绘制图标（逻辑尺寸 24×24 缩放）。"""
    p.setRenderHint(QtGui.QPainter.Antialiasing, True)
    p.scale(s / 24.0, s / 24.0)
    w = 1.9
    _pen(p, color, w)

    if name == "grid":
        p.drawRoundedRect(QtCore.QRectF(3.5, 3.5, 7, 7), 2, 2)
        p.drawRoundedRect(QtCore.QRectF(13.5, 3.5, 7, 7), 2, 2)
        p.drawRoundedRect(QtCore.QRectF(3.5, 13.5, 7, 7), 2, 2)
        p.drawRoundedRect(QtCore.QRectF(13.5, 13.5, 7, 7), 2, 2)
    elif name == "search":
        p.drawEllipse(QtCore.QRectF(4.2, 4.2, 12.4, 12.4))
        p.drawLine(QtCore.QPointF(16.2, 16.2), QtCore.QPointF(20.2, 20.2))
    elif name == "star":
        path = QtGui.QPainterPath()
        import math
        for i in range(10):
            ang = -math.pi / 2 + i * math.pi / 5
            r = 9.2 if i % 2 == 0 else 4.0
            pt = QtCore.QPointF(12 + r * math.cos(ang), 12 + r * math.sin(ang))
            path.moveTo(pt) if i == 0 else path.lineTo(pt)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "pencil":
        p.drawLine(QtCore.QPointF(4.5, 19.5), QtCore.QPointF(8.0, 18.6))
        p.drawLine(QtCore.QPointF(4.5, 19.5), QtCore.QPointF(5.4, 16.0))
        p.drawLine(QtCore.QPointF(5.4, 16.0), QtCore.QPointF(15.4, 6.0))
        p.drawLine(QtCore.QPointF(8.0, 18.6), QtCore.QPointF(18.0, 8.6))
        p.drawLine(QtCore.QPointF(15.4, 6.0), QtCore.QPointF(18.0, 8.6))
    elif name == "settings":
        p.drawEllipse(QtCore.QRectF(9.0, 9.0, 6, 6))
        import math
        for i in range(8):
            a = i * math.pi / 4
            p.drawLine(
                QtCore.QPointF(12 + 8.0 * math.cos(a), 12 + 8.0 * math.sin(a)),
                QtCore.QPointF(12 + 10.2 * math.cos(a), 12 + 10.2 * math.sin(a)),
            )
    elif name == "info":
        p.drawEllipse(QtCore.QRectF(3.6, 3.6, 16.8, 16.8))
        p.drawLine(QtCore.QPointF(12, 11.0), QtCore.QPointF(12, 16.6))
        p.drawPoint(QtCore.QPointF(12, 7.9))
    elif name == "copy":
        p.drawRoundedRect(QtCore.QRectF(8.4, 3.6, 12.0, 12.0), 2.4, 2.4)
        p.drawRoundedRect(QtCore.QRectF(3.6, 8.4, 12.0, 12.0), 2.4, 2.4)
    elif name == "trash":
        p.drawLine(QtCore.QPointF(4.4, 6.6), QtCore.QPointF(19.6, 6.6))
        p.drawLine(QtCore.QPointF(9.6, 6.6), QtCore.QPointF(9.6, 4.0))
        p.drawLine(QtCore.QPointF(14.4, 6.6), QtCore.QPointF(14.4, 4.0))
        p.drawLine(QtCore.QPointF(9.6, 4.0), QtCore.QPointF(14.4, 4.0))
        p.drawPolyline([QtCore.QPointF(6.4, 6.6), QtCore.QPointF(7.3, 20.0),
                        QtCore.QPointF(16.7, 20.0), QtCore.QPointF(17.6, 6.6)])
        p.drawLine(QtCore.QPointF(10.4, 10.0), QtCore.QPointF(10.9, 16.6))
        p.drawLine(QtCore.QPointF(13.6, 10.0), QtCore.QPointF(13.1, 16.6))
    elif name == "close":
        p.drawLine(QtCore.QPointF(5.6, 5.6), QtCore.QPointF(18.4, 18.4))
        p.drawLine(QtCore.QPointF(18.4, 5.6), QtCore.QPointF(5.6, 18.4))
    elif name == "plus":
        p.drawLine(QtCore.QPointF(12, 4.6), QtCore.QPointF(12, 19.4))
        p.drawLine(QtCore.QPointF(4.6, 12), QtCore.QPointF(19.4, 12))
    elif name == "check":
        p.drawPolyline([QtCore.QPointF(4.6, 12.8), QtCore.QPointF(9.8, 18.0), QtCore.QPointF(19.4, 6.4)])
    elif name == "save":
        p.drawRoundedRect(QtCore.QRectF(4.0, 4.0, 16.0, 16.0), 2.6, 2.6)
        p.drawRect(QtCore.QRectF(8.0, 4.0, 8.0, 5.4))
        p.drawRoundedRect(QtCore.QRectF(7.4, 13.2, 9.2, 6.8), 1.6, 1.6)
    elif name == "shuffle":
        p.drawPolyline([QtCore.QPointF(3.6, 7.0), QtCore.QPointF(8.0, 7.0),
                        QtCore.QPointF(16.0, 17.0), QtCore.QPointF(20.4, 17.0)])
        p.drawPolyline([QtCore.QPointF(3.6, 17.0), QtCore.QPointF(8.0, 17.0),
                        QtCore.QPointF(16.0, 7.0), QtCore.QPointF(20.4, 7.0)])
        p.drawPolyline([QtCore.QPointF(17.4, 4.2), QtCore.QPointF(20.4, 7.0), QtCore.QPointF(17.4, 9.8)])
        p.drawPolyline([QtCore.QPointF(17.4, 14.2), QtCore.QPointF(20.4, 17.0), QtCore.QPointF(17.4, 19.8)])
    elif name == "chevron_right":
        p.drawPolyline([QtCore.QPointF(9.4, 5.6), QtCore.QPointF(16.0, 12.0), QtCore.QPointF(9.4, 18.4)])
    elif name == "chevron_left":
        p.drawPolyline([QtCore.QPointF(14.6, 5.6), QtCore.QPointF(8.0, 12.0), QtCore.QPointF(14.6, 18.4)])
    elif name == "chevron_down":
        p.drawPolyline([QtCore.QPointF(5.6, 9.4), QtCore.QPointF(12.0, 16.0), QtCore.QPointF(18.4, 9.4)])
    elif name == "image":
        p.drawRoundedRect(QtCore.QRectF(3.4, 5.0, 17.2, 14.0), 2.6, 2.6)
        p.drawEllipse(QtCore.QRectF(6.6, 8.0, 3.0, 3.0))
        p.drawPolyline([QtCore.QPointF(4.4, 17.2), QtCore.QPointF(10.0, 12.0),
                        QtCore.QPointF(14.0, 15.6), QtCore.QPointF(16.4, 13.4), QtCore.QPointF(19.6, 16.6)])
    elif name == "heart":
        path = QtGui.QPainterPath()
        path.moveTo(12.0, 20.0)
        path.cubicTo(2.4, 13.6, 3.4, 5.4, 8.4, 4.6)
        path.cubicTo(10.6, 4.2, 12.0, 6.0, 12.0, 7.4)
        path.cubicTo(12.0, 6.0, 13.4, 4.2, 15.6, 4.6)
        path.cubicTo(20.6, 5.4, 21.6, 13.6, 12.0, 20.0)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "wand":
        p.drawLine(QtCore.QPointF(5.0, 19.0), QtCore.QPointF(15.0, 9.0))
        p.drawLine(QtCore.QPointF(13.4, 7.4), QtCore.QPointF(16.6, 10.6))
        for dx, dy, r in ((18.4, 4.0, 2.4), (6.0, 4.6, 1.6), (20.0, 12.0, 1.5)):
            p.drawLine(QtCore.QPointF(dx - r, dy), QtCore.QPointF(dx + r, dy))
            p.drawLine(QtCore.QPointF(dx, dy - r), QtCore.QPointF(dx, dy + r))
    elif name == "note":
        p.drawLine(QtCore.QPointF(10.0, 17.6), QtCore.QPointF(10.0, 5.2))
        p.drawLine(QtCore.QPointF(10.0, 5.2), QtCore.QPointF(18.0, 7.2))
        p.drawLine(QtCore.QPointF(18.0, 7.2), QtCore.QPointF(18.0, 15.4))
        p.drawEllipse(QtCore.QRectF(6.0, 15.4, 4.4, 3.6))
        p.drawEllipse(QtCore.QRectF(14.0, 13.2, 4.4, 3.6))
    elif name == "tag":
        path = QtGui.QPainterPath()
        path.moveTo(11.0, 3.6)
        path.lineTo(20.4, 3.6)
        path.lineTo(20.4, 13.0)
        path.lineTo(12.2, 20.4)
        path.lineTo(3.6, 11.8)
        path.closeSubpath()
        p.drawPath(path)
        p.drawEllipse(QtCore.QRectF(15.6, 6.6, 2.6, 2.6))
    elif name == "download":
        p.drawLine(QtCore.QPointF(12, 4.0), QtCore.QPointF(12, 15.0))
        p.drawPolyline([QtCore.QPointF(7.4, 10.6), QtCore.QPointF(12, 15.2), QtCore.QPointF(16.6, 10.6)])
        p.drawPolyline([QtCore.QPointF(4.6, 16.4), QtCore.QPointF(4.6, 19.6),
                        QtCore.QPointF(19.4, 19.6), QtCore.QPointF(19.4, 16.4)])
    elif name == "eye":
        path = QtGui.QPainterPath()
        path.moveTo(2.8, 12.0)
        path.quadTo(12.0, 3.6, 21.2, 12.0)
        path.quadTo(12.0, 20.4, 2.8, 12.0)
        p.drawPath(path)
        p.drawEllipse(QtCore.QRectF(9.4, 9.4, 5.2, 5.2))
    elif name == "eye_off":
        path = QtGui.QPainterPath()
        path.moveTo(2.8, 12.0)
        path.quadTo(12.0, 3.6, 21.2, 12.0)
        path.quadTo(12.0, 20.4, 2.8, 12.0)
        p.drawPath(path)
        p.drawEllipse(QtCore.QRectF(9.4, 9.4, 5.2, 5.2))
        _pen(p, "#0B1626", 4.2)
        p.drawLine(QtCore.QPointF(4.0, 20.0), QtCore.QPointF(20.0, 4.0))
        _pen(p, color, w)
        p.drawLine(QtCore.QPointF(4.0, 20.0), QtCore.QPointF(20.0, 4.0))
    else:  # 兜底：一个圆点
        p.drawEllipse(QtCore.QRectF(8.0, 8.0, 8.0, 8.0))


def make_pixmap(name: str, size: int = 20, color: str = theme.TEXT_MAIN, ratio: float = 2.0) -> QtGui.QPixmap:
    pm = QtGui.QPixmap(int(size * ratio), int(size * ratio))
    pm.setDevicePixelRatio(ratio)
    pm.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pm)
    _paint(name, p, size * ratio, color)
    p.end()
    return pm


def icon(name: str, size: int = 20, color: str = theme.TEXT_MAIN) -> QtGui.QIcon:
    key = (name, size, color)
    if key not in _CACHE:
        _CACHE[key] = QtGui.QIcon(make_pixmap(name, size, color))
    return _CACHE[key]


def paint_glyph(p: QtGui.QPainter, name: str, rect: QtCore.QRectF, color: str) -> None:
    """在指定矩形内绘制图标（用于自绘控件）。"""
    p.save()
    p.translate(rect.topLeft())
    _paint(name, p, min(rect.width(), rect.height()), color)
    p.restore()
