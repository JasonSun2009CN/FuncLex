"""后台索引构建线程 - 首次运行构建 SQLite 索引，不阻塞 UI"""
from __future__ import annotations

from typing import List

from PySide6.QtCore import QThread, Signal

from funlex.core.dictionary import DictionaryService


class IndexBuildWorker(QThread):
    """按顺序构建各词典索引。

    信号（均在主线程槽内接收）：
    - progress(str, int, int): 词典名, 已处理, 总数
    - dict_finished(str, int): 词典名, 词条数
    - all_finished(): 全部完成
    """

    progress = Signal(str, int, int)
    dict_finished = Signal(str, int)
    dict_failed = Signal(str, str)  # (词典名, 错误信息)
    all_finished = Signal()

    def __init__(
        self, service: DictionaryService, names: List[str], parent=None
    ) -> None:
        super().__init__(parent)
        self.service = service
        self.names = names
        self._current = ""

    def run(self) -> None:
        for name in self.names:
            self._current = name
            try:
                count = self.service.build_index(name, progress_cb=self._cb)
                self.dict_finished.emit(name, count)
            except Exception as e:
                print(f"[IndexBuildWorker] failed to build {name}: {e}")
                self.dict_failed.emit(name, str(e))
        self.all_finished.emit()

    def _cb(self, done: int, total: int) -> None:
        self.progress.emit(self._current, done, total)
