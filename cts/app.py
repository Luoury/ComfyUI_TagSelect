# -*- coding: utf-8 -*-
"""应用启动逻辑。"""

from __future__ import annotations

import sys

from .qtcompat import QtCore, QtGui, QtWidgets, exec_app
from . import theme
from .data_store import CORE_FILE, TagDatabase
from .main_window import APP_TITLE, MainWindow
from .resources import ICON_DIR
from .user_data import UserData

def _prepare_high_dpi() -> None:
    """Qt5 需要在 QApplication 之前声明高 DPI 支持；Qt6 已默认开启。"""
    for attr_name in ("AA_EnableHighDpiScaling", "AA_UseHighDpiPixmaps"):
        attr = getattr(QtCore.Qt, attr_name, None)
        if attr is not None:
            try:
                QtWidgets.QApplication.setAttribute(attr, True)
            except (AttributeError, TypeError):
                pass

def _check_data() -> str | None:
    if not CORE_FILE.exists():
        return (
            "缺少标签数据文件：\n"
            f"{CORE_FILE}\n\n"
            "请在项目目录下运行：\n"
            "    python tools/build_data.py\n"
            "生成数据后再启动本程序。"
        )
    return None

def main(argv: list[str] | None = None) -> int:
    _prepare_high_dpi()
    argv = list(argv if argv is not None else sys.argv)
    app = QtWidgets.QApplication(argv)
    app.setApplicationName(APP_TITLE)
    app.setApplicationDisplayName(APP_TITLE)
    app.setOrganizationName(APP_TITLE)
    app.setStyle("Fusion")

    icon_file = ICON_DIR / "app.ico"
    if not icon_file.exists():
        icon_file = ICON_DIR / "app.png"
    if icon_file.exists():
        app.setWindowIcon(QtGui.QIcon(str(icon_file)))

    problem = _check_data()
    if problem:
        QtWidgets.QMessageBox.critical(None, f"{APP_TITLE} · 数据缺失", problem)
        return 2

    theme.fonts()  # 提前解析一次字体族
    app.setFont(theme.font(10, 400))
    app.setStyleSheet(theme.global_qss())

    db = TagDatabase()
    db.load_core()
    if db.error:
        QtWidgets.QMessageBox.critical(None, f"{APP_TITLE} · 数据错误", db.error)
        return 3

    user = UserData()
    window = MainWindow(db, user)
    window.show()

    # 全量索引在后台线程加载，不阻塞启动
    db.load_full_async()
    return exec_app(app)

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
