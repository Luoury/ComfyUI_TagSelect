# -*- coding: utf-8 -*-
"""主窗口：搜索栏 + 已选标签框 + 分类标签网格 + 左侧页面。"""

from __future__ import annotations

from .qtcompat import QtCore, QtGui, QtWidgets, Signal, text_width
from . import data_store, icons, resources, theme
from .data_store import Tag, TagDatabase
from .user_data import UserData
from .widgets import pages as pages_mod
from .widgets.background import BackgroundWidget
from .widgets.common import GlassCard, IconButton, PillButton, ToggleSwitch, Toast, VScroll
from .widgets.leek_rain import LeekRain
from .widgets.sidebar import Sidebar
from .widgets.tag_canvas import TagScroll

APP_TITLE = "ComfyUI_TagSelect"


# ==================================================================== 工具
def format_tags(names, fmt: str) -> str:
    """按用户选择的格式拼接标签。"""
    items = [str(n) for n in names if str(n).strip()]
    if not items:
        return ""
    if fmt == "comma":
        return ",".join(items)
    if fmt == "comma_space":
        return ", ".join(items)
    if fmt == "space":
        return " ".join(items)
    if fmt == "newline":
        return "\n".join(items)
    if fmt == "brace":
        return ",".join("{%s}" % n for n in items)
    return ",".join(items)


def _clamp(value, low, high):
    return max(low, min(high, value))


# ==================================================================== 分类胶囊
class _CatPill(QtWidgets.QAbstractButton):
    def __init__(self, cid: str, name: str, count: int = 0, parent=None) -> None:
        super().__init__(parent)
        self.cid = cid
        self._name = name
        self._count = count
        self._active = False
        self._hover = False
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self._recalc()

    def set_active(self, value: bool) -> None:
        if self._active != value:
            self._active = value
            self.update()

    def _recalc(self) -> None:
        f = theme.font(9.2, 600)
        fm = QtGui.QFontMetrics(f)
        w = text_width(fm, self._name) + 24
        if self._count:
            w += text_width(QtGui.QFontMetrics(theme.font(7.8, 400)), str(self._count)) + 8
        self.setFixedSize(w, max(28, fm.height() + 12))

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        r = QtCore.QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        if self._active:
            grad = QtGui.QLinearGradient(r.topLeft(), r.bottomRight())
            grad.setColorAt(0.0, QtGui.QColor(theme.MIKU_BLUE))
            grad.setColorAt(1.0, QtGui.QColor(theme.MIKU_CYAN))
            p.setBrush(QtGui.QBrush(grad))
            p.setPen(QtGui.QPen(QtGui.QColor(200, 250, 255, 150), 1.0))
        else:
            p.setBrush(QtGui.QColor(255, 255, 255, 40 if self._hover else 18))
            p.setPen(QtGui.QPen(QtGui.QColor(theme.CHIP_BORDER_HOVER if self._hover
                                             else theme.CHIP_BORDER), 1.0))
        p.drawRoundedRect(r, 13, 13)
        f = theme.font(9.2, 600)
        fm = QtGui.QFontMetrics(f)
        p.setFont(f)
        p.setPen(QtGui.QColor("#FFFFFF" if self._active else theme.TEXT_MAIN))
        x = r.left() + 12
        p.drawText(QtCore.QRectF(x, r.top(), r.width() - 24, r.height()),
                   QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft, self._name)
        if self._count:
            p.setFont(theme.font(7.8, 400))
            p.setPen(QtGui.QColor("rgba(255,255,255,0.78)" if self._active else theme.TEXT_FAINT))
            p.drawText(QtCore.QRectF(r.left(), r.top(), r.width() - 11, r.height()),
                       QtCore.Qt.AlignVCenter | QtCore.Qt.AlignRight, str(self._count))
        p.end()


class CategoryPills(QtWidgets.QScrollArea):
    changed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # 分类有 20 多个，一屏放不下，保留一条细横向滚动条作为可滚动的提示
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setFixedHeight(50)
        self.viewport().setAutoFillBackground(False)
        self.setStyleSheet("background: transparent;")
        self._holder = QtWidgets.QWidget()
        self._holder.setStyleSheet("background: transparent;")
        self._lay = QtWidgets.QHBoxLayout(self._holder)
        self._lay.setContentsMargins(0, 2, 0, 6)
        self._lay.setSpacing(7)
        self._lay.addStretch(1)
        self.setWidget(self._holder)
        self._pills: dict[str, _CatPill] = {}
        self._current = "all"

    def wheelEvent(self, event) -> None:  # noqa: N802
        bar = self.horizontalScrollBar()
        bar.setValue(bar.value() - event.angleDelta().y())

    def set_categories(self, items: list[tuple[str, str, int]]) -> None:
        while self._lay.count() > 1:
            item = self._lay.takeAt(0)
            w = item.widget()
            if w is not None:
                # 必须先解除父子关系并隐藏，否则旧胶囊会保留几何位置继续绘制
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self._pills.clear()
        for cid, name, count in items:
            pill = _CatPill(cid, name, count, self._holder)
            pill.clicked.connect(lambda _=False, c=cid: self.select(c))
            self._lay.insertWidget(self._lay.count() - 1, pill)
            self._pills[cid] = pill
        self.horizontalScrollBar().setValue(0)
        self.select(self._current if self._current in self._pills else "all", emit=False)

    def select(self, cid: str, emit: bool = True) -> None:
        if cid not in self._pills:
            cid = "all"
        self._current = cid
        for key, pill in self._pills.items():
            pill.set_active(key == cid)
        # 把当前分类滚进可视范围（R18 在最右边，不然用户看不到它被选中）
        QtCore.QTimer.singleShot(0, lambda: self.ensureWidgetVisible(self._pills[cid], 24, 0))
        if emit:
            self.changed.emit(cid)

    def current(self) -> str:
        return self._current


# ==================================================================== 已选标签框
class SelectedBar(GlassCard):
    copyRequested = Signal()
    exportRequested = Signal()
    saveRequested = Signal()
    clearRequested = Signal()
    changed = Signal()

    MIN_H = 46
    MAX_H = 152

    def __init__(self, parent=None, user: UserData | None = None, scale: float = 1.0) -> None:
        super().__init__(parent, radius=17, strong=True)
        self.user = user
        self._scale = scale
        self._tags: list[Tag] = []
        self._index: dict[str, Tag] = {}

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(16, 11, 14, 12)
        lay.setSpacing(8)

        head = QtWidgets.QHBoxLayout()
        head.setSpacing(8)
        self.title = QtWidgets.QLabel("已选标签", self)
        self.title.setFont(theme.font(int(round(10.4 * scale)), 700))
        self.title.setStyleSheet(f"color: {theme.TEXT_MAIN}; background: transparent;")
        head.addWidget(self.title)

        self.count = QtWidgets.QLabel("0", self)
        self.count.setAlignment(QtCore.Qt.AlignCenter)
        self.count.setFont(theme.font(int(round(8.4 * scale)), 700))
        self.count.setMinimumWidth(26)
        self.count.setFixedHeight(19)
        self.count.setStyleSheet(
            "color: #07131F; background: rgba(57,197,187,0.95);"
            "border-radius: 9px; padding: 0 8px;")
        head.addWidget(self.count)

        self.hint = QtWidgets.QLabel("单击下方标签加入 · 再单击移出", self)
        self.hint.setFont(theme.font(int(round(8.6 * scale)), 400))
        self.hint.setStyleSheet(f"color: {theme.TEXT_FAINT}; background: transparent;")
        head.addWidget(self.hint)
        head.addStretch(1)

        self.btn_save = PillButton("存为预设", "save", "ghost", self, scale=0.92 * scale)
        self.btn_save.setToolTip("把当前已选标签保存成预设")
        self.btn_save.clicked.connect(self.saveRequested)
        head.addWidget(self.btn_save)

        self.btn_export = IconButton("download", "导出为 txt 文件", "ghost", self,
                                     size=32, scale=0.92 * scale)
        self.btn_export.clicked.connect(self.exportRequested)
        head.addWidget(self.btn_export)

        self.btn_clear = PillButton("清空", "trash", "ghost", self, scale=0.92 * scale)
        self.btn_clear.clicked.connect(self.clearRequested)
        head.addWidget(self.btn_clear)

        self.btn_copy = PillButton("复制全部", "copy", "primary", self, scale=1.0 * scale)
        self.btn_copy.setToolTip("把已选标签拼接成提示词并复制到剪贴板  (Ctrl+Shift+C)")
        self.btn_copy.clicked.connect(self.copyRequested)
        head.addWidget(self.btn_copy)
        lay.addLayout(head)

        self.scroll = TagScroll(self, removable=True, mode="both", scale=scale,
                                empty_hint="这里还是空的 —— 点下面的标签，它们会出现在这里 ✨")
        self.scroll.setFixedHeight(self.MIN_H)
        self.scroll.tagRemoveRequested.connect(self.remove)
        self.scroll.canvas.contentHeightChanged.connect(self._schedule_autosize)
        lay.addWidget(self.scroll)

    # ------------------------------------------------------------
    def names(self) -> list[str]:
        return [t.en for t in self._tags]

    def tags(self) -> list[Tag]:
        return list(self._tags)

    def has(self, english: str) -> bool:
        return english in self._index

    def set_visual(self, mode: str, scale: float, show_count: bool = False) -> None:
        self._scale = scale
        self.title.setFont(theme.font(int(round(10.4 * scale)), 700))
        self.count.setFont(theme.font(int(round(8.4 * scale)), 700))
        self.hint.setFont(theme.font(int(round(8.6 * scale)), 400))
        for btn, factor in ((self.btn_save, 0.92), (self.btn_export, 0.92),
                            (self.btn_clear, 0.92), (self.btn_copy, 1.0)):
            btn.set_scale(factor * scale)
        self.scroll.canvas.set_visual(mode=mode, scale=scale, show_count=show_count)
        self._schedule_autosize()

    # ------------------------------------------------------------
    def toggle(self, tag: Tag) -> bool:
        """选中则移除、未选中则加入；返回操作后是否处于选中状态。"""
        if tag.en in self._index:
            self.remove(tag)
            return False
        self.add(tag)
        return True

    def add(self, tag: Tag) -> None:
        if tag.en in self._index:
            return
        self._tags.append(tag)
        self._index[tag.en] = tag
        self._refresh()

    def remove(self, tag: Tag) -> None:
        if tag.en not in self._index:
            return
        self._index.pop(tag.en, None)
        self._tags = [t for t in self._tags if t.en != tag.en]
        self._refresh()

    def clear(self) -> None:
        if not self._tags:
            return
        self._tags = []
        self._index.clear()
        self._refresh()

    def add_names(self, names, db: TagDatabase, append: bool = True) -> int:
        if not append:
            self._tags = []
            self._index.clear()
        added = 0
        for tag in data_store.tags_from_names(names, db):
            if tag.en not in self._index:
                self._tags.append(tag)
                self._index[tag.en] = tag
                added += 1
        if added or not append:
            self._refresh()
        return added

    def _refresh(self) -> None:
        self.scroll.set_tags(self._tags)
        n = len(self._tags)
        self.count.setText(str(n))
        self.hint.setVisible(n == 0)
        self.btn_copy.setEnabled(n > 0)
        self.btn_clear.setEnabled(n > 0)
        self.btn_export.setEnabled(n > 0)
        self.btn_save.setEnabled(n > 0)
        self._schedule_autosize()
        self.changed.emit()

    def _schedule_autosize(self, *_: object) -> None:
        QtCore.QTimer.singleShot(0, self._autosize)

    def _autosize(self) -> None:
        # 用真实内容高度，不能用控件高度（控件会被撑满视口，否则会不断长高）
        content = self.scroll.canvas.content_height()
        target = int(_clamp(content + 4, self.MIN_H, self.MAX_H))
        if self.scroll.height() != target:
            self.scroll.setFixedHeight(target)


# ==================================================================== 标签库页
class LibraryPage(QtWidgets.QWidget):
    tagClicked = Signal(object)

    def __init__(self, db: TagDatabase, user: UserData, parent=None, scale: float = 1.0) -> None:
        super().__init__(parent)
        self.db = db
        self.user = user
        self._scale = scale
        self._mode = "browse"
        self._query = ""
        self.setStyleSheet("background: transparent;")

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # 一层很淡的玻璃底板，保证标签在花哨的壁纸上也清晰可读
        self.panel = GlassCard(self, radius=17, alpha=118, highlight=False)
        play = QtWidgets.QVBoxLayout(self.panel)
        play.setContentsMargins(12, 10, 12, 12)
        play.setSpacing(8)

        self.pills = CategoryPills(self.panel)
        self.pills.changed.connect(self._on_category)
        play.addWidget(self.pills)

        info = QtWidgets.QHBoxLayout()
        info.setContentsMargins(4, 0, 4, 0)
        info.setSpacing(8)
        self.info = QtWidgets.QLabel("", self.panel)
        self.info.setFont(theme.font(int(round(8.8 * scale)), 400))
        self.info.setStyleSheet(f"color: {theme.TEXT_DIM}; background: transparent;")
        info.addWidget(self.info)
        info.addStretch(1)
        self.btn_clear_search = PillButton("返回分类浏览", "close", "ghost", self.panel,
                                           scale=0.86 * scale)
        self.btn_clear_search.clicked.connect(lambda: self.searchCleared.emit())
        self.btn_clear_search.setVisible(False)
        info.addWidget(self.btn_clear_search)
        play.addLayout(info)

        self.grid = TagScroll(self.panel, removable=False, mode="both", scale=scale,
                              empty_hint="没有找到匹配的标签，换个词试试？")
        self.grid.tagClicked.connect(self.tagClicked)
        self.grid.tagContextRequested.connect(self._context_menu)
        play.addWidget(self.grid, 1)
        lay.addWidget(self.panel)

        self._pills_signature: tuple | None = None

    searchCleared = Signal()

    # ------------------------------------------------------------
    def apply_visual(self, mode: str, scale: float, show_count: bool) -> None:
        self._scale = scale
        self.info.setFont(theme.font(int(round(8.8 * scale)), 400))
        self.btn_clear_search.set_scale(0.86 * scale)
        self.grid.canvas.set_visual(mode=mode, scale=scale, show_count=show_count)

    def set_selected(self, selected: set[str]) -> None:
        self.grid.set_selected(selected)

    def reload_categories(self, include_r18: bool, has_custom: bool) -> None:
        items: list[tuple[str, str, int]] = [("all", "热门", len(self.db.hot))]
        for cat in self.db.categories:
            if cat.id == "r18" and not include_r18:
                continue
            items.append((cat.id, cat.name, len(cat.tags)))
        if has_custom:
            items.append(("custom", "自定义", 0))
        signature = tuple(i[0] for i in items) + (include_r18,)
        self._pills_signature = signature
        self.pills.set_categories(items)

    def show_category(self, cid: str, include_r18: bool, custom_tags: list[Tag]) -> None:
        self._mode = "browse"
        self._query = ""
        self.btn_clear_search.setVisible(False)
        if cid == "custom":
            tags = custom_tags
            self.info.setText(f"自定义标签 · {len(tags)} 个")
        else:
            tags = self.db.tags_for(cid, include_r18)
            name = "热门标签" if cid == "all" else (
                self.db.category(cid).name if self.db.category(cid) else cid)
            self.info.setText(f"{name} · {len(tags)} 个标签")
        self.grid.set_tags(tags)

    def show_search(self, query: str, results: list[Tag], index_ready: bool,
                    full_count: int) -> None:
        self._mode = "search"
        self._query = query
        self.btn_clear_search.setVisible(True)
        scope = f"全库 {full_count:,} 条" if index_ready else "核心库（全量索引加载中…）"
        self.info.setText(f"搜索「{query}」· {len(results)} 个结果 · 范围：{scope}")
        self.grid.set_tags(results)

    def current(self) -> tuple[str, str]:
        return self._mode, self._query

    # ------------------------------------------------------------
    def _on_category(self, cid: str) -> None:
        self.categoryChanged.emit(cid)

    categoryChanged = Signal(str)

    def _context_menu(self, tag: Tag, pos: QtCore.QPoint) -> None:
        menu = QtWidgets.QMenu(self)
        act_copy = menu.addAction(icons.icon("copy", 15, theme.TEXT_MAIN), "复制这个标签")
        act_search = menu.addAction(icons.icon("search", 15, theme.TEXT_MAIN), "以它为关键词搜索")
        act_custom = menu.addAction(icons.icon("pencil", 15, theme.TEXT_MAIN), "加入自定义标签")
        chosen = menu.exec_(pos) if hasattr(menu, "exec_") else menu.exec(pos)
        if chosen is act_copy:
            QtWidgets.QApplication.clipboard().setText(tag.en)
            self.copied.emit(f"已复制：{tag.en}")
        elif chosen is act_search:
            self.searchRequested.emit(tag.en)
        elif chosen is act_custom:
            self.customRequested.emit(tag)

    copied = Signal(str)
    searchRequested = Signal(str)
    customRequested = Signal(object)


# ==================================================================== 主窗口
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, db: TagDatabase, user: UserData) -> None:
        super().__init__()
        self.db = db
        self.user = user
        self._scale = float(user.get("font_scale", 1.0))
        self._r18 = bool(user.get("r18", False))
        self._side_collapsed = bool(user.get("sidebar_collapsed", False))

        self.setWindowTitle(f"{APP_TITLE} · 初音未来主题标签选择器")
        self.setMinimumSize(1020, 660)
        icon_path = resources.ICON_DIR / "app.ico"
        if icon_path.exists():
            self.setWindowIcon(QtGui.QIcon(str(icon_path)))
        elif (resources.ICON_DIR / "app.png").exists():
            self.setWindowIcon(QtGui.QIcon(str(resources.ICON_DIR / "app.png")))

        # ---- 背景层
        self.bg = BackgroundWidget(
            self,
            scrim=float(user.get("scrim", 0.52)),
            blur=float(user.get("blur", 0.0)),
        )
        self._apply_wallpaper_from_settings()
        self.setCentralWidget(self.bg)

        root = QtWidgets.QHBoxLayout(self.bg)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar(self.bg, collapsed=self._side_collapsed)
        self.sidebar.pageChanged.connect(self._on_page)
        self.sidebar.collapseToggled.connect(self._on_collapse)
        self.sidebar.mikuClicked.connect(self._miku_egg)
        root.addWidget(self.sidebar)

        content = QtWidgets.QWidget(self.bg)
        content.setStyleSheet("background: transparent;")
        self.content_lay = QtWidgets.QVBoxLayout(content)
        self.content_lay.setContentsMargins(16, 12, 16, 12)
        self.content_lay.setSpacing(10)
        root.addWidget(content, 1)

        # ---- 顶栏
        self.topbar = QtWidgets.QHBoxLayout()
        self.topbar.setSpacing(10)
        self.search = QtWidgets.QLineEdit(content)
        self.search.setPlaceholderText("搜索标签：中文或英文都行，例如「长发」「long_hair」「双马尾」")
        self.search.setFont(theme.font(int(round(10.2 * self._scale))))
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumHeight(int(38 * self._scale))
        self.search.textChanged.connect(self._on_search_text)
        self.search.returnPressed.connect(self._flush_search)
        self.topbar.addWidget(self.search, 1)

        r18_box = QtWidgets.QWidget(content)
        r18_box.setStyleSheet("background: transparent;")
        rb = QtWidgets.QHBoxLayout(r18_box)
        rb.setContentsMargins(0, 0, 0, 0)
        rb.setSpacing(7)
        self.r18_label = QtWidgets.QLabel("R18", r18_box)
        self.r18_label.setFont(theme.font(int(round(9.4 * self._scale)), 700))
        self.r18_switch = ToggleSwitch(r18_box, checked=self._r18, on_color="#FF5C8A")
        self.r18_switch.setToolTip("默认关闭。打开后显示 R18 分类与相关搜索结果。")
        self.r18_switch.toggled.connect(self._on_r18)
        rb.addWidget(self.r18_label)
        rb.addWidget(self.r18_switch)
        self.topbar.addWidget(r18_box)

        self.stats_label = QtWidgets.QLabel("", content)
        self.stats_label.setFont(theme.font(int(round(8.4 * self._scale)), 400))
        self.stats_label.setStyleSheet(f"color: {theme.TEXT_FAINT}; background: transparent;")
        self.topbar.addWidget(self.stats_label)
        self.content_lay.addLayout(self.topbar)

        # ---- 已选标签框（永远在最上面）
        self.selected = SelectedBar(content, self.user, scale=self._scale)
        self.selected.copyRequested.connect(self.copy_all)
        self.selected.exportRequested.connect(self.export_tags)
        self.selected.saveRequested.connect(self.save_current_as_preset)
        self.selected.clearRequested.connect(self.clear_selection)
        self.content_lay.addWidget(self.selected)

        # ---- 页面栈
        self.stack = QtWidgets.QStackedWidget(content)
        self.stack.setStyleSheet("background: transparent;")

        self.library = LibraryPage(self.db, self.user, self.stack, self._scale)
        self.library.tagClicked.connect(self.toggle_tag)
        self.library.categoryChanged.connect(self._on_category)
        self.library.searchCleared.connect(self._clear_search)
        self.library.copied.connect(lambda m: self.toast.show_message(m))
        self.library.searchRequested.connect(self._search_from_menu)
        self.library.customRequested.connect(self._add_to_custom)

        self.presets_page = pages_mod.PresetsPage(self.db, self.user, self.stack, self._scale)
        self.presets_page.applyRequested.connect(self._apply_preset)
        self.presets_page.copyRequested.connect(self._copy_preset)
        self.presets_page.saveCurrentRequested.connect(self._save_from_presets_page)

        self.custom_page = pages_mod.CustomTagsPage(self.db, self.user, self.stack, self._scale)
        self.custom_page.tagClicked.connect(self.toggle_tag)

        self.settings_page = pages_mod.SettingsPage(self.db, self.user, self.stack, self._scale)
        self.about_page = pages_mod.AboutPage(self.db, self.user, self.stack, self._scale)

        for page in (self.library, self.presets_page, self.custom_page,
                     self.settings_page, self.about_page):
            self.stack.addWidget(page)
        self.content_lay.addWidget(self.stack, 1)

        # ---- 覆盖层
        self.toast = Toast(self.bg)
        self.leek_rain = LeekRain(self.bg)

        # ---- 状态
        self.user.settingsChanged.connect(self._on_setting)
        self.user.customChanged.connect(self._on_custom_changed)
        self.user.presetsChanged.connect(self._on_presets_changed)
        self.db.fullIndexReady.connect(self._on_index_ready)
        self.db.fullIndexFailed.connect(self._on_index_failed)

        self._selected: dict[str, Tag] = {}
        self._search_timer = QtCore.QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(140)
        self._search_timer.timeout.connect(self._flush_search)

        self._restore_geometry()
        self._on_page(str(self.user.get("last_page", "library")), persist=False)
        self._refresh_categories()
        self.library.pills.select("all", emit=False)
        self.library.show_category("all", self._r18, self._custom_tag_objects())
        self._update_stats()

        if self._r18:
            self.toast.show_message("R18 已开启", "请注意内容分级，理性使用～", "eye", 2200)

    # ------------------------------------------------------------ 生命周期
    def _restore_geometry(self) -> None:
        geo = self.user.get("window")
        screen = QtWidgets.QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else QtCore.QRect(0, 0, 1440, 900)
        if isinstance(geo, (list, tuple)) and len(geo) == 4:
            x, y, w, h = (int(v) for v in geo)
            w = _clamp(w, 1020, avail.width())
            h = _clamp(h, 660, avail.height())
            x = _clamp(x, avail.left() - 40, avail.right() - 200)
            y = _clamp(y, avail.top(), avail.bottom() - 120)
            self.setGeometry(x, y, w, h)
        else:
            w = min(1320, int(avail.width() * 0.82))
            h = min(860, int(avail.height() * 0.86))
            self.setGeometry(avail.center().x() - w // 2, avail.center().y() - h // 2, w, h)

    def closeEvent(self, event) -> None:  # noqa: N802
        try:
            g = self.geometry()
            self.user.set("window", [g.x(), g.y(), g.width(), g.height()], save=False)
            self.user.set("sidebar_collapsed", self._side_collapsed, save=False)
            self.user.save_settings()
        except Exception:
            pass
        super().closeEvent(event)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.toast.raise_()
        self.leek_rain.raise_()

    # ------------------------------------------------------------ 壁纸 / 设置
    def _apply_wallpaper_from_settings(self) -> None:
        path = str(self.user.get("wallpaper", "") or "")
        if path and self.bg.set_wallpaper(path):
            return
        wallpapers = resources.wallpaper_files()
        if wallpapers:
            self.bg.set_wallpaper(wallpapers[0][1])

    def _on_setting(self, key: str) -> None:
        if key == "wallpaper":
            self._apply_wallpaper_from_settings()
            self.settings_page.refresh_wallpaper()
        elif key == "scrim":
            self.bg.set_scrim(float(self.user.get("scrim", 0.52)))
        elif key == "blur":
            self.bg.set_blur(float(self.user.get("blur", 0.0)))
        elif key == "r18":
            self._on_r18(bool(self.user.get("r18", False)))
        elif key in ("chip_mode", "show_counts", "font_scale"):
            self._apply_visual_settings()

    def _apply_visual_settings(self) -> None:
        self._scale = float(self.user.get("font_scale", 1.0))
        mode = str(self.user.get("chip_mode", "both"))
        show_count = bool(self.user.get("show_counts", True))
        self.search.setFont(theme.font(int(round(10.2 * self._scale))))
        self.search.setMinimumHeight(int(38 * self._scale))
        self.r18_label.setFont(theme.font(int(round(9.4 * self._scale)), 700))
        self.stats_label.setFont(theme.font(int(round(8.4 * self._scale)), 400))
        self.selected.set_visual(mode, self._scale, show_count)
        self.library.apply_visual(mode, self._scale, show_count)
        ctx = self.library.grid.canvas
        ctx.set_visual(mode=mode, scale=self._scale, show_count=show_count)
        ctx.update()
        for page in (self.presets_page, self.custom_page, self.settings_page, self.about_page):
            page.rebuild_fonts(self._scale)

    # ------------------------------------------------------------ 页面
    def _on_page(self, key: str, persist: bool = True) -> None:
        mapping = {
            "library": 0, "presets": 1, "custom": 2, "settings": 3, "about": 4,
        }
        self.stack.setCurrentIndex(mapping.get(key, 0))
        self.sidebar.set_page(key)
        if persist:
            self.user.set("last_page", key)

    def _on_collapse(self, collapsed: bool) -> None:
        self._side_collapsed = collapsed
        self.user.set("sidebar_collapsed", collapsed)

    # ------------------------------------------------------------ 搜索
    def _on_search_text(self, text: str) -> None:
        if text.strip() == "39":
            self.search.clear()
            self._miku_egg()
            return
        if self.stack.currentIndex() != 0:
            self._on_page("library")
        self._search_timer.start()

    def _search_from_menu(self, query: str) -> None:
        self._on_page("library")
        self.search.setText(query)
        self._flush_search()

    def _clear_search(self) -> None:
        self.search.clear()
        self._flush_search()

    def _flush_search(self) -> None:
        self._search_timer.stop()
        query = self.search.text().strip()
        if not query:
            self.library.pills.select(self.library.pills.current(), emit=False)
            self.library.show_category(self.library.pills.current(), self._r18,
                                       self._custom_tag_objects())
            self.library.set_selected(set(self._selected))
            return
        results = self._search_all(query)
        self.library.show_search(query, results, self.db.full_ready, self.db.full_count)
        self.library.set_selected(set(self._selected))

    def _search_all(self, query: str) -> list[Tag]:
        q = query.strip().lower()
        hits: list[Tag] = []
        for row in self.user.custom_tags:
            en = row["en"]
            zh = row.get("zh", "")
            if q in en.lower() or (zh and query.strip() in zh):
                hits.append(Tag(en, zh, 0, 0, "custom", custom=True))
        hits.extend(self.db.search(query, limit=600, include_r18=self._r18))
        return data_store.merge_tags(hits)

    # ------------------------------------------------------------ 选择
    def toggle_tag(self, tag: Tag) -> None:
        if tag.en in self._selected:
            del self._selected[tag.en]
            self.selected.remove(tag)
        else:
            self._selected[tag.en] = tag
            self.selected.add(tag)
        self._sync_selection()

    def _sync_selection(self) -> None:
        keys = set(self._selected)
        self.library.set_selected(keys)
        self.custom_page.canvas.set_selected(keys)

    def clear_selection(self) -> None:
        if not self._selected:
            return
        if bool(self.user.get("confirm_clear", True)):
            box = QtWidgets.QMessageBox(self)
            box.setWindowTitle("清空已选标签")
            box.setText(f"确定要清空这 {len(self._selected)} 个标签吗？")
            box.setIcon(QtWidgets.QMessageBox.Question)
            yes = box.addButton("清空", QtWidgets.QMessageBox.AcceptRole)
            box.addButton("取消", QtWidgets.QMessageBox.RejectRole)
            box.exec_() if hasattr(box, "exec_") else box.exec()
            if box.clickedButton() is not yes:
                return
        self._selected.clear()
        self.selected.clear()
        self._sync_selection()
        self.toast.show_message("已清空选择", icon="trash")

    # ------------------------------------------------------------ 复制
    def copy_all(self) -> None:
        names = list(self._selected.keys())
        if not names:
            self.toast.show_message("还没有选择任何标签", "先点几个标签再复制吧～", "info")
            return
        text = format_tags(names, str(self.user.get("copy_format", "comma")))
        QtWidgets.QApplication.clipboard().setText(text)
        preview = text if len(text) <= 90 else text[:90] + "…"
        self.toast.show_message(f"已复制 {len(names)} 个标签", preview, "copy", 2100)

    def export_tags(self) -> None:
        names = list(self._selected.keys())
        if not names:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出提示词", str(self.user.dir / "prompt.txt"), "文本文件 (*.txt)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(format_tags(names, str(self.user.get("copy_format", "comma"))))
        self.toast.show_message("已导出提示词", path, "download")

    # ------------------------------------------------------------ 预设
    def _preset_names(self, preset: dict, negative: bool = False) -> list[str]:
        return list(preset.get("negative" if negative else "tags", []))

    def _apply_preset(self, preset: dict, append: bool) -> None:
        names = self._preset_names(preset)
        if not names:
            self.toast.show_message("这个预设是空的", icon="info")
            return
        added = self.selected.add_names(names, self.db, append=append)
        if not append:
            self._selected = {t.en: t for t in self.selected.tags()}
        else:
            for t in self.selected.tags():
                self._selected[t.en] = t
        self._sync_selection()
        self._on_page("library")
        self.toast.show_message(
            f"已应用「{preset.get('name', '预设')}」",
            f"{'追加' if append else '替换为'} {added} 个标签", "wand", 2000)

    def _copy_preset(self, preset: dict, negative: bool) -> None:
        names = self._preset_names(preset, negative)
        if not names:
            return
        text = format_tags(names, str(self.user.get("copy_format", "comma")))
        QtWidgets.QApplication.clipboard().setText(text)
        label = "负面提示词" if negative else "正向标签"
        self.toast.show_message(f"已复制{label}", f"{preset.get('name', '')} · {len(names)} 项",
                                "copy")

    def _save_from_presets_page(self) -> None:
        name = self.presets_page.suggested_name()
        self._do_save_preset(name)

    def save_current_as_preset(self) -> None:
        if not self._selected:
            self.toast.show_message("还没有选择任何标签", "先点几个标签再存预设吧～", "info")
            return
        self._do_save_preset(self.presets_page.suggested_name())

    def _do_save_preset(self, name: str) -> None:
        if not name:
            name, ok = QtWidgets.QInputDialog.getText(
                self, "保存预设", "给这个预设起个名字：",
                QtWidgets.QLineEdit.Normal, f"我的预设 {len(self.user.user_presets) + 1}")
            if not ok or not name.strip():
                return
            name = name.strip()
        self.user.add_preset(name, list(self._selected.keys()),
                             desc=f"共 {len(self._selected)} 个标签")
        self.presets_page.clear_name()
        self._on_page("presets")
        self.toast.show_message(f"已保存预设「{name}」", f"{len(self._selected)} 个标签", "save")

    def _on_presets_changed(self) -> None:
        self.presets_page.reload()

    # ------------------------------------------------------------ 自定义标签
    def _custom_tag_objects(self) -> list[Tag]:
        return [Tag(r["en"], r.get("zh", ""), 0, 0, "custom", custom=True)
                for r in self.user.custom_tags]

    def _add_to_custom(self, tag: Tag) -> None:
        self.user.add_custom_tag(tag.en, tag.zh, "", "从标签库收藏")
        self.toast.show_message(f"已加入自定义标签：{tag.en}", icon="pencil")

    def _on_custom_changed(self) -> None:
        self.custom_page.reload()
        if self.library.pills.current() == "custom":
            self.library.show_category("custom", self._r18, self._custom_tag_objects())
        self._refresh_categories()

    # ------------------------------------------------------------ 分类
    def _refresh_categories(self) -> None:
        self.library.reload_categories(self._r18, bool(self.user.custom_tags))

    def _on_category(self, cid: str) -> None:
        if self.search.text().strip():
            self.search.blockSignals(True)
            self.search.clear()
            self.search.blockSignals(False)
            self.library.btn_clear_search.setVisible(False)
        self.library.show_category(cid, self._r18, self._custom_tag_objects())
        self.library.set_selected(set(self._selected))

    def _on_r18(self, enabled: bool) -> None:
        enabled = bool(enabled)
        if self.r18_switch.isChecked() != enabled:
            self.r18_switch.blockSignals(True)
            self.r18_switch.setChecked(enabled)
            self.r18_switch.blockSignals(False)
        self._r18 = enabled
        self.user.set("r18", enabled)
        self.r18_label.setStyleSheet(
            f"color: {'#FF8FA3' if enabled else theme.TEXT_DIM}; background: transparent;")
        self._refresh_categories()
        if self.search.text().strip():
            self._flush_search()
        else:
            self.library.pills.select(self.library.pills.current(), emit=False)
            self.library.show_category(self.library.pills.current(), enabled,
                                       self._custom_tag_objects())
            self.library.set_selected(set(self._selected))
        self._update_stats()
        if enabled:
            self.toast.show_message("R18 已开启", "相关内容已被加入分类与搜索", "eye", 2200)

    # ------------------------------------------------------------ 统计 / 索引
    def _update_stats(self) -> None:
        stats = self.db.stats()
        full = f"{stats['full']:,}" if stats["full_ready"] else "…"
        self.stats_label.setText(f"核心 {stats['core']:,} · 全库 {full}")

    def _on_index_ready(self) -> None:
        self._update_stats()
        self.toast.show_message("全量标签库已就绪",
                                f"现在可以搜索全部 {self.db.full_count:,} 个标签", "wand", 2400)
        if self.search.text().strip():
            self._flush_search()

    def _on_index_failed(self, message: str) -> None:
        self.toast.show_message("全量索引加载失败", message[:70], "info", 3200)

    # ------------------------------------------------------------ 彩蛋
    def _miku_egg(self) -> None:
        self.leek_rain.setGeometry(self.bg.rect())
        self.leek_rain.start(7200, 30)
        self.toast.show_message("ミクだよ♪  39!", "大葱雨来啦 🌱  (´∀｀)♡", "note", 2600)

    # ------------------------------------------------------------ 快捷键
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:  # noqa: N802
        mods = event.modifiers()
        key = event.key()
        ctrl = mods & QtCore.Qt.ControlModifier
        shift = mods & QtCore.Qt.ShiftModifier
        if ctrl and key == QtCore.Qt.Key_F:
            self._on_page("library")
            self.search.setFocus()
            self.search.selectAll()
            return
        if ctrl and shift and key == QtCore.Qt.Key_C:
            self.copy_all()
            return
        if ctrl and key == QtCore.Qt.Key_B:
            self.sidebar.set_collapsed(not self.sidebar.is_collapsed())
            return
        if ctrl and QtCore.Qt.Key_1 <= key <= QtCore.Qt.Key_5:
            order = ["library", "presets", "custom", "settings", "about"]
            self._on_page(order[key - QtCore.Qt.Key_1])
            return
        if key == QtCore.Qt.Key_Escape:
            if self.search.text():
                self._clear_search()
            else:
                self.search.clearFocus()
            return
        super().keyPressEvent(event)
