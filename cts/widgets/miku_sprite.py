# -*- coding: utf-8 -*-
"""MIKU 立绘组件。

三种状态对应三张图（assets/miku/）：
  idle —— 初始状态
  leek —— 咬着大葱
  yell —— 眯眼大叫

点击时会有「小黄鸭」式的挤压 + 回弹：按下瞬间纵向压扁、横向拉宽，
松开后用 OutElastic 回弹并轻微过冲。下葱雨期间在 leek / yell 之间来回切换。
"""

from __future__ import annotations

from ..qtcompat import QtCore, QtGui, QtWidgets, Signal, Property, qsin
from .. import resources

_PIXMAP_CACHE: dict[str, QtGui.QPixmap] = {}


def _sprite_pixmap(state: str) -> QtGui.QPixmap:
    """按需加载并缓存立绘。"""
    if state not in _PIXMAP_CACHE:
        path = resources.miku_sprite(state)
        pm = QtGui.QPixmap(str(path)) if path else QtGui.QPixmap()
        _PIXMAP_CACHE[state] = pm
    return _PIXMAP_CACHE[state]


class MikuSprite(QtWidgets.QWidget):
    """可点击的 MIKU 立绘，自带挤压回弹动效。"""

    clicked = Signal()

    # 按下时压到多扁（越小越夸张）
    SQUASH_MIN = 0.62
    # 横向补偿比例：压扁多少就横向撑开多少
    SQUASH_SPREAD = 0.55

    def __init__(self, parent: QtWidgets.QWidget | None = None, size: int = 72,
                 state: str = "idle", animated: bool = True) -> None:
        super().__init__(parent)
        self._state = state
        self._squash = 1.0
        self._hover = False
        self._animated = animated
        self._breath = 0.0
        self._t = 0.0
        self.setFixedSize(size, size)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip("ミクだよ♪  点一下试试～")

        self._anim = QtCore.QPropertyAnimation(self, b"squash", self)
        self._anim.setDuration(620)
        self._anim.setEasingCurve(QtCore.QEasingCurve.OutElastic)

        self._rain_timer = QtCore.QTimer(self)
        self._rain_timer.setInterval(300)
        self._rain_timer.timeout.connect(self._rain_tick)
        self._rain_left = 0

        self._idle_timer = QtCore.QTimer(self)
        self._idle_timer.timeout.connect(self._idle_tick)
        if animated:
            self._idle_timer.start(60)

    # ------------------------------------------------------------ 属性
    def _get_squash(self) -> float:
        return self._squash

    def _set_squash(self, value: float) -> None:
        self._squash = float(value)
        self.update()

    squash = Property(float, _get_squash, _set_squash)

    def state(self) -> str:
        return self._state

    def set_state(self, state: str) -> None:
        if state != self._state:
            self._state = state
            self.update()

    def set_animated(self, value: bool) -> None:
        self._animated = bool(value)
        if self._animated:
            if not self._idle_timer.isActive():
                self._idle_timer.start(60)
        else:
            self._idle_timer.stop()
            self._breath = 0.0
            self.update()

    # ------------------------------------------------------------ 动效
    def _idle_tick(self) -> None:
        self._t += 0.06
        # 很轻微的呼吸感，避免一直静止
        self._breath = qsin(self._t) * 0.012
        self.update()

    def bounce(self) -> None:
        """挤压 + 回弹。"""
        self._anim.stop()
        self._squash = self.SQUASH_MIN
        self.update()
        self._anim.setStartValue(self.SQUASH_MIN)
        self._anim.setEndValue(1.0)
        self._anim.start()

    def play_rain(self, duration_ms: int = 7200) -> None:
        """下葱雨期间在 leek / yell 两张图之间切换。"""
        self.bounce()
        self._rain_left = int(duration_ms)
        self._rain_timer.start()

    def _rain_tick(self) -> None:
        self._rain_left -= self._rain_timer.interval()
        if self._rain_left <= 0:
            self._rain_timer.stop()
            self.set_state("idle")
            return
        self.set_state("yell" if self._state == "leek" else "leek")

    # ------------------------------------------------------------ 事件
    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.LeftButton:
            # 立刻压扁，给即时反馈
            self._anim.stop()
            self._squash = self.SQUASH_MIN
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.LeftButton and self.rect().contains(event.pos()):
            self.bounce()
            self.clicked.emit()
        else:
            self.bounce()

    # ------------------------------------------------------------ 绘制
    def paintEvent(self, event) -> None:  # noqa: N802
        pm = _sprite_pixmap(self._state)
        if pm.isNull():
            return
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)

        w, h = self.width(), self.height()
        scale_y = self._squash + (self._breath if self._animated else 0.0)
        scale_x = 1.0 + (1.0 - self._squash) * self.SQUASH_SPREAD

        # 以底边中心为锚点缩放，视觉上像被按在地上压扁
        draw_w = w * scale_x
        draw_h = h * scale_y
        x = (w - draw_w) / 2
        y = h - draw_h

        if self._hover:
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QColor(57, 197, 187, 42))
            p.drawEllipse(QtCore.QRectF(x - 3, y - 3, draw_w + 6, draw_h + 6))

        p.drawPixmap(QtCore.QRectF(x, y, draw_w, draw_h), pm,
                     QtCore.QRectF(0, 0, pm.width(), pm.height()))
        p.end()
