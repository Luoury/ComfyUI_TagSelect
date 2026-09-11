# -*- coding: utf-8 -*-
"""彩蛋：点一下侧边栏的小未来，就会下一场大葱雨。"""

from __future__ import annotations

import random

from ..qtcompat import QtCore, QtGui, QtWidgets
from .. import miku_art


class _Leek:
    __slots__ = ("x", "y", "vy", "vx", "angle", "spin", "size", "alpha")

    def __init__(self, w: int, h: int) -> None:
        self.size = random.uniform(26, 54)
        self.x = random.uniform(-40, w + 40)
        # 一部分从屏幕上方落下，一部分直接出现在画面里，点击后立刻有反馈
        if random.random() < 0.45:
            self.y = random.uniform(-self.size, h * 0.75)
        else:
            self.y = random.uniform(-h * 0.9, -self.size)
        self.vy = random.uniform(90, 260)
        self.vx = random.uniform(-28, 28)
        self.angle = random.uniform(-40, 40)
        self.spin = random.uniform(-55, 55)
        self.alpha = random.uniform(0.75, 1.0)


class LeekRain(QtWidgets.QWidget):
    """覆盖整个主窗口的飘落动画层。"""

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self._leeks: list[_Leek] = []
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._life = 0
        self._last = QtCore.QElapsedTimer()
        self.hide()

    def start(self, duration_ms: int = 7000, count: int = 30) -> None:
        self.setGeometry(self.parentWidget().rect())
        self._leeks = [_Leek(self.width(), self.height()) for _ in range(count)]
        self._life = duration_ms
        self._last.restart()
        self.show()
        self.raise_()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()
        self._leeks.clear()
        self.hide()

    def _tick(self) -> None:
        dt = min(0.05, self._last.restart() / 1000.0)
        self._life -= dt * 1000.0
        h = self.height()
        for leek in self._leeks:
            leek.y += leek.vy * dt
            leek.x += leek.vx * dt
            leek.angle += leek.spin * dt
            if leek.y > h + 60:
                leek.y = random.uniform(-160, -40)
                leek.x = random.uniform(-40, max(1, self.width()) + 40)
        if self._life <= 0:
            self.stop()
        else:
            self.update()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.setGeometry(self.parentWidget().rect())

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        for leek in self._leeks:
            p.save()
            p.setOpacity(leek.alpha)
            p.translate(leek.x, leek.y)
            p.rotate(leek.angle)
            miku_art.draw_leek(p, QtCore.QRectF(-leek.size / 2, -leek.size / 2,
                                                leek.size, leek.size))
            p.restore()
        p.end()
