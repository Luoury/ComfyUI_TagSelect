#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""开发用截图工具：离屏启动应用，逐页截图，便于校对 UI 布局。

用法：
    QT_QPA_PLATFORM=offscreen python tools/screenshot.py [输出目录]
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cts.qtcompat import QtCore, QtWidgets  # noqa: E402
from cts import theme  # noqa: E402
from cts.data_store import TagDatabase, Tag  # noqa: E402
from cts.main_window import MainWindow  # noqa: E402
from cts.user_data import UserData  # noqa: E402

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / ".shots")
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    app = QtWidgets.QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    theme.fonts()
    app.setFont(theme.font(10, 400))
    app.setStyleSheet(theme.global_qss())

    db = TagDatabase()
    db.load_core()
    if db.error:
        print("DATA ERROR:", db.error)
        return 1
    user = UserData()
    win = MainWindow(db, user)
    win.resize(1400, 880)
    win.show()

    shots: list[tuple[int, str, object]] = []
    state = {"n": 0}

    def snap(name: str) -> None:
        state["n"] += 1
        pix = win.grab()
        path = OUT / f"{state['n']:02d}_{name}.png"
        pix.save(str(path))
        print("saved", path, pix.width(), "x", pix.height())

    def pick(count: int) -> None:
        names = ["1girl", "long_hair", "blue_eyes", "twintails", "school_uniform",
                 "smile", "thighhighs", "hatsune_miku", "looking_at_viewer", "cherry_blossoms"]
        for en in names[:count]:
            tag = db.lookup(en) or Tag(en, "", 0, 0, "all")
            win.toggle_tag(tag)

    def fill_custom() -> None:
        win.custom_page.en_edit.setText("my_custom_tag")
        win.custom_page.zh_edit.setText("我的自定义标签")
        win.custom_page._add()

    steps: list[tuple[int, object]] = [
        (700, lambda: snap("library_hot")),
        (60, lambda: pick(6)),
        (250, lambda: snap("selected_bar")),
        (60, lambda: win._on_page("library")),
        (120, lambda: win.library.pills.select("hair", emit=True)),
        (250, lambda: snap("category_hair")),
        (60, lambda: win.search.setText("长发")),
        (400, lambda: win._flush_search()),
        (250, lambda: snap("search_chinese")),
        (60, lambda: win.search.setText("thigh")),
        (400, lambda: win._flush_search()),
        (250, lambda: snap("search_english")),
        (60, lambda: win.search.clear()),
        (60, lambda: win._on_r18(True)),
        (300, lambda: snap("r18_on")),
        (60, lambda: win._on_r18(False)),
        (60, lambda: win._on_page("presets")),
        (450, lambda: snap("presets")),
        (60, lambda: win._on_page("custom")),
        (300, fill_custom),
        (250, lambda: snap("custom_tags")),
        (60, lambda: win._on_page("settings")),
        (350, lambda: snap("settings")),
        (60, lambda: win._on_page("about")),
        (350, lambda: snap("about")),
        (60, lambda: win._on_page("library")),
        (60, lambda: win.sidebar.set_collapsed(True)),
        (300, lambda: snap("sidebar_collapsed")),
        (60, lambda: win.sidebar.set_collapsed(False)),
        (60, lambda: win._miku_egg()),
        (700, lambda: snap("leek_rain")),
        (400, app.quit),
    ]

    delay = 0
    for ms, fn in steps:
        delay += ms
        QtCore.QTimer.singleShot(delay, fn)

    return app.exec_() if hasattr(app, "exec_") else app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
