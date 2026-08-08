"""历史侧边栏 - QListWidget 展示查询历史，点击回查"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from funlex.core.history import HistoryStore


class HistoryPanel(QWidget):
    """右侧历史栏。

    - 点击条目 → wordClicked(word)
    - 右键菜单删除单条；顶部"清空"按钮
    - refresh() 从 HistoryStore 重读
    """

    wordClicked = Signal(str)

    def __init__(self, store: HistoryStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.setObjectName("historyPanel")
        self.setMinimumWidth(210)
        self.setMaximumWidth(320)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 10, 10, 0)
        root.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(10, 0, 4, 0)
        title = QLabel("查询历史")
        title.setObjectName("panelTitle")
        self._count_label = QLabel("0")
        self._count_label.setObjectName("panelCount")
        clear_btn = QPushButton("清空")
        clear_btn.setObjectName("panelClearBtn")
        clear_btn.setToolTip("清空全部历史")
        clear_btn.clicked.connect(self._on_clear)
        header.addWidget(title)
        header.addWidget(self._count_label)
        header.addStretch(1)
        header.addWidget(clear_btn)
        root.addLayout(header)

        self.list = QListWidget()
        self.list.setObjectName("historyList")
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.itemClicked.connect(self._on_clicked)
        self.list.customContextMenuRequested.connect(self._on_context_menu)
        root.addWidget(self.list, 1)

    # ---------- 公共 API ----------
    def refresh(self) -> None:
        self.list.clear()
        items = self.store.list()
        self._count_label.setText(str(len(items)))
        for it in items:
            li = QListWidgetItem(f"{it.word}   {it.time_str}")
            li.setData(Qt.UserRole, it.word)
            self.list.addItem(li)

    # ---------- 槽 ----------
    def _on_clicked(self, item: QListWidgetItem) -> None:
        w = item.data(Qt.UserRole)
        if w:
            self.wordClicked.emit(w)

    def _on_clear(self) -> None:
        self.store.clear()
        self.refresh()

    def _on_context_menu(self, pos) -> None:
        item = self.list.itemAt(pos)
        if item is None:
            return
        menu = QMenu(self)
        act = menu.addAction("删除该条")
        if menu.exec(self.list.mapToGlobal(pos)):
            w = item.data(Qt.UserRole)
            if w:
                self.store.delete(w)
                self.refresh()
