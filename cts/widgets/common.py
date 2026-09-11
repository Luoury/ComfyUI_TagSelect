# -*- coding: utf-8 -*-
"""通用视觉组件：玻璃卡片、胶囊按钮、开关、提示气泡、滚动区。"""

from __future__ import annotations

from ..qtcompat import QtCore, QtGui, QtWidgets, Signal, Property, text_width
from .. import icons, theme


# ------------------------------------------------------------------ 卡片
class GlassCard(QtWidgets.QFrame):
    """半透明毛玻璃卡片。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None, radius: int = theme.RADIUS_CARD,
                 strong: bool = False, padding: int = 0, alpha: int | None = None,
                 highlight: bool = True, border: bool = True) -> None:
        super().__init__(parent)
        self._radius = radius
        self._strong = strong
        self._alpha = alpha
        self._highlight = highlight
        self._border = border
        self.setAttribute(QtCore.Qt.WA_StyledBackground, False)
        if padding:
            self.setContentsMargins(padding, padding, padding, padding)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        r = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        alpha = self._alpha if self._alpha is not None else (214 if self._strong else 168)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(7, 16, 30, alpha))
        p.drawRoundedRect(r, self._radius, self._radius)
        if self._highlight:
            grad = QtGui.QLinearGradient(r.topLeft(), r.bottomLeft())
            grad.setColorAt(0.0, QtGui.QColor(255, 255, 255, 22))
            grad.setColorAt(1.0, QtGui.QColor(255, 255, 255, 0))
            p.setBrush(QtGui.QBrush(grad))
            p.drawRoundedRect(r, self._radius, self._radius)
        if self._border:
            p.setBrush(QtCore.Qt.NoBrush)
            p.setPen(QtGui.QPen(QtGui.QColor(theme.GLASS_BORDER), 1.0))
            p.drawRoundedRect(r, self._radius, self._radius)
        p.end()


# ------------------------------------------------------------------ 按钮
class PillButton(QtWidgets.QPushButton):
    """自绘胶囊按钮，支持 primary / ghost / danger / soft 四种风格。"""

    def __init__(self, text: str = "", icon_name: str | None = None,
                 variant: str = "ghost", parent: QtWidgets.QWidget | None = None,
                 icon_size: int = 15, scale: float = 1.0, radius: int = 11) -> None:
        super().__init__(text, parent)
        self._variant = variant
        self._icon_name = icon_name
        self._icon_size = icon_size
        self._radius = radius
        self._scale = scale
        self._hover = False
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self._recalc()

    def set_scale(self, scale: float) -> None:
        self._scale = scale
        self._recalc()
        self.update()

    def set_variant(self, variant: str) -> None:
        self._variant = variant
        self.update()

    def set_icon_name(self, name: str | None) -> None:
        self._icon_name = name
        self._recalc()
        self.update()

    def _font(self) -> QtGui.QFont:
        return theme.font(int(round(9.6 * self._scale)), 600)

    def _recalc(self) -> None:
        fm = QtGui.QFontMetrics(self._font())
        w = text_width(fm, self.text()) if self.text() else 0
        if self._icon_name:
            w += int(self._icon_size * self._scale) + (7 if self.text() else 0)
        w += int(26 * self._scale)
        h = max(int(34 * self._scale), fm.height() + int(14 * self._scale))
        self.setFixedSize(max(w, int(34 * self._scale)), h)
        self.update()

    def setText(self, text: str) -> None:  # noqa: N802
        super().setText(text)
        self._recalc()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        r = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        enabled = self.isEnabled()
        v = self._variant

        if v == "primary":
            grad = QtGui.QLinearGradient(r.topLeft(), r.bottomRight())
            c1 = QtGui.QColor(theme.MIKU_BLUE)
            c2 = QtGui.QColor(theme.MIKU_CYAN)
            if self._hover:
                c1, c2 = c1.lighter(118), c2.lighter(112)
            if not enabled:
                c1.setAlpha(90)
                c2.setAlpha(90)
            grad.setColorAt(0.0, c1)
            grad.setColorAt(1.0, c2)
            p.setBrush(QtGui.QBrush(grad))
            p.setPen(QtGui.QPen(QtGui.QColor(190, 250, 255, 130 if enabled else 60), 1.0))
            fg = "#FFFFFF"
        elif v == "danger":
            p.setBrush(QtGui.QColor(255, 92, 118, 210 if self._hover else 150))
            p.setPen(QtGui.QPen(QtGui.QColor(255, 160, 175, 190), 1.0))
            fg = "#FFFFFF"
        elif v == "soft":
            p.setBrush(QtGui.QColor(57, 197, 187, 90 if self._hover else 44))
            p.setPen(QtGui.QPen(QtGui.QColor(theme.MIKU_CYAN_LIGHT if self._hover
                                             else theme.CHIP_BORDER), 1.0))
            fg = "#EAFBFA"
        else:  # ghost
            p.setBrush(QtGui.QColor(255, 255, 255, 48 if self._hover else 24))
            p.setPen(QtGui.QPen(QtGui.QColor(theme.CHIP_BORDER_HOVER if self._hover
                                             else theme.CHIP_BORDER), 1.0))
            fg = theme.TEXT_MAIN

        if not enabled:
            fg = "rgba(220,235,250,0.42)"
        p.drawRoundedRect(r, self._radius, self._radius)

        f = self._font()
        fm = QtGui.QFontMetrics(f)
        icon_w = int(self._icon_size * self._scale) if self._icon_name else 0
        gap = 7 if (self._icon_name and self.text()) else 0
        text_w = text_width(fm, self.text()) if self.text() else 0
        total = icon_w + gap + text_w
        x = r.center().x() - total / 2
        cy = r.center().y()

        if self._icon_name:
            icons.paint_glyph(p, self._icon_name,
                              QtCore.QRectF(x, cy - icon_w / 2, icon_w, icon_w), fg)
            x += icon_w + gap
        if self.text():
            p.setFont(f)
            p.setPen(QtGui.QColor(fg))
            p.drawText(QtCore.QRectF(x, r.top(), text_w + 2, r.height()),
                       QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, self.text())
        p.end()


class IconButton(PillButton):
    """只有一个图标的方形按钮。"""

    def __init__(self, icon_name: str, tooltip: str = "", variant: str = "ghost",
                 parent: QtWidgets.QWidget | None = None, size: int = 32,
                 scale: float = 1.0) -> None:
        super().__init__("", icon_name, variant, parent, icon_size=16, scale=scale,
                         radius=9)
        self._box = int(size * scale)
        self.setFixedSize(self._box, self._box)
        if tooltip:
            self.setToolTip(tooltip)

    def _recalc(self) -> None:
        pass


# ------------------------------------------------------------------ 开关
class ToggleSwitch(QtWidgets.QAbstractButton):
    """带滑动动画的开关。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None, checked: bool = False,
                 on_color: str = theme.MIKU_CYAN, off_color: str = "rgba(255,255,255,0.22)") -> None:
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(checked)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self._on = on_color
        self._off = off_color
        self._pos = 1.0 if checked else 0.0
        self._anim = QtCore.QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        self.setFixedSize(40, 22)
        self.toggled.connect(self._animate)

    def _get_knob(self) -> float:
        return self._pos

    def _set_knob(self, value: float) -> None:
        self._pos = float(value)
        self.update()

    knob = Property(float, _get_knob, _set_knob)

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def sizeHint(self) -> QtCore.QSize:  # noqa: N802
        return QtCore.QSize(40, 22)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        r = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = r.height() / 2
        off = QtGui.QColor(self._off)
        on = QtGui.QColor(self._on)
        col = QtGui.QColor(
            int(off.red() + (on.red() - off.red()) * self._pos),
            int(off.green() + (on.green() - off.green()) * self._pos),
            int(off.blue() + (on.blue() - off.blue()) * self._pos),
            int(off.alpha() + (on.alpha() - off.alpha()) * self._pos),
        )
        if self._pos > 0.05:
            glow = QtGui.QColor(on)
            glow.setAlpha(int(70 * self._pos))
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(glow)
            p.drawRoundedRect(r.adjusted(-1.5, -1.5, 1.5, 1.5), radius + 1.5, radius + 1.5)
        p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 60), 1.0))
        p.setBrush(col)
        p.drawRoundedRect(r, radius, radius)

        d = r.height() - 5
        x = r.left() + 2.5 + (r.width() - d - 5) * self._pos
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(255, 255, 255))
        p.drawEllipse(QtCore.QRectF(x, r.top() + 2.5, d, d))
        p.end()


# ------------------------------------------------------------------ 滚动区
class VScroll(QtWidgets.QScrollArea):
    """透明背景、按宽度自适应高度的竖向滚动区。"""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.viewport().setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")


# ------------------------------------------------------------------ 提示
class Toast(QtWidgets.QWidget):
    """浮在主窗口上的淡入淡出提示条。"""

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        self._text = ""
        self._sub = ""
        self._icon = "check"
        self._font = theme.font(11, 600)
        self._font_s = theme.font(9, 400)
        self._opacity = QtWidgets.QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity)
        self._anim = QtCore.QPropertyAnimation(self._opacity, b"opacity", self)
        self._anim.setDuration(220)
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)
        self.hide()

    def show_message(self, text: str, sub: str = "", icon: str = "check", msec: int = 1900) -> None:
        self._text = text
        self._sub = sub
        self._icon = icon
        fm = QtGui.QFontMetrics(self._font)
        fms = QtGui.QFontMetrics(self._font_s)
        w = max(text_width(fm, text), text_width(fms, sub) if sub else 0) + 78
        h = 54 if sub else 42
        self.resize(int(w), h)
        self._reposition()
        self.show()
        self.raise_()
        self._anim.stop()
        self._anim.setStartValue(self._opacity.opacity())
        self._anim.setEndValue(1.0)
        self._anim.start()
        self._timer.start(msec)

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if parent:
            self.move((parent.width() - self.width()) // 2,
                      max(16, parent.height() - self.height() - 26))

    def _fade_out(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._opacity.opacity())
        self._anim.setEndValue(0.0)
        try:
            self._anim.finished.disconnect()
        except TypeError:
            pass
        self._anim.finished.connect(self.hide)
        self._anim.start()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        r = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(6, 16, 30, 236))
        p.drawRoundedRect(r, 14, 14)
        grad = QtGui.QLinearGradient(r.topLeft(), r.bottomLeft())
        grad.setColorAt(0.0, QtGui.QColor(255, 255, 255, 20))
        grad.setColorAt(1.0, QtGui.QColor(255, 255, 255, 0))
        p.setBrush(QtGui.QBrush(grad))
        p.drawRoundedRect(r, 14, 14)
        p.setBrush(QtCore.Qt.NoBrush)
        p.setPen(QtGui.QPen(QtGui.QColor(57, 197, 187, 170), 1.2))
        p.drawRoundedRect(r, 14, 14)

        box = 24
        icons.paint_glyph(p, self._icon, QtCore.QRectF(16, (self.height() - box) / 2, box, box),
                          theme.MIKU_CYAN_LIGHT)
        x = 16 + box + 13
        if self._sub:
            p.setFont(self._font)
            p.setPen(QtGui.QColor(theme.TEXT_MAIN))
            p.drawText(QtCore.QRectF(x, r.top() + 8, r.right() - x - 12, 20),
                       QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, self._text)
            p.setFont(self._font_s)
            p.setPen(QtGui.QColor(theme.TEXT_DIM))
            p.drawText(QtCore.QRectF(x, r.top() + 27, r.right() - x - 12, 18),
                       QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, self._sub)
        else:
            p.setFont(self._font)
            p.setPen(QtGui.QColor(theme.TEXT_MAIN))
            p.drawText(QtCore.QRectF(x, r.top(), r.right() - x - 12, r.height()),
                       QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, self._text)
        p.end()
