"""FuncLex 应用入口"""
from __future__ import annotations

import os
import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox

from funlex.core.config import ConfigManager
from funlex.core.dictionary import DictionaryService
from funlex.ui.main_window import MainWindow
from funlex.ui.styles import get_main_qss


def _excepthook(exc_type, exc_value, exc_tb) -> None:
    """全局异常钩子，未捕获异常弹 QMessageBox"""
    msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print(msg, file=sys.stderr)
    try:
        QMessageBox.critical(None, "FuncLex 出错了", msg)
    except Exception:
        pass


def main() -> int:
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    sys.excepthook = _excepthook

    app = QApplication(sys.argv)
    app.setApplicationName("FuncLex")
    app.setOrganizationName("FuncLex")
    app.setStyleSheet(get_main_qss())

    # 配置（词典路径来自 config.json，未配置则走默认扫描目录）
    config_mgr = ConfigManager()
    paths = config_mgr.config.dictionary_paths or None

    try:
        service = DictionaryService(paths=paths)
    except Exception as e:
        QMessageBox.critical(None, "词典加载失败", f"无法初始化词典服务：\n{e}")
        return 1

    window = MainWindow(service, config_mgr)
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
