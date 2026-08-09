#!/usr/bin/env bash
# 构建 Linux 版 FuncLex（onedir），需在 Linux 上运行
#
# 用法: ./packaging/build_linux.sh
#
# 前置:
#   - python-lzo：Ubuntu 建议先 apt install liblzo2-dev（源码编译需要）
#   - QMediaPlayer(.mdd 发音) 依赖系统 GStreamer: apt install gstreamer1.0-plugins-base gstreamer1.0-plugins-good
#   - 打包后数据目录: ~/.local/share/FuncLex/
#
# 桌面集成（可选）: 用 dist/FuncLex/FuncLex 二进制 + packaging/assets/icon.png 建 .desktop 文件。
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV="$HOME/funlex-venv-linux"

echo "==> 构建 Linux 版（venv: $VENV）"

if [ ! -d "$VENV" ]; then
  "$PYTHON_BIN" -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --quiet --upgrade pip pyinstaller pillow
"$VENV/bin/python" -m pip install --quiet -r requirements.txt python-lzo

if [ -f packaging/assets/icon.png ]; then
  "$VENV/bin/python" packaging/make_icons.py packaging/assets/icon.png packaging/assets
fi

# Linux 的 --windowed 不改变产物（仍是控制台/无控制台均可，随 PySide6）；这里省略
"$VENV/bin/python" -m PyInstaller \
  --noconfirm --clean --onedir \
  --name FuncLex \
  --paths . \
  --hidden-import lzo \
  --add-data "funlex/ui/assets:funlex/ui/assets" \
  --add-data "dictionaries:dictionaries" \
  --exclude-module PySide6.QtWebEngineCore \
  --exclude-module PySide6.QtWebEngineWidgets \
  app.py

echo "==> 完成: dist/FuncLex/FuncLex"
echo "    数据目录: ~/.local/share/FuncLex/"
echo "    提示: QMediaPlayer 发音需系统 GStreamer（见文件头）"
