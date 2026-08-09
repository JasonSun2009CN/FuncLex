@echo off
REM 构建 Windows 版 FuncLex（onedir，需在 Windows 上运行）
REM 用法: build_windows.bat
REM
REM 前置:
REM   1. 安装 Python 3.11 (64位)，勾选 Add to PATH
REM   2. python-lzo 若 pip 装不上：conda install python-lzo 或装 Visual C++ Build Tools
REM   3. 正式 icon.png 放 packaging\assets\ 后自动生成 icon.ico
REM
REM 打包后数据目录: %APPDATA%\FuncLex\

cd /d "%~dp0.."

echo ==> 创建 venv + 安装依赖
if not exist "%USERPROFILE%\funlex-venv-win" (
  python -m venv "%USERPROFILE%\funlex-venv-win"
)
call "%USERPROFILE%\funlex-venv-win\Scripts\activate.bat"
python -m pip install --upgrade pip pyinstaller pillow
pip install -r requirements.txt
pip install python-lzo

echo ==> 生成图标
if exist packaging\assets\icon.png (
  python packaging\make_icons.py packaging\assets\icon.png packaging\assets
)

echo ==> PyInstaller onedir
set ICON_ARG=
if exist packaging\assets\icon.ico set ICON_ARG=--icon packaging\assets\icon.ico
python -m PyInstaller --noconfirm --clean --onedir --windowed ^
  --name FuncLex ^
  --paths . ^
  --hidden-import lzo ^
  --add-data "funlex/ui/assets;funlex/ui/assets" ^
  --exclude-module PySide6.QtWebEngineCore ^
  --exclude-module PySide6.QtWebEngineWidgets ^
  %ICON_ARG% ^
  app.py

echo.
echo ==> 完成: dist\FuncLex\FuncLex.exe
echo     数据目录: %%APPDATA%%\FuncLex\
pause
