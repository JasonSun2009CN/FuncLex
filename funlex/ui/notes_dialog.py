"""所有笔记对话框 - 浏览/搜索/删除全部笔记，双击或"查询"回查单词

- 顶部搜索框按 词/内容 过滤
- 列表每条显示 单词 + 内容预览 + 更新时间；双击/查询 → wordChosen(word)
- 右键或按钮删除单条
"""
from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QVBoxLayout,
)

from funlex.core.notes import NotesStore


def _time_str(ts: float) -> str:
    """相对时间：刚刚 / N 分钟前 / N 小时前 / 昨天 / 日期"""
    dt = datetime.fromtimestamp(ts)
    now = datetime.now()
    if dt.date() == now.date():
        return dt.strftime("%H:%M")
    if dt.date() == (now - timedelta(days=1)).date():
        return "昨天 " + dt.strftime("%H:%M")
    return dt.strftime("%m-%d")


class NotesDialog(QDialog):
    """全部笔记列表。双击条目 → wordChosen(word)。"""

    wordChosen = Signal(str)

    def __init__(self, store: NotesStore, parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self.setWindowTitle("我的笔记")
        self.setMinimumSize(480, 420)
        self._build_ui()
        self.refresh()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("全部笔记")
        title.setObjectName("panelTitle")
        self._count_label = QLabel("")
        self._count_label.setObjectName("panelCount")
        self.filter_edit = QLineEdit()
        self.filter_edit.setObjectName("notesFilter")
        self.filter_edit.setPlaceholderText("搜索单词或内容…")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        header.addWidget(title)
        header.addWidget(self._count_label)
        header.addStretch(1)
        header.addWidget(self.filter_edit, 1)
        root.addLayout(header)

        self.list = QListWidget()
        self.list.setObjectName("notesList")
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.itemDoubleClicked.connect(self._on_query)
        self.list.customContextMenuRequested.connect(self._on_context_menu)
        root.addWidget(self.list, 1)

        footer = QHBoxLayout()
        self.open_btn = QPushButton("查询该词")
        self.delete_btn = QPushButton("删除选中")
        self.close_btn = QPushButton("关闭")
        footer.addStretch(1)
        footer.addWidget(self.open_btn)
        footer.addWidget(self.delete_btn)
        footer.addWidget(self.close_btn)
        root.addLayout(footer)

        self.open_btn.clicked.connect(lambda: self._query_current())
        self.delete_btn.clicked.connect(self._delete_current)
        self.close_btn.clicked.connect(self.accept)

    # ---------- 数据 ----------
    def refresh(self) -> None:
        self.list.clear()
        q = self.filter_edit.text().strip().lower()
        items = self.store.list()
        if q:
            items = [
                n for n in items
                if q in n.word.lower() or q in n.content.lower()
            ]
        self._count_label.setText(f"{len(items)}")
        for n in items:
            preview = n.content.replace("\n", " ").strip()
            if len(preview) > 60:
                preview = preview[:60] + "…"
            li = QListWidgetItem(f"{n.word}    ·    {preview}")
            li.setData(Qt.UserRole, n.word)
            li.setData(Qt.UserRole + 1, n.content)
            li.setData(Qt.UserRole + 2, _time_str(n.updated_at))
            li.setToolTip(f"{n.content}\n\n更新于 {datetime.fromtimestamp(n.updated_at):%Y-%m-%d %H:%M}")
            self.list.addItem(li)

    # ---------- 槽 ----------
    def _on_filter_changed(self, _: str) -> None:
        self.refresh()

    def _query_current(self) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        w = item.data(Qt.UserRole)
        if w:
            self.wordChosen.emit(w)
            self.accept()

    def _on_query(self, item: QListWidgetItem) -> None:
        w = item.data(Qt.UserRole)
        if w:
            self.wordChosen.emit(w)
            self.accept()

    def _delete_current(self) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        w = item.data(Qt.UserRole)
        if w:
            self.store.delete(w)
            self.refresh()

    def _on_context_menu(self, pos) -> None:
        item = self.list.itemAt(pos)
        if item is None:
            return
        menu = QMenu(self)
        act = menu.addAction("查询该词")
        menu.addSeparator()
        del_act = menu.addAction("删除该条")
        chosen = menu.exec(self.list.mapToGlobal(pos))
        if chosen == act:
            w = item.data(Qt.UserRole)
            if w:
                self.wordChosen.emit(w)
                self.accept()
        elif chosen == del_act:
            w = item.data(Qt.UserRole)
            if w:
                self.store.delete(w)
                self.refresh()
