"""路径策略 - 区分开发(源码运行)与打包(frozen)两种场景

开发：数据/配置/词典沿用项目根（`./data`、`./config.json`、根目录 + `dictionaries/`），
     与既有行为完全一致。
打包（PyInstaller frozen）：数据/配置/词典落到平台用户数据目录，避免依赖启动 CWD：

- macOS:   ~/Library/Application Support/FuncLex/
- Windows: %APPDATA%/FuncLex/
- Linux:   ~/.local/share/FuncLex/

纯 Python，无 UI 依赖。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List

APP_NAME = "FuncLex"


def is_frozen() -> bool:
    """是否运行在打包后的应用中（PyInstaller）"""
    return bool(getattr(sys, "frozen", False))


def user_data_dir() -> Path:
    """平台用户数据根目录（含应用名）"""
    if sys.platform == "darwin":
        base = Path(os.environ.get("HOME", ".")) / "Library" / "Application Support"
    elif os.name == "nt":
        base = Path(os.environ.get("APPDATA") or str(Path.home()))
    else:
        base = Path(
            os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        )
    return base / APP_NAME


def default_data_dir() -> str:
    """运行时数据目录（index.db / history.db / notes.db）"""
    if is_frozen():
        d = user_data_dir() / "data"
        d.mkdir(parents=True, exist_ok=True)
        return str(d)
    return os.path.join(os.getcwd(), "data")


def default_config_path() -> str:
    """config.json 路径"""
    if is_frozen():
        return str(user_data_dir() / "config.json")
    return os.path.join(os.getcwd(), "config.json")


def bundled_dictionary_dir() -> Path:
    """打包内置词库目录（PyInstaller onedir：--add-data 打入 sys._MEIPASS/dictionaries）。

    离线开箱即用：随安装包分发的 .mdx 就在这，只读、不可被用户改动。
    """
    if is_frozen():
        base = getattr(sys, "_MEIPASS", None)
        if base:
            d = Path(base) / "dictionaries"
            if d.is_dir():
                return d
    return Path()


def default_dictionary_dirs() -> List[str]:
    """默认词典扫描目录。

    打包(frozen)：内置词库(sys._MEIPASS/dictionaries) 优先 + 用户数据目录/dictionaries 扩充；
    开发：项目根 + dictionaries/。
    """
    if is_frozen():
        dirs: List[str] = []
        bundled = bundled_dictionary_dir()
        if bundled.is_dir():
            dirs.append(str(bundled))
        d = user_data_dir() / "dictionaries"
        d.mkdir(parents=True, exist_ok=True)
        dirs.append(str(d))
        return dirs
    cwd = os.getcwd()
    return [cwd, os.path.join(cwd, "dictionaries")]
