# -*- coding: utf-8 -*-
"""背景层：让壁纸始终铺满整个窗口，绝不出现空白。"""

from __future__ import annotations

from pathlib import Path

from ..qtcompat import QtCore, QtGui, QtWidgets


def _blur_pixmap(pm: QtGui.QPixmap, radius: float) -> QtGui.QPixmap:
    """廉价高斯近似：先缩小再平滑放大。"""
    if radius <= 0.5:
        return pm
    factor = max(2.0, radius / 1.6)
    w = max(1, int(pm.width() / factor))
    h = max(1, int(pm.height() / factor))
    small = pm.scaled(w, h, QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)
    return small.scaled(pm.size(), QtCore.Qt.IgnoreAspectRatio, QtCore.Qt.SmoothTransformation)


class BackgroundWidget(QtWidgets.QWidget):
    """铺满窗口的壁纸容器。

    - 使用 KeepAspectRatioByExpanding + 居中裁剪，保证任意窗口比例下都无留白。
    - 支持压暗蒙版与模糊，让前景文字始终可读。
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
        self._cache = None
        self._cache_key = None
        self.update()
        return True

    def wallpaper_path(self) -> Path | None:
        return self._path

    def set_scrim(self, value: float) -> None:
        self._scrim = max(0.0, min(0.9, float(value)))
        self.update()

    def set_blur(self, value: float) -> None:
        self._blur = max(0.0, float(value))
        self._cache = None
        self._cache_key = None
        self.update()

    # ------------------------------------------------------------ 绘制
    def _ensure_cache(self) -> None:
        if self._source is None:
            self._cache = None
            return
        size = self.size()
        key = (size.width(), size.height(), round(self._blur, 1))
        if self._cache is not None and self._cache_key == key:
            return
        if size.width() <= 0 or size.height() <= 0:
            return
        # KeepAspectRatioByExpanding 保证覆盖，绝不出现空白
        scaled = self._source.scaled(
            size, QtCore.Qt.KeepAspectRatioByExpanding, QtCore.Qt.SmoothTransformation
        )
        if self._blur > 0.5:
            scaled = _blur_pixmap(scaled, self._blur)
        # 居中裁剪到窗口大小
        x = max(0, (scaled.width() - size.width()) // 2)
        y = max(0, (scaled.height() - size.height()) // 2)
        cropped = scaled.copy(x, y, size.width(), size.height())
        if cropped.width() < size.width() or cropped.height() < size.height():
            # 极端比例下的兜底：拉伸补齐，仍然不露白
            cropped = cropped.scaled(size, QtCore.Qt.IgnoreAspectRatio,
                                     QtCore.Qt.SmoothTransformation)
        self._cache = cropped
        self._cache_key = key

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802
        self._cache = None
        self._cache_key = None
        super().resizeEvent(event)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        self._ensure_cache()
        if self._cache is not None and not self._cache.isNull():
            p.drawPixmap(0, 0, self._cache)
        else:
            # 没有壁纸时的兜底渐变
            grad = QtGui.QLinearGradient(0, 0, 0, self.height())
            grad.setColorAt(0.0, QtGui.QColor("#0C2036"))
            grad.setColorAt(1.0, QtGui.QColor("#07121F"))
            p.fillRect(self.rect(), QtGui.QBrush(grad))

        if self._scrim > 0.001:
            p.fillRect(self.rect(), QtGui.QColor(4, 12, 24, int(255 * self._scrim)))
        # 顶部/底部轻微渐隐，让层次更柔和
        top = QtGui.QLinearGradient(0, 0, 0, self.height() * 0.4)
        top.setColorAt(0.0, QtGui.QColor(3, 10, 20, 110))
        top.setColorAt(1.0, QtGui.QColor(3, 10, 20, 0))
        p.fillRect(QtCore.QRectF(0, 0, self.width(), self.height() * 0.4), QtGui.QBrush(top))
        p.end()
