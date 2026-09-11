# -*- coding: utf-8 -*-
"""可切换「单行」与「自动换行」两种模式的流式布局。

分类胶囊默认排成一行（放不下就横向滚动），点「展开」后变成多行换行，
一屏能看到全部分类，不用来回拖。
"""

from __future__ import annotations

from ..qtcompat import QtCore, QtWidgets


class FlowLayout(QtWidgets.QLayout):
    def __init__(self, parent: QtWidgets.QWidget | None = None, margin: int = 0,
                 h_spacing: int = 7, v_spacing: int = 7, wrap: bool = False) -> None:
        super().__init__(parent)
        self._items: list[QtWidgets.QLayoutItem] = []
        self._h = h_spacing
        self._v = v_spacing
        self._wrap = wrap
        self.setContentsMargins(margin, margin, margin, margin)

    def __del__(self) -> None:  # pragma: no cover
        while self._items:
            self._items.pop()

    # ---------------------------------------------------------- 模式
    def set_wrap(self, value: bool) -> None:
        if self._wrap != value:
            self._wrap = bool(value)
            self.invalidate()

    def wrap(self) -> bool:
        return self._wrap

    # ---------------------------------------------------------- 接口
    def addItem(self, item: QtWidgets.QLayoutItem) -> None:  # noqa: N802
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):  # noqa: N802
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int):  # noqa: N802
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):  # noqa: N802
        return QtCore.Qt.Orientations(QtCore.Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:  # noqa: N802
        return self._wrap

    def heightForWidth(self, width: int) -> int:  # noqa: N802
        return self._do_layout(QtCore.QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect: QtCore.QRect) -> None:  # noqa: N802
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self) -> QtCore.QSize:  # noqa: N802
        return self.minimumSize()

    def minimumSize(self) -> QtCore.QSize:  # noqa: N802
        m = self.contentsMargins()
        if not self._items:
            return QtCore.QSize(m.left() + m.right(), m.top() + m.bottom())
        if self._wrap:
            size = QtCore.QSize()
            for item in self._items:
                size = size.expandedTo(item.minimumSize())
        else:
            # 单行：宽度取总和，这样外层滚动区会乖乖出现横向滚动条
            w = sum(item.sizeHint().width() for item in self._items)
            w += self._h * max(0, len(self._items) - 1)
            h = max(item.sizeHint().height() for item in self._items)
            size = QtCore.QSize(w, h)
        size += QtCore.QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    # ---------------------------------------------------------- 布局
    def _do_layout(self, rect: QtCore.QRect, test_only: bool) -> int:
        m = self.contentsMargins()
        area = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x, y, line_h = area.x(), area.y(), 0

        for item in self._items:
            widget = item.widget()
            if widget is not None and widget.isHidden():
                continue
            hint = item.sizeHint()
            next_x = x + hint.width() + self._h
            if self._wrap and x > area.x() and next_x - self._h > area.right():
                x = area.x()
                y += line_h + self._v
                next_x = x + hint.width() + self._h
                line_h = 0
            if not test_only:
                item.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), hint))
            x = next_x
            line_h = max(line_h, hint.height())

        return y + line_h - rect.y() + m.bottom()
