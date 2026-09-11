# -*- coding: utf-8 -*-
"""Qt 绑定兼容层。

优先使用 PySide6（LGPL，发布更友好），找不到时回退到 PyQt5。
整个项目只从这里导入 Qt，别处不要直接 import PyQt5 / PySide6。
"""

from __future__ import annotations

import math

QT_API = ""

try:  # pragma: no cover - 取决于运行环境
    from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore

    QT_API = "PySide6"
    Signal = QtCore.Signal
    Slot = QtCore.Slot
    Property = QtCore.Property
except ImportError:  # pragma: no cover
    from PyQt5 import QtCore, QtGui, QtWidgets  # type: ignore

    QT_API = "PyQt5"
    Signal = QtCore.pyqtSignal
    Slot = QtCore.pyqtSlot
    Property = QtCore.pyqtProperty


def exec_app(app) -> int:
    """QApplication.exec() 在 Qt5 里叫 exec_()。"""
    runner = getattr(app, "exec", None) or getattr(app, "exec_")
    return int(runner())


def text_width(fm: "QtGui.QFontMetrics", text: str) -> int:
    """QFontMetrics.horizontalAdvance 在 Qt5.11 之前叫 width。"""
    fn = getattr(fm, "horizontalAdvance", None)
    if fn is not None:
        return int(fn(text))
    return int(fm.width(text))  # type: ignore[attr-defined]


# PyQt5 没有导出 QtCore.qSin / qCos，这里统一用 math 实现
def qsin(x: float) -> float:
    return math.sin(x)


def qcos(x: float) -> float:
    return math.cos(x)


# QtWidgets.QAction (Qt5) / QtGui.QAction (Qt6)
QAction = getattr(QtWidgets, "QAction", None) or QtGui.QAction

__all__ = [
    "QT_API",
    "QtCore",
    "QtGui",
    "QtWidgets",
    "Signal",
    "Slot",
    "Property",
    "QAction",
    "exec_app",
    "text_width",
    "qsin",
    "qcos",
]
