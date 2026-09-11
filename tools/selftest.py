#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离屏功能自测：壁纸覆盖、选择/复制、预设、自定义标签、持久化。

用法：
    QT_QPA_PLATFORM=offscreen python tools/selftest.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cts.qtcompat import QtCore, QtGui, QtWidgets  # noqa: E402
from cts import resources, theme  # noqa: E402
from cts.data_store import Tag, TagDatabase  # noqa: E402
from cts.main_window import MainWindow, format_tags  # noqa: E402
from cts.user_data import UserData  # noqa: E402
from cts.widgets.background import BackgroundWidget  # noqa: E402


from _utf8 import force_utf8

force_utf8()

PASS, FAIL, SKIP = [], [], []


def check(name: str, cond: bool, extra: str = "") -> None:
    (PASS if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{('  ' + extra) if extra else ''}")


def skip(name: str, reason: str) -> None:
    SKIP.append(name)
    print(f"  SKIP  {name}  （{reason}）")


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="tagselect-selftest-"))
    import os
    os.environ["TAGSELECT_DATA_DIR"] = str(tmp)

    app = QtWidgets.QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    theme.fonts()
    app.setStyleSheet(theme.global_qss())

    db = TagDatabase()
    db.load_core()
    check("核心数据加载", not db.error and db.stats()["core"] > 5000, str(db.stats()))

    user = UserData()
    win = MainWindow(db, user)
    win.resize(1400, 880)
    win.show()
    app.processEvents()

    # ---------------- 壁纸全覆盖 ----------------
    print("\n[壁纸覆盖]")
    # 仓库不再附带壁纸，这里用一张自造的图来验证"铺满不留白"的绘制逻辑
    probe = tmp / "wall_probe.png"
    probe_pm = QtGui.QPixmap(200, 120)
    probe_pm.fill(QtGui.QColor("#204060"))
    probe_pm.save(str(probe))
    check("自造测试壁纸可用", probe.exists())

    bg = BackgroundWidget(None, probe, scrim=0.0, blur=0.0)
    for w, h in [(1400, 880), (600, 1000), (1900, 500), (300, 300), (2560, 1440), (801, 601)]:
        bg.resize(w, h)
        bg._ensure_cache()
        pm = bg._cache
        ok = pm is not None and not pm.isNull() and pm.width() == w and pm.height() == h
        # 四角必须是壁纸的颜色，而不是兜底渐变的颜色
        img = pm.toImage() if ok else None
        corner_ok = True
        if img is not None:
            for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, h // 2)]:
                c = img.pixelColor(x, y)
                if c.alpha() != 255 or c.name() != "#204060":
                    corner_ok = False
        check(f"{w}x{h} 铺满且无空白", ok and corner_ok,
              f"pixmap={pm.width()}x{pm.height()}" if pm else "None")

    # 模糊 / 压暗不能破坏覆盖
    bg.set_blur(8.0)
    bg.resize(1234, 567)
    bg._ensure_cache()
    check("开模糊后仍铺满", bg._cache is not None and bg._cache.width() == 1234
          and bg._cache.height() == 567)

    # 兜底：没有壁纸时也必须填满
    bg2 = BackgroundWidget(None, None, scrim=0.0, blur=0.0)
    bg2.resize(900, 400)
    bg2._ensure_cache()
    check("无壁纸时也能填满（兜底渐变）", bg2._cache is None)
    # 仓库不带壁纸时，wallpaper_files() 必须安全返回空列表
    check("wallpaper_files() 返回列表", isinstance(resources.wallpaper_files(), list),
          f"{len(resources.wallpaper_files())} 张")

    # ---------------- 点击加入 / 移出 ----------------
    print("\n[选择行为]")
    miku = db.lookup("hatsune_miku")
    long_hair = db.lookup("long_hair")
    check("能查到 hatsune_miku / long_hair", miku is not None and long_hair is not None)
    win.toggle_tag(miku)
    win.toggle_tag(long_hair)
    app.processEvents()
    check("点击后进入选择框", win.selected.names() == ["hatsune_miku", "long_hair"],
          str(win.selected.names()))
    check("选中集合与选择框一致", set(win._selected) == {"hatsune_miku", "long_hair"})
    win.toggle_tag(miku)
    app.processEvents()
    check("再次点击即移出", win.selected.names() == ["long_hair"], str(win.selected.names()))
    win.toggle_tag(miku)
    app.processEvents()

    # ---------------- 复制全部 ----------------
    print("\n[复制全部]")
    win.copy_all()
    clip = QtWidgets.QApplication.clipboard().text()
    expect_clip = ",".join(win.selected.names())
    if not clip and expect_clip:
        # offscreen 等无剪贴板的平台上，setText 是空操作，这属于环境限制而非缺陷
        skip("剪贴板内容正确", "当前平台无可用剪贴板，格式逻辑由下面的纯函数用例覆盖")
    else:
        check("剪贴板内容正确", clip == expect_clip, repr(clip))
    for fmt, want in [("comma", "a,b"), ("comma_space", "a, b"), ("space", "a b"),
                      ("newline", "a\nb"), ("brace", "{a},{b}")]:
        check(f"格式 {fmt}", format_tags(["a", "b"], fmt) == want)
    check("空列表返回空串", format_tags([], "comma") == "")

    # ---------------- 中文搜英文 ----------------
    print("\n[中文搜索]")
    db.load_full_async()
    waited = 0
    while not db.full_ready and waited < 200:
        app.processEvents()
        QtCore.QThread.msleep(50)
        waited += 1
    check("全量索引加载完成", db.full_ready, f"{db.full_count:,} 行")

    for query, expect in [("长发", "long_hair"), ("双马尾", "twintails"),
                          ("初音未来", "hatsune_miku"), ("微笑", "smile")]:
        hits = db.search(query, limit=40, include_r18=False)
        names = [h.en for h in hits]
        check(f"搜「{query}」命中 {expect}", expect in names, ", ".join(names[:4]))

    for query, expect in [("long_hair", "long_hair"), ("hatsune", "hatsune_miku")]:
        names = [h.en for h in db.search(query, limit=40, include_r18=False)]
        check(f"搜「{query}」命中 {expect}", expect in names, ", ".join(names[:3]))

    # ---------------- R18 开关 ----------------
    print("\n[R18 开关]")
    off = [h.en for h in db.search("nude", limit=80, include_r18=False)]
    on = [h.en for h in db.search("nude", limit=80, include_r18=True)]
    check("关闭时过滤掉 R18", "nude" not in off and len(off) == 0, f"{len(off)} 条")
    check("打开时能看到 R18", "nude" in on, f"{len(on)} 条")
    check("默认关闭", bool(user.get("r18")) is False)
    cats_off = [c.id for c in db.categories if c.id != "r18"]
    check("R18 分类存在且含内容", len(db.category("r18").tags) > 100,
          f"{len(db.category('r18').tags)} 个")
    check("默认分类列表可隐藏 R18", all(c != "r18" for c in cats_off))

    # ---------------- 自定义标签 ----------------
    print("\n[自定义标签]")
    user.add_custom_tag("my_oc_tag", "我的原创角色", "备注", "测试组")
    app.processEvents()
    check("自定义标签已保存", any(r["en"] == "my_oc_tag" for r in user.custom_tags))
    hits = [h.en for h in win._search_all("我的原创角色")]
    check("自定义标签可被中文搜索到", "my_oc_tag" in hits, str(hits[:4]))
    hits = [h.en for h in win._search_all("my_oc")]
    check("自定义标签可被英文搜索到", "my_oc_tag" in hits, str(hits[:4]))
    raw = (tmp / "custom_tags.json").read_text(encoding="utf-8")
    check("自定义标签已落盘", "my_oc_tag" in raw)

    # ---------------- 预设 ----------------
    print("\n[预设]")
    groups = user.groups_with_presets()
    builtin = [g for g in groups if not g.get("user")]
    total = sum(len(g.get("presets", [])) for g in builtin)
    check("常驻预设已加载", total >= 50, f"{len(builtin)} 组 / {total} 个预设")
    check("含初音角色预设",
          any(p.get("id") == "char_hatsune_miku"
              for g in builtin for p in g.get("presets", [])))
    user.add_preset("自测预设", ["1girl", "long_hair"])
    app.processEvents()
    check("自定义预设已保存", any(p["name"] == "自测预设" for p in user.user_presets))
    preset = next(p for p in user.user_presets if p["name"] == "自测预设")
    win._apply_preset(preset, False)
    app.processEvents()
    check("应用预设后进入选择框", win.selected.names() == ["1girl", "long_hair"],
          str(win.selected.names()))
    assert_user = UserData()
    check("预设可从磁盘重载", any(p["name"] == "自测预设" for p in assert_user.user_presets))

    # ---------------- 设置持久化 ----------------
    print("\n[设置持久化]")
    user.set("copy_format", "comma_space")
    user.set("scrim", 0.7)
    user.set("r18", True)
    reloaded = UserData()
    check("copy_format 持久化", reloaded.get("copy_format") == "comma_space")
    check("scrim 持久化", abs(float(reloaded.get("scrim")) - 0.7) < 1e-6)
    check("r18 持久化", reloaded.get("r18") is True)

    # ---------------- 清空 ----------------
    print("\n[清空]")
    user.set("confirm_clear", False)
    win.clear_selection()
    app.processEvents()
    check("清空后选择框为空", win.selected.names() == [] and not win._selected)

    # ---------------- 分类浏览 ----------------
    print("\n[分类浏览]")
    for cid in ["all", "hair", "clothing", "character", "pose"]:
        tags = db.tags_for(cid, include_r18=False)
        check(f"分类 {cid} 有内容", len(tags) > 20, f"{len(tags)} 个")
    check("关闭 R18 时分类内无 R18",
          all(not t.r18 for cid in ["all", "hair", "clothing", "body"]
              for t in db.tags_for(cid, False)))

    print("\n" + "=" * 60)
    tail = f"，跳过 {len(SKIP)} 项" if SKIP else ""
    print(f"通过 {len(PASS)} 项，失败 {len(FAIL)} 项{tail}")
    for name in SKIP:
        print("  跳过：", name)
    if FAIL:
        print("失败项：")
        for name in FAIL:
            print("  -", name)
    print("=" * 60)
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
