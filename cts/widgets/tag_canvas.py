# -*- coding: utf-8 -*-
"""虚拟化标签画布。

分类里可能有几千个标签，为每个标签都建一个 QWidget 会非常慢。
这里用单个自绘控件完成布局与命中测试，只绘制可见区域的胶囊，
可以轻松承载上万个标签。
"""

from __future__ import annotations

from ..qtcompat import QtCore, QtGui, QtWidgets, Signal
from .. import theme
from . import chip_paint

MARGIN = 4
H_GAP = 8
V_GAP = 8


class TagCanvas(QtWidgets.QWidget):
    tagClicked = Signal(object)                    # Tag
    tagRemoveRequested = Signal(object)            # Tag
    tagContextRequested = Signal(object, QtCore.QPoint)  # Tag, 全局坐标
    contentHeightChanged = Signal(int)             # 内容总高度（用于父级自适应）

    def __init__(self, parent: QtWidgets.QWidget | None = None, removable: bool = False,
                 mode: str = "both", show_count: bool = False, scale: float = 1.0,
                 compact: bool = False, empty_hint: str = "") -> None:
        super().__init__(parent)
        self._tags: list = []
        self._selected: set[str] = set()
        self._rects: list[tuple[QtCore.QRect, int]] = []
        self._size_cache: dict[tuple[str, bool], QtCore.QSize] = {}
        self._hover = -1
        self._hover_close = False
        self._content_h = 0
        self._min_height = 0

        self.removable = removable
        self.mode = mode
        self.show_count = show_count
        self.scale = max(0.7, min(1.6, scale))
        self.compact = compact
        self.empty_hint = empty_hint

        self.setMouseTracking(True)
        self.setAttribute(QtCore.Qt.WA_Hover, True)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.setMinimumHeight(60)

    # ------------------------------------------------------------ 数据
    def tags(self) -> list:
        return list(self._tags)

    def set_tags(self, tags: list, selected: set[str] | None = None) -> None:
        self._tags = list(tags)
        if selected is not None:
            self._selected = set(selected)
        self._hover = -1
        self._relayout()
        self.update()

    def set_selected(self, selected: set[str]) -> None:
        if self._selected == selected:
            return
        self._selected = set(selected)
        self.update()

    def set_visual(self, mode: str | None = None, show_count: bool | None = None,
                   scale: float | None = None) -> None:
        changed = False
        if mode is not None and mode != self.mode:
            self.mode = mode
            changed = True
        if show_count is not None and show_count != self.show_count:
            self.show_count = show_count
            changed = True
        if scale is not None and abs(scale - self.scale) > 1e-3:
            self.scale = max(0.7, min(1.6, scale))
            changed = True
        if changed:
            self._size_cache.clear()
            self._relayout()
            self.update()

    def set_min_height(self, height: int) -> None:
        """由外层滚动区告知视口高度，让空状态能在正中显示。"""
        height = max(0, int(height))
        if height != self._min_height:
            self._min_height = height
            self._relayout()

    def content_height(self) -> int:
        """真实内容高度（不含为撑满视口而补的最小高度）。"""
        return self._content_h

    # ------------------------------------------------------------ 布局
    def _size_for(self, tag) -> QtCore.QSize:
        key = (tag.en, bool(tag.custom))
        cached = self._size_cache.get(key)
        if cached is None:
            cached = chip_paint.chip_size(
                tag, self.mode, self.show_count, self.scale,
                selected=False, removable=self.removable, compact=self.compact)
            self._size_cache[key] = cached
        return cached

    def _relayout(self) -> None:
        avail = max(80, self.width() - MARGIN * 2)
        rects: list[tuple[QtCore.QRect, int]] = []
        x, y, line_h = MARGIN, MARGIN, 0
        for i, tag in enumerate(self._tags):
            size = self._size_for(tag)
            if x > MARGIN and x + size.width() > avail + MARGIN:
                x = MARGIN
                y += line_h + V_GAP
                line_h = 0
            rect = QtCore.QRect(x, y, size.width(), size.height())
            rects.append((rect, i))
            x += size.width() + H_GAP
            line_h = max(line_h, size.height())
        self._rects = rects
        previous = self._content_h
        self._content_h = y + line_h + MARGIN
        target = max(self._content_h, self._min_height, 1)
        if self.height() != target:
            self.setFixedHeight(target)
        self.update()
        if previous != self._content_h:
            self.contentHeightChanged.emit(self._content_h)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if event.size().width() != event.oldSize().width():
            self._relayout()

    def sizeHint(self) -> QtCore.QSize:  # noqa: N802
        return QtCore.QSize(self.width(), max(self._content_h, 60))

    # ------------------------------------------------------------ 命中
    def _hit(self, pos: QtCore.QPoint):
        x, y = pos.x(), pos.y()
        for rect, idx in self._rects:
            if rect.top() <= y <= rect.bottom() and rect.left() <= x <= rect.right():
                return idx, rect
        return -1, QtCore.QRect()

    def _close_rect(self, rect: QtCore.QRect) -> QtCore.QRect:
        if not self.removable:
            return QtCore.QRect()
        s = int(13 * self.scale)
        return QtCore.QRect(int(rect.right() - s - 7 * self.scale),
                            int(rect.center().y() - s / 2), s, s)

    # ------------------------------------------------------------ 事件
    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        idx, rect = self._hit(event.pos())
        close = bool(self.removable and idx >= 0 and self._close_rect(rect).contains(event.pos()))
        if idx != self._hover or close != self._hover_close:
            self._hover = idx
            self._hover_close = close
            self.setCursor(QtCore.Qt.PointingHandCursor if idx >= 0 else QtCore.Qt.ArrowCursor)
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        if self._hover != -1:
            self._hover = -1
            self._hover_close = False
            self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.LeftButton:
            idx, rect = self._hit(event.pos())
            if idx >= 0:
                tag = self._tags[idx]
                if self.removable and self._close_rect(rect).contains(event.pos()):
                    self.tagRemoveRequested.emit(tag)
                else:
                    self.tagClicked.emit(tag)
        elif event.button() == QtCore.Qt.RightButton:
            idx, _ = self._hit(event.pos())
            if idx >= 0:
                self.tagContextRequested.emit(self._tags[idx], event.globalPos())
        super().mouseReleaseEvent(event)

    def event(self, evt):  # noqa: N802
        if evt.type() == QtCore.QEvent.ToolTip:
            idx, _ = self._hit(evt.pos())
            if idx >= 0:
                QtWidgets.QToolTip.showText(evt.globalPos(),
                                            chip_paint.chip_tooltip(self._tags[idx]), self)
            else:
                QtWidgets.QToolTip.hideText()
            return True
        return super().event(evt)

    def _scroll_delta(self, event) -> int:
        """把滚轮事件交给外层滚动区（画布自身不滚动）。"""
        area = self.parent()
        while area is not None and not isinstance(area, QtWidgets.QAbstractScrollArea):
            area = area.parent()
        if area is None:
            return 0
        bar = area.verticalScrollBar()
        steps = event.angleDelta().y() / 120.0
        bar.setValue(int(bar.value() - steps * (bar.singleStep() * 3)))
        return 1

    def wheelEvent(self, event) -> None:  # noqa: N802
        if not self._scroll_delta(event):
            super().wheelEvent(event)

    # ------------------------------------------------------------ 绘制
    def paintEvent(self, event) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        if not self._tags:
            if self.empty_hint:
                p.setFont(theme.font(11, 400))
                p.setPen(QtGui.QColor(theme.TEXT_FAINT))
                p.drawText(self.rect(), QtCore.Qt.AlignCenter, self.empty_hint)
            p.end()
            return

        visible = event.rect()
        # 只绘制可见行的胶囊
        for rect, idx in self._rects:
            if rect.bottom() < visible.top() - V_GAP:
                continue
            if rect.top() > visible.bottom() + V_GAP:
                continue
            tag = self._tags[idx]
            chip_paint.paint_chip(
                p, QtCore.QRectF(rect), tag,
                selected=tag.en in self._selected,
                hover=(idx == self._hover),
                hover_close=(idx == self._hover and self._hover_close),
                mode=self.mode, show_count=self.show_count, scale=self.scale,
                removable=self.removable, compact=self.compact,
                dirty=bool(getattr(tag, "custom", False)),
            )
        p.end()


class TagScroll(QtWidgets.QScrollArea):
    """把 TagCanvas 包进滚动区，并转发常用操作。"""

    tagClicked = Signal(object)
    tagRemoveRequested = Signal(object)
    tagContextRequested = Signal(object, QtCore.QPoint)

    def __init__(self, parent: QtWidgets.QWidget | None = None, removable: bool = False,
                 mode: str = "both", show_count: bool = False, scale: float = 1.0,
                 compact: bool = False, empty_hint: str = "") -> None:
        super().__init__(parent)
        self.canvas = TagCanvas(self, removable=removable, mode=mode, show_count=show_count,
                                scale=scale, compact=compact, empty_hint=empty_hint)
        self.setWidget(self.canvas)
        self.setWidgetResizable(True)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.viewport().setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")
        self.canvas.tagClicked.connect(self.tagClicked)
        self.canvas.tagRemoveRequested.connect(self.tagRemoveRequested)
        self.canvas.tagContextRequested.connect(self.tagContextRequested)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.canvas.set_min_height(self.viewport().height())

    def set_tags(self, tags: list, selected: set[str] | None = None) -> None:
        self.canvas.set_tags(tags, selected)
        self.canvas.set_min_height(self.viewport().height())
        self.verticalScrollBar().setValue(0)

    def set_selected(self, selected: set[str]) -> None:
        self.canvas.set_selected(selected)

    def tags(self) -> list:
        return self.canvas.tags()
