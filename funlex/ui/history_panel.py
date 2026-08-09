"""历史侧边栏 - 按日期分组 + 搜索过滤 + 点击回查

- 组：今天 / 昨天 / 7 天内 / 更早（组头可展开/折叠，含条数）
- 顶部搜索框按词过滤；过滤时扁平显示（组头收起）
- 点击词条 → wordClicked(word)；右键删除单条；顶部"清空"需确认
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from funlex.core.history import HistoryStore
from funlex.core.models import HistoryItem

_GROUP_ORDER = ["今天", "昨天", "7 天内", "更早"]


def _group_name(ts: float) -> str:
    """按时间戳分到 今天/昨天/7天内/更早"""
    days = (datetime.now().date() - datetime.fromtimestamp(ts).date()).days
    if days <= 0:
        return "今天"
    if days == 1:
        return "昨天"
    if days <= 7:
        return "7 天内"
    return "更早"


def _short_time(ts: float) -> str:
    """相对时间：今天 HH:MM / 昨天 / 更早 MM-DD"""
    dt = datetime.fromtimestamp(ts)
    days = (datetime.now().date() - dt.date()).days
    if days <= 0:
        return dt.strftime("%H:%M")
    if days == 1:
        return "昨天"
    return dt.strftime("%m-%d")


class HistoryPanel(QWidget):
    """右侧历史栏（分组 + 搜索）。

    - 点击词条 → wordClicked(word)
    - 右键删除单条；顶部"清空"确认后清空
    - refresh() 从 HistoryStore 重读并分组
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

        self.filter_edit = QLineEdit()
        self.filter_edit.setObjectName("historyFilter")
        self.filter_edit.setPlaceholderText("搜索历史…")
        self.filter_edit.setClearButtonEnabled(True)
        self.filter_edit.textChanged.connect(self._on_filter_changed)
        root.addWidget(self.filter_edit)

        self.list = QTreeWidget()
        self.list.setObjectName("historyList")
        self.list.setHeaderHidden(True)
        self.list.setRootIsDecorated(False)
        self.list.setIndentation(10)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.itemClicked.connect(self._on_clicked)
        self.list.customContextMenuRequested.connect(self._on_context_menu)
        root.addWidget(self.list, 1)

    # ---------- 数据 ----------
    def refresh(self) -> None:
        self.list.clear()
        items = self.store.list()
        q = self.filter_edit.text().strip().lower()
        if q:
            items = [it for it in items if q in it.word.lower()]
        self._count_label.setText(str(len(items)))

        if q:
            # 过滤态：扁平列表（无组头）
            for it in items:
                self.list.addTopLevelItem(self._make_word_item(it))
            return

        # 分组态
        groups: Dict[str, List[HistoryItem]] = {}
        for it in items:
            groups.setdefault(_group_name(it.timestamp), []).append(it)
        for name in _GROUP_ORDER:
            gitems = groups.get(name)
            if not gitems:
                continue
            group = QTreeWidgetItem([f"{name}  ({len(gitems)})"])
            group.setFlags(Qt.ItemIsEnabled)  # 组头不可选/不可交互
            group.setForeground(0, QColor("#8e8e93"))
            f = QFont()
            f.setBold(True)
            f.setPointSize(10)
            group.setFont(0, f)
            for it in gitems:
                group.addChild(self._make_word_item(it))
            self.list.addTopLevelItem(group)
            group.setExpanded(True)

    def _make_word_item(self, it: HistoryItem) -> QTreeWidgetItem:
        item = QTreeWidgetItem([f"{it.word}   {_short_time(it.timestamp)}"])
        item.setData(0, Qt.UserRole, it.word)
        detail = f"{it.dictionary_name or ''}\n{datetime.fromtimestamp(it.timestamp):%Y-%m-%d %H:%M}"
        item.setToolTip(0, detail.strip())
        return item

    # ---------- 槽 ----------
    def _on_filter_changed(self, _: str) -> None:
        self.refresh()

    def _on_clicked(self, item: QTreeWidgetItem) -> None:
        w = item.data(0, Qt.UserRole)
        if w:
            self.wordClicked.emit(w)

    def _on_clear(self) -> None:
        ret = QMessageBox.question(
            self,
            "清空历史",
            "确定清空全部查询历史吗？\n此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        self.store.clear()
        self.refresh()

    def _on_context_menu(self, pos) -> None:
        item = self.list.itemAt(pos)
        if item is None or not item.data(0, Qt.UserRole):
            return
        menu = QMenu(self)
        act = menu.addAction("删除该条")
        if menu.exec(self.list.mapToGlobal(pos)):
            w = item.data(0, Qt.UserRole)
            if w:
                self.store.delete(w)
                self.refresh()
