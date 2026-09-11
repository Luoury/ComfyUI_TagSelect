# -*- coding: utf-8 -*-
"""侧边栏各个页面：预设、自定义标签、设置、关于。"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ..qtcompat import QtCore, QtGui, QtWidgets, Signal, qsin
from .. import __author__, __version__
from .. import data_store, icons, miku_art, resources, theme
from ..user_data import COPY_FORMATS
from .background import build_default_background
from .common import GlassCard, IconButton, PillButton, ToggleSwitch, VScroll
from .tag_canvas import TagScroll


# ==================================================================== 基础
class PageBase(QtWidgets.QWidget):
    """带标题与可滚动内容区的页面骨架。"""

    def __init__(self, title: str, subtitle: str = "",
                 parent: QtWidgets.QWidget | None = None, scale: float = 1.0) -> None:
        super().__init__(parent)
        self.scale = scale
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(10)

        head = QtWidgets.QVBoxLayout()
        head.setContentsMargins(4, 0, 4, 0)
        head.setSpacing(1)
        self.title_label = QtWidgets.QLabel(title, self)
        self.title_label.setFont(theme.font(int(round(15 * scale)), 700))
        self.title_label.setStyleSheet(f"color: {theme.TEXT_MAIN}; background: transparent;")
        head.addWidget(self.title_label)
        if subtitle:
            self.subtitle_label = QtWidgets.QLabel(subtitle, self)
            self.subtitle_label.setFont(theme.font(int(round(9.2 * scale)), 400))
            self.subtitle_label.setStyleSheet(f"color: {theme.TEXT_DIM}; background: transparent;")
            head.addWidget(self.subtitle_label)
        outer.addLayout(head)

        self.scroll = VScroll(self)
        self.holder = QtWidgets.QWidget()
        self.holder.setStyleSheet("background: transparent;")
        self.body = QtWidgets.QVBoxLayout(self.holder)
        self.body.setContentsMargins(4, 2, 10, 16)
        self.body.setSpacing(12)
        self.scroll.setWidget(self.holder)
        outer.addWidget(self.scroll, 1)

    def rebuild_fonts(self, scale: float) -> None:
        self.scale = scale
        self.title_label.setFont(theme.font(int(round(15 * scale)), 700))
        if hasattr(self, "subtitle_label"):
            self.subtitle_label.setFont(theme.font(int(round(9.2 * scale)), 400))


def card(title: str = "", desc: str = "") -> tuple[GlassCard, QtWidgets.QVBoxLayout]:
    box = GlassCard(strong=False)
    lay = QtWidgets.QVBoxLayout(box)
    lay.setContentsMargins(16, 13, 16, 15)
    lay.setSpacing(9)
    if title:
        t = QtWidgets.QLabel(title, box)
        t.setFont(theme.font(11, 700))
        t.setStyleSheet(f"color: {theme.TEXT_MAIN}; background: transparent;")
        lay.addWidget(t)
    if desc:
        d = QtWidgets.QLabel(desc, box)
        d.setFont(theme.font(9, 400))
        d.setWordWrap(True)
        d.setStyleSheet(f"color: {theme.TEXT_DIM}; background: transparent;")
        lay.addWidget(d)
    return box, lay


def row(label: str, widget: QtWidgets.QWidget, desc: str = "",
        parent: QtWidgets.QWidget | None = None) -> QtWidgets.QWidget:
    holder = QtWidgets.QWidget(parent)
    lay = QtWidgets.QHBoxLayout(holder)
    lay.setContentsMargins(0, 2, 0, 2)
    lay.setSpacing(12)
    left = QtWidgets.QVBoxLayout()
    left.setContentsMargins(0, 0, 0, 0)
    left.setSpacing(1)
    name = QtWidgets.QLabel(label, holder)
    name.setFont(theme.font(9.8, 600))
    name.setStyleSheet(f"color: {theme.TEXT_MAIN}; background: transparent;")
    left.addWidget(name)
    if desc:
        d = QtWidgets.QLabel(desc, holder)
        d.setFont(theme.font(8.4, 400))
        d.setStyleSheet(f"color: {theme.TEXT_FAINT}; background: transparent;")
        d.setWordWrap(True)
        left.addWidget(d)
    lay.addLayout(left, 1)
    lay.addWidget(widget, 0, QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
    return holder


# ==================================================================== 预设
class PresetCard(GlassCard):
    applyRequested = Signal(dict, bool)
    copyRequested = Signal(dict, bool)
    deleteRequested = Signal(dict)
    editRequested = Signal(dict)

    def __init__(self, preset: dict, is_user: bool, db, parent=None) -> None:
        super().__init__(parent)
        self.preset = preset
        self.setStyleSheet("background: transparent;")
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(15, 12, 15, 13)
        lay.setSpacing(8)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(8)
        name = QtWidgets.QLabel(preset.get("name", "未命名"), self)
        name.setFont(theme.font(10.6, 700))
        name.setStyleSheet(f"color: {theme.TEXT_MAIN}; background: transparent;")
        top.addWidget(name)
        if is_user:
            badge = QtWidgets.QLabel("我的", self)
            badge.setFont(theme.font(7.6, 700))
            badge.setStyleSheet(
                "color: #07131F; background: rgba(57,197,187,0.9);"
                "border-radius: 7px; padding: 1px 7px;")
            top.addWidget(badge)
        top.addStretch(1)

        btn_apply = PillButton("应用", "check", "primary", self, scale=0.92)
        btn_apply.setToolTip("把这些标签加入上方选择框")
        btn_apply.clicked.connect(lambda: self.applyRequested.emit(self.preset, False))
        top.addWidget(btn_apply)

        btn_add = PillButton("追加", "plus", "ghost", self, scale=0.92)
        btn_add.setToolTip("保留当前已选，追加这些标签")
        btn_add.clicked.connect(lambda: self.applyRequested.emit(self.preset, True))
        top.addWidget(btn_add)

        btn_copy = IconButton("copy", "复制该预设的正向标签", "ghost", self, size=30, scale=0.92)
        btn_copy.clicked.connect(lambda: self.copyRequested.emit(self.preset, False))
        top.addWidget(btn_copy)

        if preset.get("negative"):
            btn_copy_neg = IconButton("eye_off", "复制该预设的负面提示词", "ghost", self,
                                      size=30, scale=0.92)
            btn_copy_neg.clicked.connect(lambda: self.copyRequested.emit(self.preset, True))
            top.addWidget(btn_copy_neg)

        if is_user:
            btn_edit = IconButton("pencil", "重命名 / 覆盖", "ghost", self, size=30, scale=0.92)
            btn_edit.clicked.connect(lambda: self.editRequested.emit(self.preset))
            top.addWidget(btn_edit)
            btn_del = IconButton("trash", "删除该预设", "danger", self, size=30, scale=0.92)
            btn_del.clicked.connect(lambda: self.deleteRequested.emit(self.preset))
            top.addWidget(btn_del)
        lay.addLayout(top)

        desc = preset.get("desc", "")
        if desc:
            d = QtWidgets.QLabel(desc, self)
            d.setFont(theme.font(8.6, 400))
            d.setWordWrap(True)
            d.setStyleSheet(f"color: {theme.TEXT_DIM}; background: transparent;")
            lay.addWidget(d)

        preview = TagScroll(self, mode="both", scale=0.84, compact=True)
        preview.setFixedHeight(96)
        positive = list(preset.get("tags", []))
        negative = list(preset.get("negative", []))
        shown = positive if positive else negative
        preview.set_tags(data_store.tags_from_names(shown, db))
        preview.canvas.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        # 内容少的时候收窄预览区，避免大片留白
        QtCore.QTimer.singleShot(0, lambda p=preview: p.setFixedHeight(
            int(max(34, min(96, p.canvas.content_height() + 6)))))
        caption = QtWidgets.QLabel(
            "正向标签预览" if positive else "负面提示词预览", self)
        caption.setFont(theme.font(8.2, 600))
        caption.setStyleSheet(
            f"color: {theme.TEXT_FAINT}; background: transparent;")
        lay.addWidget(caption)
        lay.addWidget(preview)

        meta_bits = [f"正向 {len(positive)} 个"]
        if negative:
            meta_bits.append(f"负面 {len(negative)} 个")
        meta = QtWidgets.QLabel(" · ".join(meta_bits), self)
        meta.setFont(theme.font(8.2, 400))
        meta.setStyleSheet(f"color: {theme.TEXT_FAINT}; background: transparent;")
        lay.addWidget(meta)


class PresetsPage(PageBase):
    applyRequested = Signal(dict, bool)
    copyRequested = Signal(dict)
    saveCurrentRequested = Signal()

    def __init__(self, db, user, parent=None, scale: float = 1.0) -> None:
        super().__init__("预设", "常驻预设开箱即用；也可以把当前选择保存成自己的预设。",
                         parent, scale)
        self.db = db
        self.user = user

        top_card, top_lay = card("我的预设", "把上方已选好的标签存成预设，下次一键复用。")
        bar = QtWidgets.QHBoxLayout()
        bar.setSpacing(8)
        self.name_edit = QtWidgets.QLineEdit(top_card)
        self.name_edit.setPlaceholderText("预设名称，例如：我的赛博少女")
        self.name_edit.setFont(theme.font(9.6))
        bar.addWidget(self.name_edit, 1)
        btn_save = PillButton("保存当前选择", "save", "primary", top_card, scale=0.95)
        btn_save.clicked.connect(self._save_clicked)
        bar.addWidget(btn_save)
        top_lay.addLayout(bar)
        self.body.addWidget(top_card)

        self.groups_box = QtWidgets.QVBoxLayout()
        self.groups_box.setSpacing(14)
        self.body.addLayout(self.groups_box)
        self.body.addStretch(1)
        self.reload()

    def _save_clicked(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.saveCurrentRequested.emit()
            return
        self.saveCurrentRequested.emit()

    def suggested_name(self) -> str:
        return self.name_edit.text().strip()

    def clear_name(self) -> None:
        self.name_edit.clear()

    def reload(self) -> None:
        while self.groups_box.count():
            item = self.groups_box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
            elif item.layout() is not None:
                _clear_layout(item.layout())

        for group in self.user.groups_with_presets():
            presets = group.get("presets", [])
            if not presets:
                continue
            header = QtWidgets.QWidget()
            hl = QtWidgets.QVBoxLayout(header)
            hl.setContentsMargins(4, 4, 4, 0)
            hl.setSpacing(1)
            t = QtWidgets.QLabel(group.get("name", ""), header)
            t.setFont(theme.font(12, 700))
            t.setStyleSheet(f"color: {theme.MIKU_CYAN_LIGHT}; background: transparent;")
            hl.addWidget(t)
            if group.get("desc"):
                d = QtWidgets.QLabel(group["desc"], header)
                d.setFont(theme.font(8.8, 400))
                d.setWordWrap(True)
                d.setStyleSheet(f"color: {theme.TEXT_DIM}; background: transparent;")
                hl.addWidget(d)
            self.groups_box.addWidget(header)

            for preset in presets:
                cardw = PresetCard(preset, bool(group.get("user")), self.db)
                cardw.applyRequested.connect(self.applyRequested)
                cardw.copyRequested.connect(self.copyRequested)
                self.groups_box.addWidget(cardw)


def _clear_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        w = item.widget()
        if w is not None:
            # 先隐藏并脱离父子关系，避免旧控件保留几何位置继续绘制
            w.hide()
            w.setParent(None)
            w.deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())


# ==================================================================== 自定义标签
class CustomTagsPage(PageBase):
    tagClicked = Signal(object)
    customChanged = Signal()

    def __init__(self, db, user, parent=None, scale: float = 1.0) -> None:
        super().__init__("自定义标签", "添加数据库里没有的标签（新模型词、个人常用词等），会同步出现在搜索里。",
                         parent, scale)
        self.db = db
        self.user = user

        form, fl = card("添加一个标签", "英文标签会原样出现在提示词里；中文名只用于搜索和显示。")
        grid = QtWidgets.QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)
        self.en_edit = QtWidgets.QLineEdit(form)
        self.en_edit.setPlaceholderText("英文标签 * 例如：my_oc_(character)")
        self.zh_edit = QtWidgets.QLineEdit(form)
        self.zh_edit.setPlaceholderText("中文名（可选）例如：我的原创角色")
        self.group_edit = QtWidgets.QLineEdit(form)
        self.group_edit.setPlaceholderText("分组（可选）例如：我的角色")
        self.note_edit = QtWidgets.QLineEdit(form)
        self.note_edit.setPlaceholderText("备注（可选）")
        for w in (self.en_edit, self.zh_edit, self.group_edit, self.note_edit):
            w.setFont(theme.font(9.6))
        grid.addWidget(self.en_edit, 0, 0, 1, 2)
        grid.addWidget(self.zh_edit, 1, 0)
        grid.addWidget(self.group_edit, 1, 1)
        grid.addWidget(self.note_edit, 2, 0, 1, 2)
        fl.addLayout(grid)

        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        btn_add = PillButton("加入自定义标签", "plus", "primary", form, scale=0.95)
        btn_add.clicked.connect(self._add)
        btns.addWidget(btn_add)
        fl.addLayout(btns)

        self.hint = QtWidgets.QLabel("", form)
        self.hint.setFont(theme.font(8.8, 400))
        self.hint.setStyleSheet(f"color: {theme.MIKU_CYAN_LIGHT}; background: transparent;")
        self.hint.setVisible(False)
        fl.addWidget(self.hint)
        self.body.addWidget(form)

        self.list_card, self.list_lay = card("我的标签库", "单击标签即可加入 / 移出上方选择框。")
        self.canvas = TagScroll(self.list_card, mode="both", scale=0.95,
                                empty_hint="还没有自定义标签，在上面添加第一个吧～")
        self.canvas.setMinimumHeight(180)
        self.canvas.tagClicked.connect(self.tagClicked)
        self.list_lay.addWidget(self.canvas)

        tools = QtWidgets.QHBoxLayout()
        tools.addStretch(1)
        btn_open = PillButton("打开数据目录", "download", "ghost", self.list_card, scale=0.9)
        btn_open.clicked.connect(self._open_dir)
        tools.addWidget(btn_open)
        btn_export = PillButton("导出为 txt", "save", "ghost", self.list_card, scale=0.9)
        btn_export.clicked.connect(self._export)
        tools.addWidget(btn_export)
        self.list_lay.addLayout(tools)
        self.body.addWidget(self.list_card)
        self.body.addStretch(1)

        self.user.customChanged.connect(self.reload)
        self.reload()

    def _add(self) -> None:
        en = self.en_edit.text().strip()
        if not en:
            self._flash("请先填写英文标签～", error=True)
            return
        self.user.add_custom_tag(en, self.zh_edit.text(), self.note_edit.text(),
                                 self.group_edit.text().strip() or "我的标签")
        self.en_edit.clear()
        self.zh_edit.clear()
        self.note_edit.clear()
        self._flash(f"已添加：{en}")
        self.reload()

    def _flash(self, msg: str, error: bool = False) -> None:
        self.hint.setText(msg)
        self.hint.setStyleSheet(
            f"color: {theme.DANGER if error else theme.MIKU_CYAN_LIGHT}; background: transparent;")
        self.hint.setVisible(True)
        QtCore.QTimer.singleShot(2600, lambda: self.hint.setVisible(False))

    def _open_dir(self) -> None:
        path = str(self.user.dir)
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    def _export(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "导出自定义标签", str(self.user.dir / "my_tags.txt"), "文本文件 (*.txt)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(", ".join(r["en"] for r in self.user.custom_tags))
        self._flash(f"已导出到 {path}")

    def reload(self) -> None:
        tags = [data_store.Tag(r["en"], r.get("zh", ""), 0, 0, "custom", custom=True)
                for r in self.user.custom_tags]
        self.canvas.set_tags(tags)

    def selected_names(self) -> set[str]:
        return {r["en"] for r in self.user.custom_tags}


# ==================================================================== 设置
class WallpaperThumb(QtWidgets.QAbstractButton):
    """壁纸缩略图。

    key 是稳定标识（``user:xxx.jpg`` / ``builtin:xxx.jpg`` / 空串=默认背景），
    设置里存的就是它 —— 单文件 exe 每次启动临时目录都不同，存绝对路径会失效。
    """

    def __init__(self, label: str, key: str, path=None, parent=None,
                 badge: str = "", tooltip: str = "") -> None:
        super().__init__(parent)
        self.label = label
        self.key = key
        self.path = path
        self._active = False
        self._hover = False
        self._badge = badge
        self.setCheckable(False)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedSize(168, 108)
        self.setToolTip(tooltip or (str(path) if path else "程序生成的初音配色星空背景"))

        img_w, img_h = self.width() - 10, 82
        if path is None:
            self._pm = build_default_background(img_w, img_h)
        else:
            pm = QtGui.QPixmap(str(path))
            self._pm = (pm.scaled(self.width(), img_h, QtCore.Qt.KeepAspectRatioByExpanding,
                                  QtCore.Qt.SmoothTransformation)
                        if not pm.isNull() else pm)

    def set_active(self, value: bool) -> None:
        if self._active != value:
            self._active = value
            self.update()

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        box = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setBrush(QtGui.QColor(255, 255, 255, 14))
        p.setPen(QtCore.Qt.NoPen)
        p.drawRoundedRect(box, 11, 11)

        img_rect = QtCore.QRectF(5, 5, self.width() - 10, 82)
        clip = QtGui.QPainterPath()
        clip.addRoundedRect(img_rect, 8, 8)
        p.save()
        p.setClipPath(clip)
        if not self._pm.isNull():
            sx = max(0, (self._pm.width() - int(img_rect.width())) // 2)
            sy = max(0, (self._pm.height() - int(img_rect.height())) // 2)
            p.drawPixmap(img_rect.toRect(), self._pm,
                         QtCore.QRect(sx, sy, int(img_rect.width()), int(img_rect.height())))
        p.restore()

        if self._active:
            p.setBrush(QtGui.QColor(57, 197, 187, 60))
            p.setPen(QtCore.Qt.NoPen)
            p.drawRoundedRect(img_rect, 8, 8)
            icons.paint_glyph(p, "check", QtCore.QRectF(img_rect.right() - 26,
                                                        img_rect.top() + 6, 18, 18), "#FFFFFF")
        if self._badge:
            w = 34
            badge_rect = QtCore.QRectF(img_rect.left() + 6, img_rect.top() + 6, w, 15)
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(QtGui.QColor(46, 139, 255, 220))
            p.drawRoundedRect(badge_rect, 7, 7)
            p.setFont(theme.font(7.4, 700))
            p.setPen(QtGui.QColor("#FFFFFF"))
            p.drawText(badge_rect, QtCore.Qt.AlignCenter, self._badge)

        border = theme.MIKU_CYAN if self._active else (
            theme.CHIP_BORDER_HOVER if self._hover else theme.CHIP_BORDER)
        p.setBrush(QtCore.Qt.NoBrush)
        p.setPen(QtGui.QPen(QtGui.QColor(border), 1.6 if self._active else 1.0))
        p.drawRoundedRect(box, 11, 11)

        p.setFont(theme.font(8.4, 600 if self._active else 400))
        p.setPen(QtGui.QColor(theme.TEXT_MAIN if self._active else theme.TEXT_DIM))
        p.drawText(QtCore.QRectF(6, 89, self.width() - 12, 16),
                   QtCore.Qt.AlignCenter, self.label)
        p.end()


class SettingsPage(PageBase):
    # (标题, 副标题, 图标) —— 由主窗口接上 Toast
    toast = Signal(str, str, str)

    def __init__(self, db, user, parent=None, scale: float = 1.0) -> None:
        super().__init__("设置", "所有改动即时生效并自动保存。", parent, scale)
        self.db = db
        self.user = user
        self._thumbs: list[WallpaperThumb] = []
        self._build()

    def _build(self) -> None:
        # ---- 外观
        box, lay = card("外观", "壁纸会自动铺满窗口，任何窗口比例下都不会出现空白。")
        self.wall_box = QtWidgets.QWidget(box)
        self.wall_lay = QtWidgets.QGridLayout(self.wall_box)
        self.wall_lay.setContentsMargins(0, 0, 0, 0)
        self.wall_lay.setSpacing(10)
        wallpapers = resources.wallpaper_files()
        for i, item in enumerate(wallpapers):
            badge = "我的" if item.user else ""
            thumb = WallpaperThumb(item.label, item.key, item.path, self.wall_box,
                                   badge=badge)
            thumb.clicked.connect(lambda _=False, k=item.key: self._set_wallpaper(k))
            self.wall_lay.addWidget(thumb, i // 4, i % 4)
            self._thumbs.append(thumb)
        if not wallpapers:
            empty = QtWidgets.QLabel(
                "还没有添加壁纸。点下面的「添加图片…」，把图片复制到\n"
                f"{resources.user_wallpaper_dir()}\n"
                "就会出现在这里 —— 这个目录是持久的，重启 exe 不会丢。\n"
                "（软件不附带插画壁纸，默认使用程序生成的初音配色星空背景。）",
                self.wall_box)
            empty.setFont(theme.font(8.8, 400))
            empty.setWordWrap(True)
            empty.setStyleSheet(
                "color: #BFE9FF; background: rgba(46,139,255,0.14);"
                "border: 1px dashed rgba(140,220,255,0.32); border-radius: 10px; padding: 12px;")
            self.wall_lay.addWidget(empty, 0, 0)

        wall_tools = QtWidgets.QHBoxLayout()
        wall_tools.setSpacing(8)
        btn_add = PillButton("添加图片…", "plus", "primary", box, scale=0.9)
        btn_add.setToolTip("从磁盘挑选图片，复制到用户壁纸目录")
        btn_add.clicked.connect(self._import_wallpapers)
        wall_tools.addWidget(btn_add)

        btn_folder = PillButton("打开壁纸文件夹", "download", "ghost", box, scale=0.9)
        btn_folder.setToolTip(str(resources.user_wallpaper_dir()))
        btn_folder.clicked.connect(self._open_wallpaper_dir)
        wall_tools.addWidget(btn_folder)

        btn_reset = PillButton("用默认背景", "image", "ghost", box, scale=0.9)
        btn_reset.setToolTip("回到程序生成的初音配色星空背景")
        btn_reset.clicked.connect(lambda: self._set_wallpaper(resources.KEY_DEFAULT))
        wall_tools.addWidget(btn_reset)
        wall_tools.addStretch(1)
        lay.addWidget(self.wall_box)
        lay.addLayout(wall_tools)

        self.scrim = QtWidgets.QSlider(QtCore.Qt.Horizontal, box)
        self.scrim.setRange(0, 85)
        self.scrim.setValue(int(float(self.user.get("scrim", 0.52)) * 100))
        self.scrim.setFixedWidth(190)
        self.scrim.valueChanged.connect(lambda v: self.user.set("scrim", v / 100.0))
        lay.addWidget(row("背景压暗", self.scrim, "壁纸太亮时调高，文字更清晰。", box))

        self.blur = QtWidgets.QSlider(QtCore.Qt.Horizontal, box)
        self.blur.setRange(0, 30)
        self.blur.setValue(int(float(self.user.get("blur", 0.0))))
        self.blur.setFixedWidth(190)
        self.blur.valueChanged.connect(lambda v: self.user.set("blur", float(v)))
        lay.addWidget(row("背景模糊", self.blur, "0 = 完全清晰。", box))

        self.font_scale = QtWidgets.QSlider(QtCore.Qt.Horizontal, box)
        self.font_scale.setRange(80, 150)
        self.font_scale.setValue(int(float(self.user.get("font_scale", 1.0)) * 100))
        self.font_scale.setFixedWidth(190)
        self.font_scale.valueChanged.connect(lambda v: self.user.set("font_scale", v / 100.0))
        lay.addWidget(row("界面缩放", self.font_scale, "整体放大标签与文字。", box))
        self.body.addWidget(box)

        # ---- 标签显示
        box2, lay2 = card("标签显示")
        self.chip_mode = QtWidgets.QComboBox(box2)
        for key, label in (("both", "英文 + 中文"), ("en", "仅英文"), ("zh", "仅中文")):
            self.chip_mode.addItem(label, key)
        idx = max(0, self.chip_mode.findData(self.user.get("chip_mode", "both")))
        self.chip_mode.setCurrentIndex(idx)
        self.chip_mode.currentIndexChanged.connect(
            lambda i: self.user.set("chip_mode", self.chip_mode.itemData(i)))
        lay2.addWidget(row("标签文字", self.chip_mode, "提示词复制时始终使用英文。", box2))

        self.show_count = ToggleSwitch(box2, checked=bool(self.user.get("show_counts", True)))
        self.show_count.toggled.connect(lambda v: self.user.set("show_counts", bool(v)))
        lay2.addWidget(row("显示投稿量", self.show_count, "分类型里的热度参考。", box2))

        self.confirm_clear = ToggleSwitch(box2, checked=bool(self.user.get("confirm_clear", True)))
        self.confirm_clear.toggled.connect(lambda v: self.user.set("confirm_clear", bool(v)))
        lay2.addWidget(row("清空前确认", self.confirm_clear, "", box2))
        self.body.addWidget(box2)

        # ---- 内容
        box3, lay3 = card("内容分级", "R18 标签默认隐藏，只有打开开关后才会出现在分类与搜索结果里。")
        self.r18 = ToggleSwitch(box3, checked=bool(self.user.get("r18", False)),
                                on_color="#FF5C8A")
        self.r18.toggled.connect(lambda v: self.user.set("r18", bool(v)))
        lay3.addWidget(row("显示 R18 标签", self.r18,
                           "默认关闭。打开后会多出 R18 分类，搜索结果也会包含相关内容。", box3))
        warn = QtWidgets.QLabel("⚠ 打开后可能出现成人向内容，请确认你已成年并自行斟酌。", box3)
        warn.setFont(theme.font(8.4, 400))
        warn.setStyleSheet("color: rgba(255,150,170,0.9); background: transparent;")
        lay3.addWidget(warn)
        self.body.addWidget(box3)

        # ---- 复制
        box4, lay4 = card("复制格式", "点击「复制全部」时，标签之间的连接方式。")
        self.fmt = QtWidgets.QComboBox(box4)
        for key, label in COPY_FORMATS:
            self.fmt.addItem(label, key)
        self.fmt.setCurrentIndex(max(0, self.fmt.findData(self.user.get("copy_format", "comma"))))
        self.fmt.currentIndexChanged.connect(self._format_changed)
        lay4.addWidget(row("分隔方式", self.fmt, "", box4))
        self.preview = QtWidgets.QLabel("", box4)
        self.preview.setFont(theme.font(9, 400, mono=True))
        self.preview.setWordWrap(True)
        self.preview.setStyleSheet(
            "color: #BFE9FF; background: rgba(0,0,0,0.28); border-radius: 9px; padding: 8px;")
        lay4.addWidget(self.preview)
        self._update_preview()
        self.body.addWidget(box4)

        # ---- 数据
        box5, lay5 = card("数据", "自定义标签与预设都保存在下面这个目录里，删掉软件也不会丢。")
        path_label = QtWidgets.QLabel(str(self.user.dir), box5)
        path_label.setFont(theme.font(8.6, 400, mono=True))
        path_label.setWordWrap(True)
        path_label.setStyleSheet("color: #BFE9FF; background: rgba(0,0,0,0.24);"
                                 "border-radius: 8px; padding: 7px;")
        lay5.addWidget(path_label)
        rr = QtWidgets.QHBoxLayout()
        rr.addStretch(1)
        btn_open = PillButton("打开目录", "download", "ghost", box5, scale=0.9)
        btn_open.clicked.connect(self._open_dir)
        rr.addWidget(btn_open)
        btn_reset = PillButton("恢复默认设置", "trash", "danger", box5, scale=0.9)
        btn_reset.clicked.connect(self._reset)
        rr.addWidget(btn_reset)
        lay5.addLayout(rr)

        stats = self.db.stats()
        index_state = "已就绪" if stats["full_ready"] else "后台加载中"
        info = QtWidgets.QLabel(
            "核心标签 {:,} 个 · 分类 {} 个 · 全量索引 {:,} 条（{}）".format(
                stats["core"], stats["categories"], stats["full"], index_state),
            box5)
        info.setFont(theme.font(8.6, 400))
        info.setStyleSheet(f"color: {theme.TEXT_DIM}; background: transparent;")
        lay5.addWidget(info)
        self.body.addWidget(box5)

        self.refresh_wallpaper()
        self.body.addStretch(1)

    # ------------------------------------------------------------
    def _set_wallpaper(self, key: str) -> None:
        """key 是稳定标识（user:xxx / builtin:xxx / 空串=默认背景）。"""
        self.user.set("wallpaper", key)
        self.refresh_wallpaper()

    def refresh_wallpaper(self, allow_reload: bool = True) -> None:
        """同步缩略图的选中状态。

        注意：**不能**只拿手里的 _thumbs 判断 key 是否有效 —— 刚导入的图片
        还没进列表，会被误判成"失效"然后把设置清掉（这个 bug 真发生过）。
        所以先重建一次缩略图再判断，只有确实不存在时才回落到默认背景。
        """
        current = str(self.user.get("wallpaper", "") or "")
        if current and current not in {t.key for t in self._thumbs}:
            if allow_reload:
                self.reload_wallpapers()
                return
            self.user.set("wallpaper", resources.KEY_DEFAULT)
            current = resources.KEY_DEFAULT
        for thumb in self._thumbs:
            thumb.set_active(thumb.key == current)

    def reload_wallpapers(self) -> None:
        """重新扫描壁纸目录并重建缩略图（导入新图片后调用）。"""
        while self.wall_lay.count():
            item = self.wall_lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        self._thumbs.clear()

        for i, item in enumerate(resources.wallpaper_files()):
            badge = "我的" if item.user else ""
            thumb = WallpaperThumb(item.label, item.key, item.path, self.wall_box, badge=badge)
            thumb.clicked.connect(lambda _=False, k=item.key: self._set_wallpaper(k))
            self.wall_lay.addWidget(thumb, i // 4, i % 4)
            self._thumbs.append(thumb)
        if not self._thumbs:
            empty = QtWidgets.QLabel(
                "还没有添加壁纸，点下面的「添加图片…」就能加进来。", self.wall_box)
            empty.setFont(theme.font(8.8, 400))
            empty.setWordWrap(True)
            empty.setStyleSheet(
                "color: #BFE9FF; background: rgba(46,139,255,0.14);"
                "border: 1px dashed rgba(140,220,255,0.32); border-radius: 10px; padding: 12px;")
            self.wall_lay.addWidget(empty, 0, 0)
        self.refresh_wallpaper(allow_reload=False)

    def _import_wallpapers(self) -> None:
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "选择壁纸图片", str(Path.home()),
            "图片 (*.jpg *.jpeg *.png *.webp *.bmp);;所有文件 (*)")
        if not paths:
            return
        imported: list[str] = []
        for raw in paths:
            item = resources.import_wallpaper(Path(raw))
            if item is not None:
                imported.append(item.label)
        if not imported:
            self._toast.emit("没有导入任何图片", "格式不支持或复制失败", "info")
            return
        self.reload_wallpapers()
        # 导入后直接应用第一张，用户马上能看到效果
        first = next((t for t in self._thumbs if t.label == imported[0]), None)
        if first is not None:
            self._set_wallpaper(first.key)
        self._toast.emit(f"已导入 {len(imported)} 张壁纸", "、".join(imported[:3]), "image")

    def _open_wallpaper_dir(self) -> None:
        self._open_path(str(resources.user_wallpaper_dir()))

    def _format_changed(self, index: int) -> None:
        self.user.set("copy_format", self.fmt.itemData(index))
        self._update_preview()

    def _update_preview(self) -> None:
        from ..main_window import format_tags  # 延迟导入避免循环
        demo = ["1girl", "long_hair", "blue_eyes", "school_uniform"]
        self.preview.setText(format_tags(demo, self.user.get("copy_format", "comma")))

    def _open_path(self, path: str) -> None:
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    def _open_dir(self) -> None:
        self._open_path(str(self.user.dir))

    def _reset(self) -> None:
        from ..user_data import DEFAULT_SETTINGS
        for key, value in DEFAULT_SETTINGS.items():
            if key == "window":
                continue
            self.user.set(key, value, save=False)
        self.user.save_settings()
        self.scrim.setValue(int(DEFAULT_SETTINGS["scrim"] * 100))
        self.blur.setValue(int(DEFAULT_SETTINGS["blur"]))
        self.font_scale.setValue(int(DEFAULT_SETTINGS["font_scale"] * 100))
        self.r18.setChecked(bool(DEFAULT_SETTINGS["r18"]))
        self.show_count.setChecked(bool(DEFAULT_SETTINGS["show_counts"]))
        self.confirm_clear.setChecked(bool(DEFAULT_SETTINGS["confirm_clear"]))
        self.fmt.setCurrentIndex(max(0, self.fmt.findData(DEFAULT_SETTINGS["copy_format"])))
        self.chip_mode.setCurrentIndex(max(0, self.chip_mode.findData(DEFAULT_SETTINGS["chip_mode"])))
        self.refresh_wallpaper()


# ==================================================================== 关于
class AboutPage(PageBase):
    def __init__(self, db, user, parent=None, scale: float = 1.0) -> None:
        super().__init__("关于", "ComfyUI_TagSelect · 简约的 AI 生图标签选择器", parent, scale)
        self.db = db
        self.user = user

        hero, hl = card()
        hero_lay = QtWidgets.QHBoxLayout()
        hero_lay.setSpacing(16)
        art = _ChibiArt(hero, 92)
        hero_lay.addWidget(art, 0, QtCore.Qt.AlignTop)
        text = QtWidgets.QVBoxLayout()
        text.setSpacing(6)
        t1 = QtWidgets.QLabel("ComfyUI_TagSelect", hero)
        t1.setFont(theme.font(14, 700))
        t1.setStyleSheet(f"color: {theme.TEXT_MAIN}; background: transparent;")
        text.addWidget(t1)
        ver = QtWidgets.QLabel(f"版本 v{__version__} · {__author__}", hero)
        ver.setFont(theme.font(8.8, 600))
        ver.setStyleSheet(f"color: {theme.MIKU_CYAN}; background: transparent;")
        text.addWidget(ver)
        body = QtWidgets.QLabel(
            "把 AI 生图常用的 tag 分门别类摆好，点一下就进上面的框，再点一下移出，"
            "最后按「复制全部」直接粘进 ComfyUI / NovelAI / WebUI。\n"
            "支持中文搜英文：输入「长发」就能找到 long_hair。", hero)
        body.setFont(theme.font(9.4, 400))
        body.setWordWrap(True)
        body.setStyleSheet(f"color: {theme.TEXT_DIM}; background: transparent;")
        text.addWidget(body)
        hero_lay.addLayout(text, 1)
        hl.addLayout(hero_lay)
        self.body.addWidget(hero)

        box2, lay2 = card("怎么用")
        steps = [
            ("1", "搜索或分类", "左上方搜索框支持中文和英文；也可以点分类胶囊逐类浏览。"),
            ("2", "点击选择", "点一下标签加入上方选择框，标签会变成蓝色；再点一下即移出。"),
            ("3", "复制全部", "右上角的「复制全部」把已选标签拼成提示词并放进剪贴板。"),
            ("4", "存成预设", "选择框里的「存为预设」，或到预设页保存当前选择，下次一键复用。"),
            ("5", "自定义标签", "数据库里没有的标签，可以在自定义标签页添加，之后能搜索、能选择。"),
        ]
        for num, title, desc in steps:
            lay2.addWidget(_step_row(num, title, desc, box2))
        self.body.addWidget(box2)

        box3, lay3 = card("快捷键")
        for key, desc in (("Ctrl + F", "聚焦搜索框"),
                          ("Ctrl + Shift + C", "复制全部已选标签"),
                          ("Esc", "清空搜索 / 取消聚焦"),
                          ("Ctrl + B", "收起或展开侧边栏"),
                          ("Ctrl + 1 ~ 5", "切换左侧页面")):
            lay3.addWidget(_kv_row(key, desc, box3))
        self.body.addWidget(box3)

        box4, lay4 = card("彩蛋 & 数据")
        egg = QtWidgets.QLabel(
            "· 点左下方那只小未来，会下一场大葱雨 🌱\n"
            "· 「39」是ミク的谐音，也是她最经典的应援数字\n"
            "· 背景壁纸可以在设置里随时切换\n"
            f"· 标签数据：核心 {self.db.stats()['core']:,} 个，全量索引 {self.db.stats()['full']:,} 条\n"
            "· 标签与中文翻译参考自 Danbooru 公开标签库", box4)
        egg.setFont(theme.font(9.2, 400))
        egg.setWordWrap(True)
        egg.setStyleSheet(f"color: {theme.TEXT_DIM}; background: transparent;")
        lay4.addWidget(egg)
        self.body.addWidget(box4)
        self.body.addStretch(1)


class _ChibiArt(QtWidgets.QWidget):
    def __init__(self, parent=None, size: int = 92) -> None:
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._t = 0.0
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(60)

    def _tick(self) -> None:
        self._t += 0.07
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        miku_art.draw_chibi(p, QtCore.QRectF(0, 0, self.width(), self.height()),
                            sway=0.8 * qsin(self._t))
        p.end()


def _step_row(num: str, title: str, desc: str, parent) -> QtWidgets.QWidget:
    w = QtWidgets.QWidget(parent)
    lay = QtWidgets.QHBoxLayout(w)
    lay.setContentsMargins(0, 2, 0, 2)
    lay.setSpacing(11)
    badge = QtWidgets.QLabel(num, w)
    badge.setFixedSize(22, 22)
    badge.setAlignment(QtCore.Qt.AlignCenter)
    badge.setFont(theme.font(9, 700))
    badge.setStyleSheet("color: #07131F; background: rgba(57,197,187,0.9); border-radius: 11px;")
    lay.addWidget(badge, 0, QtCore.Qt.AlignTop)
    box = QtWidgets.QVBoxLayout()
    box.setSpacing(1)
    t = QtWidgets.QLabel(title, w)
    t.setFont(theme.font(9.8, 600))
    t.setStyleSheet(f"color: {theme.TEXT_MAIN}; background: transparent;")
    d = QtWidgets.QLabel(desc, w)
    d.setFont(theme.font(8.8, 400))
    d.setWordWrap(True)
    d.setStyleSheet(f"color: {theme.TEXT_DIM}; background: transparent;")
    box.addWidget(t)
    box.addWidget(d)
    lay.addLayout(box, 1)
    return w


def _kv_row(key: str, desc: str, parent) -> QtWidgets.QWidget:
    w = QtWidgets.QWidget(parent)
    lay = QtWidgets.QHBoxLayout(w)
    lay.setContentsMargins(0, 1, 0, 1)
    lay.setSpacing(12)
    k = QtWidgets.QLabel(key, w)
    k.setFont(theme.font(8.8, 600, mono=True))
    k.setFixedWidth(120)
    k.setStyleSheet(
        "color: #BFE9FF; background: rgba(46,139,255,0.18);"
        "border: 1px solid rgba(140,220,255,0.24); border-radius: 7px; padding: 3px 8px;")
    lay.addWidget(k)
    d = QtWidgets.QLabel(desc, w)
    d.setFont(theme.font(9, 400))
    d.setStyleSheet(f"color: {theme.TEXT_DIM}; background: transparent;")
    lay.addWidget(d, 1)
    return w
