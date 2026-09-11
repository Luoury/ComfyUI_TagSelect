# -*- coding: utf-8 -*-
"""背景层。

两种模式：
  1. **壁纸**：用户选了一张图，用 KeepAspectRatioByExpanding + 居中裁剪，
     保证任意窗口比例下都铺满、绝不露白。
  2. **默认背景**：没有壁纸时，用 QPainter 现画一张初音配色的星空渐变。
     是程序生成的，没有版权问题；而且它同样会被「背景压暗 / 背景模糊」
     影响，所以那两个滑块在任何情况下都能看到效果。
"""

from __future__ import annotations

import random
from pathlib import Path

from ..qtcompat import QtCore, QtGui, QtWidgets, qcos, qsin


def _blur_pixmap(pm: QtGui.QPixmap, radius: float) -> QtGui.QPixmap:
    """廉价高斯近似：先缩小再平滑放大。"""
    if radius <= 0.5:
        return pm
    factor = max(2.0, radius / 1.6)
    w = max(1, int(pm.width() / factor))
    h = max(1, int(pm.height() / factor))
    small = pm.scaled(w, h, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
    return small.scaled(pm.size(), QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)


_DEFAULT_CACHE: dict[tuple[int, int], QtGui.QPixmap] = {}

# 生成默认背景用的固定种子，保证每次启动长得一样
_STAR_SEED = 20240901


def build_default_background(width: int, height: int) -> QtGui.QPixmap:
    """画一张初音配色的星空渐变背景（结果带缓存）。"""
    key = (width, height)
    cached = _DEFAULT_CACHE.get(key)
    if cached is not None:
        return cached

    pm = QtGui.QPixmap(max(1, width), max(1, height))
    pm.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(pm)
    p.setRenderHint(QtGui.QPainter.Antialiasing, True)
    w, h = pm.width(), pm.height()

    # 1) 底色：深海蓝 → 夜空黑
    base = QtGui.QLinearGradient(0, 0, 0, h)
    base.setColorAt(0.0, QtGui.QColor("#153A6B"))
    base.setColorAt(0.42, QtGui.QColor("#0E2444"))
    base.setColorAt(1.0, QtGui.QColor("#081324"))
    p.fillRect(0, 0, w, h, QtGui.QBrush(base))

    # 2) 几团柔和的光晕：初音青、蓝、以及一点粉
    span = max(w, h)
    glows = [
        (0.16, 0.14, 0.62, "#3D9BFF", 128),
        (0.84, 0.24, 0.52, "#39C5BB", 118),
        (0.62, 0.98, 0.70, "#2472E8", 104),
        (0.04, 0.88, 0.42, "#FF6FA5", 48),
        (0.50, 0.46, 0.34, "#6FE3DA", 38),
    ]
    for cx, cy, r, color, alpha in glows:
        grad = QtGui.QRadialGradient(QtCore.QPointF(cx * w, cy * h), span * r)
        inner = QtGui.QColor(color)
        inner.setAlpha(alpha)
        mid = QtGui.QColor(color)
        mid.setAlpha(alpha // 4)
        outer = QtGui.QColor(color)
        outer.setAlpha(0)
        grad.setColorAt(0.0, inner)
        grad.setColorAt(0.55, mid)
        grad.setColorAt(1.0, outer)
        p.fillRect(0, 0, w, h, QtGui.QBrush(grad))

    # 3) 星点：分辨率无关的归一化坐标，越靠上越亮
    rng = random.Random(_STAR_SEED)
    count = max(70, int(w * h / 8500))
    p.setPen(QtCore.Qt.NoPen)
    for _ in range(count):
        x = rng.random() * w
        y = rng.random() * h
        depth = 1.0 - (y / max(1, h))
        radius = rng.uniform(0.5, 1.7)
        alpha = int(26 + 165 * depth * rng.uniform(0.35, 1.0))
        p.setBrush(QtGui.QColor(214, 240, 255, max(0, min(255, alpha))))
        p.drawEllipse(QtCore.QPointF(x, y), radius, radius)

    # 4) 少量带十字星芒的亮星
    for _ in range(max(3, count // 90)):
        x = rng.random() * w
        y = rng.random() * h * 0.62
        length = rng.uniform(5.0, 12.0)
        pen = QtGui.QPen(QtGui.QColor(200, 245, 255, 150))
        pen.setWidthF(1.1)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(QtCore.QPointF(x - length, y), QtCore.QPointF(x + length, y))
        p.drawLine(QtCore.QPointF(x, y - length), QtCore.QPointF(x, y + length))
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(235, 252, 255, 225))
        p.drawEllipse(QtCore.QPointF(x, y), 1.8, 1.8)

    # 5) 底部压暗，让下半部分的内容更清晰
    shade = QtGui.QLinearGradient(0, h * 0.45, 0, h)
    shade.setColorAt(0.0, QtGui.QColor(3, 8, 16, 0))
    shade.setColorAt(1.0, QtGui.QColor(3, 8, 16, 90))
    p.fillRect(QtCore.QRectF(0, h * 0.45, w, h * 0.55), QtGui.QBrush(shade))

    p.end()
    _DEFAULT_CACHE[key] = pm
    # 缓存别无限增长
    if len(_DEFAULT_CACHE) > 6:
        for old in list(_DEFAULT_CACHE)[:-4]:
            _DEFAULT_CACHE.pop(old, None)
    return pm


class BackgroundWidget(QtWidgets.QWidget):
    """铺满窗口的背景容器。

    - 有壁纸：KeepAspectRatioByExpanding + 居中裁剪，任意比例都无留白
    - 无壁纸：程序生成的星空渐变
    - 两者都支持压暗蒙版与模糊
    """

    def __init__(self, parent: QtWidgets.QWidget | None = None,
                 wallpaper: str | Path | None = None,
                 scrim: float = 0.52, blur: float = 0.0) -> None:
        super().__init__(parent)
        self._source: QtGui.QPixmap | None = None
        self._cache: QtGui.QPixmap | None = None
        self._cache_key: tuple | None = None
        self._scrim = scrim
        self._blur = blur
        self._path: Path | None = None
        self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent, True)
        self.setAutoFillBackground(False)
        if wallpaper:
            self.set_wallpaper(wallpaper)

    # ------------------------------------------------------------ 属性
    def set_wallpaper(self, path: str | Path) -> bool:
        p = Path(path)
        if not p.exists():
            return False
        pm = QtGui.QPixmap(str(p))
        if pm.isNull():
            return False
        self._source = pm
        self._path = p
        self._invalidate()
        return True

    def clear_wallpaper(self) -> None:
        """回到程序生成的默认背景。"""
        self._source = None
        self._path = None
        self._invalidate()

    def has_wallpaper(self) -> bool:
        return self._source is not None

    def wallpaper_path(self) -> Path | None:
        return self._path

    def set_scrim(self, value: float) -> None:
        self._scrim = max(0.0, min(0.9, float(value)))
        self.update()

    def set_blur(self, value: float) -> None:
        self._blur = max(0.0, float(value))
        self._invalidate()

    def _invalidate(self) -> None:
        self._cache = None
        self._cache_key = None
        self.update()

    # ------------------------------------------------------------ 绘制
    def _ensure_cache(self) -> None:
        size = self.size()
        if size.width() <= 0 or size.height() <= 0:
            return
        key = (size.width(), size.height(), round(self._blur, 1), self._path)
        if self._cache is not None and self._cache_key == key:
            return

        if self._source is None:
            base = build_default_background(size.width(), size.height())
            cropped = base
        else:
            # KeepAspectRatioByExpanding 保证覆盖，绝不出现空白
            scaled = self._source.scaled(
                size, QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation
            )
            x = max(0, (scaled.width() - size.width()) // 2)
            y = max(0, (scaled.height() - size.height()) // 2)
            cropped = scaled.copy(x, y, size.width(), size.height())
            if cropped.width() < size.width() or cropped.height() < size.height():
                # 极端比例下的兜底：拉伸补齐，仍然不露白
                cropped = cropped.scaled(size, QtCore.Qt.IgnoreAspectRatio,
                                         QtCore.Qt.SmoothTransformation)

        if self._blur > 0.5:
            cropped = _blur_pixmap(cropped, self._blur)
        self._cache = cropped
        self._cache_key = key

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802
        self._invalidate()
        super().resizeEvent(event)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        self._ensure_cache()
        if self._cache is not None and not self._cache.isNull():
            p.drawPixmap(0, 0, self._cache)
        else:  # 理论上到不了这里，纯兜底
            p.fillRect(self.rect(), QtGui.QColor("#0A1729"))

        # 默认背景本身就是暗色调，压暗系数减半，否则星空会被压没
        scrim = self._scrim if self._source is not None else self._scrim * 0.55
        if scrim > 0.001:
            p.fillRect(self.rect(), QtGui.QColor(4, 12, 24, int(255 * scrim)))

        # 顶部轻微渐隐，让层次更柔和
        top = QtGui.QLinearGradient(0, 0, 0, self.height() * 0.4)
        top.setColorAt(0.0, QtGui.QColor(3, 10, 20, 110))
        top.setColorAt(1.0, QtGui.QColor(3, 10, 20, 0))
        p.fillRect(QtCore.QRectF(0, 0, self.width(), self.height() * 0.4), QtGui.QBrush(top))
        p.end()


class BackgroundFX(QtWidgets.QWidget):
    """铺在壁纸之上、界面之下的动效层。

    只做两件便宜的事：几团缓慢游走的光晕 + 一批向上飘的星尘。
    单独做成一个透明控件是为了**只重绘它自己**，不去连累上层那一堆面板，
    否则每帧重画整个界面会明显吃 CPU。
    """

    FPS_MS = 40

    def __init__(self, parent: QtWidgets.QWidget | None = None,
                 enabled: bool = True, intensity: float = 1.0) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self._enabled = bool(enabled)
        self._intensity = max(0.0, min(1.5, float(intensity)))
        self._t = 0.0
        self._particles: list[tuple[float, float, float, float, float]] = []
        self._built_for = (0, 0)
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(self.FPS_MS)
        self._timer.timeout.connect(self._tick)
        if self._enabled:
            self._timer.start()

    # ------------------------------------------------------------
    def set_enabled(self, value: bool) -> None:
        self._enabled = bool(value)
        if self._enabled:
            self._timer.start()
        else:
            self._timer.stop()
        self.update()

    def is_enabled(self) -> bool:
        return self._enabled

    def set_intensity(self, value: float) -> None:
        self._intensity = max(0.0, min(1.5, float(value)))
        self.update()

    # ------------------------------------------------------------
    def _build_particles(self, w: int, h: int) -> None:
        rng = random.Random(90210)
        n = max(28, int((w * h) / 26000))
        self._particles = [
            (rng.random(), rng.random(), rng.uniform(0.8, 2.6), rng.uniform(0.004, 0.020),
             rng.uniform(0.35, 1.0))
            for _ in range(n)
        ]
        self._built_for = (w, h)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._built_for = (0, 0)

    def _tick(self) -> None:
        if not self.isVisible():
            return
        self._t += self.FPS_MS / 1000.0
        self.update()

    # ------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._enabled or self._intensity <= 0.01:
            return
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0:
            return
        if self._built_for != (w, h):
            self._build_particles(w, h)

        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        short = min(w, h)

        # 1) 缓慢游走的光晕
        p.setPen(QtCore.Qt.NoPen)
        glows = [
            (0.22, 0.28, 0.34, "#39C5BB", 30, 0.13),
            (0.78, 0.62, 0.30, "#2E8BFF", 26, 0.09),
            (0.48, 0.88, 0.26, "#FF6FA5", 16, 0.11),
        ]
        for i, (bx, by, br, color, alpha, speed) in enumerate(glows):
            cx = (bx + 0.05 * qsin(self._t * speed * 3 + i * 2.1)) * w
            cy = (by + 0.04 * qcos(self._t * speed * 2.3 + i * 1.7)) * h
            radius = br * short
            box = QtCore.QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
            grad = QtGui.QRadialGradient(QtCore.QPointF(cx, cy), radius)
            inner = QtGui.QColor(color)
            inner.setAlpha(int(alpha * self._intensity))
            outer = QtGui.QColor(color)
            outer.setAlpha(0)
            grad.setColorAt(0.0, inner)
            grad.setColorAt(1.0, outer)
            p.setBrush(QtGui.QBrush(grad))
            p.drawEllipse(box)

        # 2) 缓缓上浮的星尘
        for px, py, radius, speed, bright in self._particles:
            y = (py - self._t * speed) % 1.0
            x = (px + 0.012 * qsin(self._t * 0.5 + py * 9.0)) % 1.0
            alpha = int(140 * bright * self._intensity * (0.35 + 0.65 * (1.0 - y)))
            if alpha <= 3:
                continue
            p.setBrush(QtGui.QColor(210, 244, 255, min(255, alpha)))
            p.drawEllipse(QtCore.QPointF(x * w, y * h), radius, radius)

        p.end()
