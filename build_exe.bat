@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo   ComfyUI_TagSelect  ^|  打包成单文件 exe
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 没有找到 python，请先安装 Python 3.10 ~ 3.12 并加入 PATH。
    echo        下载地址： https://www.python.org/downloads/
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] 创建虚拟环境 .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败。
        pause
        exit /b 1
    )
) else (
    echo [1/4] 复用已有的虚拟环境 .venv
)

set PY=.venv\Scripts\python.exe

echo [2/4] 安装依赖 ...
"%PY%" -m pip install --upgrade pip -q
"%PY%" -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络。
    pause
    exit /b 1
)

if not exist "assets\data\tags_core.json" (
    echo [3/4] 生成标签数据 ...
    "%PY%" tools\build_data.py
    if errorlevel 1 (
        echo [错误] 标签数据生成失败。
        pause
        exit /b 1
    )
) else (
    echo [3/4] 标签数据已存在，跳过生成。
)

echo [4/4] 正在打包，请稍候（首次大约 1~3 分钟）...
"%PY%" -m PyInstaller ComfyUI_TagSelect.spec --noconfirm --clean
if errorlevel 1 (
    echo [错误] 打包失败，请查看上面的日志。
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   完成！ exe 位于：  dist\ComfyUI_TagSelect.exe
echo   双击即可运行，不需要安装 Python。
echo ============================================================
echo.
pause
