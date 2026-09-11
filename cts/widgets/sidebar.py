# -*- coding: utf-8 -*-
"""左侧侧边栏：Logo、页面导航，以及 Q 版未来彩蛋。"""

from __future__ import annotations

import random

from ..qtcompat import QtCore, QtGui, QtWidgets, Signal, qsin
from .. import icons, miku_art, theme

EXPANDED_W = 214
COLLAPSED_W = 70

PAGES = [
    ("library", "标签库", "grid", "浏览与搜索所有标签"),
    ("presets", "预设", "star", "常驻预设与我的预设"),
    ("custom", "自定义标签", "pencil", "添加你自己的标签"),
    ("settings", "设置", "settings", "壁纸、复制格式、R18 等"),
    ("about", "关于", "info", "使用说明与彩蛋"),
]


class NavItem(QtWidgets.QWidget):
    activated = Signal(str)

    def __init__(self, key: str, label: str, icon_name: str, tip: str,
                 parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.key = key
        self.label = label
        self.icon_name = icon_name
        self._active = False
        self._hover = False
        self._collapsed = False
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip(f"{label} · {tip}")
        self.setFixedHeight(42)

    def set_active(self, value: bool) -> None:
        if self._active != value:
            self._active = value
            self.update()

    def set_collapsed(self, value: bool) -> None:
        self._collapsed = value
        self.update()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.LeftButton and self.rect().contains(event.pos()):
            self.activated.emit(self.key)

    def sizeHint(self) -> QtCore.QSize:  # noqa: N802
        return QtCore.QSize(COLLAPSED_W if self._collapsed else EXPANDED_W, 42)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        r = QtCore.QRectF(self.rect()).adjusted(8, 3, -8, -3)

        if self._active:
            grad = QtGui.QLinearGradient(r.topLeft(), r.bottomRight())
            grad.setColorAt(0.0, QtGui.QColor(46, 139, 255, 150))
            grad.setColorAt(1.0, QtGui.QColor(57, 197, 187, 120))
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QBrush(grad))
            p.drawRoundedRect(r, 11, 11)
            p.setBrush(QtGui.QColor(theme.MIKU_CYAN_LIGHT))
            p.drawRoundedRect(QtCore.QRectF(r.left(), r.top() + 7, 3, r.height() - 14), 1.5, 1.5)
        elif self._hover:
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QColor(255, 255, 255, 30))
            p.drawRoundedRect(r, 11, 11)

        color = "#FFFFFF" if self._active else (theme.TEXT_MAIN if self._hover else theme.TEXT_DIM)
        box = 19
        cx = r.left() + (r.width() - box) / 2 if self._collapsed else r.left() + 13
        icons.paint_glyph(p, self.icon_name, QtCore.QRectF(cx, r.center().y() - box / 2, box, box), color)

        if not self._collapsed:
            p.setFont(theme.font(10, 600 if self._active else 500))
            p.setPen(QtGui.QColor(color))
            p.drawText(QtCore.QRectF(cx + box + 11, r.top(), r.right() - cx - box - 14, r.height()),
                       QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, self.label)
        p.end()


class MikuChibi(QtWidgets.QWidget):
    """侧边栏底部的小未来，会眨眼，点一下会下葱雨。"""

    clicked = Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(64, 64)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setToolTip("ミクだよ♪  点一下试试～")
        self._blink = 0.0
        self._sway = 0.0
        self._t = 0.0
        self._hover = False

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(60)
        self._next_blink = random.randint(40, 110)

    def _tick(self) -> None:
        self._t += 1
        self._sway = 0.6 * qsin(self._t * 0.06)
        if self._blink > 0:
            self._blink = max(0.0, self._blink - 0.18)
        else:
            self._next_blink -= 1
            if self._next_blink <= 0:
                self._blink = 1.0
                self._next_blink = random.randint(50, 150)
                self._sway = 0.0
        self.update()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.LeftButton and self.rect().contains(event.pos()):
            self.clicked.emit()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        if self._hover:
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QColor(57, 197, 187, 46))
            p.drawEllipse(self.rect().adjusted(2, 2, -2, -2))
        miku_art.draw_chibi(p, QtCore.QRectF(4, 2, self.width() - 8, self.height() - 4),
                            blink=self._blink, sway=self._sway)
        p.end()


class Sidebar(QtWidgets.QWidget):
    pageChanged = Signal(str)
    collapseToggled = Signal(bool)
    mikuClicked = Signal()

    def __init__(self, parent: QtWidgets.QWidget | None = None, collapsed: bool = False) -> None:
        super().__init__(parent)
        self._collapsed = collapsed
        self._current = "library"
        self._logo_t = 0.0

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 14, 0, 12)
        layout.setSpacing(2)

        # ---- Logo 区
        self.logo_row = QtWidgets.QWidget(self)
        logo_lay = QtWidgets.QHBoxLayout(self.logo_row)
        logo_lay.setContentsMargins(16, 0, 12, 0)
        logo_lay.setSpacing(10)
        self.logo = _LogoMark(self.logo_row)
        self.title_box = QtWidgets.QWidget(self.logo_row)
        tb = QtWidgets.QVBoxLayout(self.title_box)
        tb.setContentsMargins(0, 0, 0, 0)
        tb.setSpacing(0)
        self.title = QtWidgets.QLabel("TagSelect", self.title_box)
        self.title.setFont(theme.font(12, 700))
        self.title.setStyleSheet(f"color: {theme.TEXT_MAIN}; background: transparent;")
        self.subtitle = QtWidgets.QLabel("39 · MIKU THEME", self.title_box)
        self.subtitle.setFont(theme.font(7, 500))
        self.subtitle.setStyleSheet(f"color: {theme.MIKU_CYAN}; background: transparent;")
        tb.addWidget(self.title)
        tb.addWidget(self.subtitle)
        logo_lay.addWidget(self.logo)
        logo_lay.addWidget(self.title_box)
        logo_lay.addStretch(1)
        self.logo_row.setFixedHeight(52)
        layout.addWidget(self.logo_row)

        layout.addSpacing(8)

        # ---- 导航
        self.items: dict[str, NavItem] = {}
        for key, label, icon_name, tip in PAGES:
            item = NavItem(key, label, icon_name, tip, self)
            item.activated.connect(self._on_nav)
            layout.addWidget(item, 0, QtCore.Qt.AlignHCenter)
            self.items[key] = item

        layout.addStretch(1)

        # ---- 彩蛋区
        self.corner = QtWidgets.QWidget(self)
        corner_lay = QtWidgets.QVBoxLayout(self.corner)
        corner_lay.setContentsMargins(0, 0, 0, 0)
        corner_lay.setSpacing(4)
        self.badge = QtWidgets.QLabel("39", self.corner)
        self.badge.setAlignment(QtCore.Qt.AlignCenter)
        self.badge.setFont(theme.font(8, 700))
        self.badge.setFixedHeight(20)
        self.badge.setStyleSheet(
            "color: #07131F; background: rgba(57,197,187,0.92);"
            "border-radius: 10px; padding: 0 8px;")
        self.badge.setToolTip("39 = Miku（ミク）的谐音，也是初音未来的应援数字～")
        row = QtWidgets.QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        row.addWidget(self.badge)
        row.addStretch(1)
        corner_lay.addLayout(row)

        self.chibi = MikuChibi(self.corner)
        self.chibi.clicked.connect(self.mikuClicked)
        crow = QtWidgets.QHBoxLayout()
        crow.setContentsMargins(0, 0, 0, 0)
        crow.addStretch(1)
        crow.addWidget(self.chibi)
        crow.addStretch(1)
        corner_lay.addLayout(crow)
        layout.addWidget(self.corner)

        # ---- 折叠按钮
        self.collapse_btn = QtWidgets.QToolButton(self)
        self.collapse_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.collapse_btn.setAutoRaise(True)
        self.collapse_btn.setIconSize(QtCore.QSize(16, 16))
        self.collapse_btn.clicked.connect(lambda: self.set_collapsed(not self._collapsed))
        self.collapse_btn.setStyleSheet(
            "QToolButton { background: transparent; border: none; padding: 6px; border-radius: 8px; }"
            "QToolButton:hover { background: rgba(255,255,255,0.10); }")
        crow2 = QtWidgets.QHBoxLayout()
        crow2.setContentsMargins(0, 6, 0, 0)
        crow2.addStretch(1)
        crow2.addWidget(self.collapse_btn)
        crow2.addStretch(1)
        layout.addLayout(crow2)

        self.set_collapsed(collapsed, emit=False)
        self._logo_timer = QtCore.QTimer(self)
        self._logo_timer.timeout.connect(self._pulse)
        self._logo_timer.start(50)

    # ------------------------------------------------------------
    def _pulse(self) -> None:
        self._logo_t += 0.08
        self.logo.set_phase(self._logo_t)

    def _on_nav(self, key: str) -> None:
        self.set_page(key)
        self.pageChanged.emit(key)

    def set_page(self, key: str) -> None:
        self._current = key
        for k, item in self.items.items():
            item.set_active(k == key)

    def current_page(self) -> str:
        return self._current

    def is_collapsed(self) -> bool:
        return self._collapsed

    def set_collapsed(self, value: bool, emit: bool = True) -> None:
        self._collapsed = bool(value)
        for item in self.items.values():
            item.set_collapsed(self._collapsed)
        self.title_box.setVisible(not self._collapsed)
        self.corner.setVisible(not self._collapsed)
        icon = "chevron_right" if self._collapsed else "chevron_left"
        self.collapse_btn.setIcon(icons.icon(icon, 16, theme.TEXT_DIM))
        self.collapse_btn.setToolTip("展开侧边栏" if self._collapsed else "收起侧边栏")
        self.setFixedWidth(COLLAPSED_W if self._collapsed else EXPANDED_W)
        if emit:
            self.collapseToggled.emit(self._collapsed)

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        r = QtCore.QRectF(self.rect())
        path = QtGui.QPainterPath()
        rad = 18
        path.moveTo(r.left(), r.top())
        path.lineTo(r.right() - rad, r.top())
        path.quadTo(r.right(), r.top(), r.right(), r.top() + rad)
        path.lineTo(r.right(), r.bottom() - rad)
        path.quadTo(r.right(), r.bottom(), r.right() - rad, r.bottom())
        path.lineTo(r.left(), r.bottom())
        path.closeSubpath()
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(6, 14, 27, 205))
        p.drawPath(path)
        grad = QtGui.QLinearGradient(r.topLeft(), r.bottomLeft())
        grad.setColorAt(0.0, QtGui.QColor(57, 197, 187, 26))
        grad.setColorAt(0.5, QtGui.QColor(57, 197, 187, 0))
        grad.setColorAt(1.0, QtGui.QColor(46, 139, 255, 22))
        p.setBrush(QtGui.QBrush(grad))
        p.drawPath(path)
        p.setBrush(QtCore.Qt.NoBrush)
        p.setPen(QtGui.QPen(QtGui.QColor(120, 210, 255, 46), 1.0))
        path2 = QtGui.QPainterPath()
        path2.moveTo(r.right() - 0.5, r.top() + rad)
        path2.lineTo(r.right() - 0.5, r.bottom() - rad)
        p.drawPath(path2)
        p.end()


class _LogoMark(QtWidgets.QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self._phase = 0.0

    def set_phase(self, value: float) -> None:
        self._phase = value
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        miku_art.draw_logo(p, QtCore.QRectF(0, 0, self.width(), self.height()))
        # 音符随节奏微微起伏
        p.end()
