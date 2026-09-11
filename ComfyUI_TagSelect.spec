# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：生成单文件 ComfyUI_TagSelect.exe。

用法：
    pyinstaller ComfyUI_TagSelect.spec --noconfirm --clean

想改成"文件夹模式"（启动更快）：
    把下面的 ONEFILE 改成 False 再执行同样的命令。
"""

from pathlib import Path

ONEFILE = True
ROOT = Path(SPECPATH)  # noqa: F821  (PyInstaller 注入)

block_cipher = None

datas = [
    (str(ROOT / "assets" / "wallpapers"), "assets/wallpapers"),
    (str(ROOT / "assets" / "icons"), "assets/icons"),
    (str(ROOT / "assets" / "data"), "assets/data"),
]

hiddenimports = [
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    "PyQt5.QtWidgets",
]

# 这些库用不到，排掉可以显著减小体积
excludes = [
    "tkinter", "unittest", "pydoc_data", "test", "lib2to3",
    "numpy", "scipy", "pandas", "matplotlib", "PIL",
    "PyQt5.QtWebEngineWidgets", "PyQt5.QtQml", "PyQt5.QtQuick",
    "PyQt5.QtMultimedia", "PyQt5.QtNetwork", "PyQt5.QtSql",
    "PyQt5.QtTest", "PyQt5.QtBluetooth", "PyQt5.QtDesigner",
    "PyQt5.QtHelp", "PyQt5.QtLocation", "PyQt5.QtNfc",
    "PyQt5.QtOpenGL", "PyQt5.QtPositioning", "PyQt5.QtSensors",
    "PyQt5.QtSerialPort", "PyQt5.QtWebChannel", "PyQt5.QtWebSockets",
    "PyQt5.QtXml", "PyQt5.QtXmlPatterns",
]

a = Analysis(  # noqa: F821
    [str(ROOT / "app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

icon_path = str(ROOT / "assets" / "icons" / "app.ico")

if ONEFILE:
    exe = EXE(  # noqa: F821
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name="ComfyUI_TagSelect",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,   # 关闭 UPX：压缩后容易被杀毒软件误报
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_path,
    )
else:
    exe = EXE(  # noqa: F821
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="ComfyUI_TagSelect",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=False,   # 关闭 UPX：压缩后容易被杀毒软件误报
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_path,
    )
    coll = COLLECT(  # noqa: F821
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,   # 关闭 UPX：压缩后容易被杀毒软件误报
        name="ComfyUI_TagSelect",
    )
