@echo off
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 没有找到 python，请先安装 Python 3.10 ~ 3.12 并加入 PATH。
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo 首次运行，正在创建虚拟环境并安装依赖 ...
    python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install --upgrade pip -q
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt -q
)

if not exist "assets\data\tags_core.json" (
    echo 正在生成标签数据，请稍候 ...
    ".venv\Scripts\python.exe" tools\build_data.py
)

echo 启动 ComfyUI_TagSelect ...
".venv\Scripts\python.exe" app.py
if errorlevel 1 pause
