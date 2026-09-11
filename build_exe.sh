#!/usr/bin/env bash
# Linux / macOS 上的打包脚本（Windows 请用 build_exe.bat）
set -euo pipefail
cd "$(dirname "$0")"

PY=${PYTHON:-python3}

if [ ! -d .venv ]; then
  echo "[1/4] 创建虚拟环境 .venv ..."
  "$PY" -m venv .venv
fi
PY=.venv/bin/python

echo "[2/4] 安装依赖 ..."
"$PY" -m pip install --upgrade pip -q
"$PY" -m pip install -r requirements.txt -q

if [ ! -f assets/data/tags_core.json ]; then
  echo "[3/4] 生成标签数据 ..."
  "$PY" tools/build_data.py
else
  echo "[3/4] 标签数据已存在，跳过生成。"
fi

echo "[4/4] 打包中 ..."
"$PY" -m PyInstaller ComfyUI_TagSelect.spec --noconfirm --clean

echo
echo "完成！可执行文件在 dist/ComfyUI_TagSelect"
