#!/usr/bin/env bash
# 构建 macOS 版 FuncLex（onedir .app）
#
# 用法:
#   ./packaging/build_mac.sh [arm|intel]
#     arm   = Apple Silicon (arm64)  [默认]
#     intel = Intel (x86_64)
#
# 关键点:
#   - PyInstaller 不能交叉编译，Intel 版需用 x86_64 的 Python（Rosetta 或 python.org x86_64 安装包）。
#     构建前用 PYTHON_BIN 指定：
#         PYTHON_BIN=/path/to/x86_64-python3 ./packaging/build_mac.sh intel
#   - 每个架构用独立 venv（$HOME/funlex-venv-arm / -intel），避免混用 wheel。
#   - 打包后应用数据目录为 ~/Library/Application Support/FuncLex/（词典、index.db、config 都在这）。
#
# 正式 icon 就绪: 把源图放 packaging/assets/icon.png 后运行（自动生成 icon.icns）。
set -euo pipefail
cd "$(dirname "$0")/.."

ARCH="${1:-arm}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV="$HOME/funlex-venv-${ARCH}"
ICON_ICNS="packaging/assets/icon.icns"

echo "==> 构建 macOS ${ARCH} 版（Python: $PYTHON_BIN，venv: $VENV）"

# 1) venv + 依赖
if [ ! -d "$VENV" ]; then
  "$PYTHON_BIN" -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install --quiet --upgrade pip pyinstaller pillow
"$VENV/bin/python" -m pip install --quiet -r requirements.txt python-lzo

# 2) 图标（若存在正式 icon.png 源图则重新生成）
if [ -f packaging/assets/icon.png ]; then
  "$VENV/bin/python" packaging/make_icons.py packaging/assets/icon.png packaging/assets
fi
if [ ! -f "$ICON_ICNS" ]; then
  echo "!! 缺少 icon.icns，将使用无图标构建。请准备 icon.png 并运行 make_icons.py。"
  ICON_ICNS=""
fi

# 3) PyInstaller onedir
ICON_ARGS=()
[ -n "$ICON_ICNS" ] && ICON_ARGS=(--icon "$ICON_ICNS")
"$VENV/bin/python" -m PyInstaller \
  --noconfirm --clean --onedir --windowed \
  --name FuncLex \
  --osx-bundle-identifier com.funlex.app \
  --paths . \
  --hidden-import lzo \
  --add-data "funlex/ui/assets:funlex/ui/assets" \
  --exclude-module PySide6.QtWebEngineCore \
  --exclude-module PySide6.QtWebEngineWidgets \
  "${ICON_ARGS[@]}" \
  app.py

# 4) 版本号写进 Info.plist（PyInstaller 默认 0.0.0）
VERSION=$("$VENV/bin/python" -c "import sys; sys.path.insert(0, '.'); from funlex import __version__; print(__version__)")
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString $VERSION" \
  -c "Set :CFBundleVersion $VERSION" dist/FuncLex.app/Contents/Info.plist 2>/dev/null || true

# 5) 尽力 ad-hoc 签名；失败则移除签名保持 app 可运行
#    注意：较新 macOS 会给文件打 com.apple.provenance（系统托管、用户态无法剥离），
#    会导致 codesign 报 "resource fork... not allowed"。此情况 app 未签名仍可正常使用。
xattr -cr dist/FuncLex.app 2>/dev/null || true
if codesign --force -s - dist/FuncLex.app 2>/dev/null; then
  echo "  ad-hoc 签名完成"
else
  codesign --remove-signature dist/FuncLex.app 2>/dev/null || true
  echo "  (未签名：本 macOS 的 com.apple.provenance 阻止签名，app 可正常运行)"
  echo "  分发提示: 用 Apple Developer 证书在无此限制的环境签名+公证，可免 Gatekeeper 弹窗。"
fi

echo "==> 完成: dist/FuncLex.app（v$VERSION）"
echo "    测试: open dist/FuncLex.app"
echo "    数据目录: ~/Library/Application Support/FuncLex/"
