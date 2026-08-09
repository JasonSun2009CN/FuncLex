"""搜索框组件 - QLineEdit + 防抖 + 浮动补全弹窗

交互：
- 输入停顿 150ms 后经 set_suggest_cb 拉取建议，弹出玻璃下拉（最多 8 条）
- 方向键↑↓ 在弹窗内移动选中；回车选中并搜索（或搜索当前输入）；Esc 关闭弹窗
- 点击建议条目直接搜索；建议命中后回填输入框
- 回车不在此拦截（交给 Qt returnPressed），避免破坏中文输入法组词确认
"""
from __future__ import annotations

from typing import Callable, List, Optional

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QWidget,
)

_DEFAULT_DEBOUNCE_MS = 150
_MAX_SUGGESTIONS = 8


class SuggestionLineEdit(QLineEdit):
    """搜索输入框：方向键/ Esc 交给 SearchBar 处理补全弹窗。

    信号：
    - navDown / navUp: 弹窗内移动选中
    - dismissRequested: Esc，关闭弹窗
    """

    navDown = Signal()
    navUp = Signal()
    dismissRequested = Signal()

    def keyPressEvent(self, e: QKeyEvent) -> None:
        k = e.key()
        if k == Qt.Key_Down:
            self.navDown.emit()
            e.accept()
            return
        if k == Qt.Key_Up:
            self.navUp.emit()
            e.accept()
            return
        if k == Qt.Key_Escape:
            self.dismissRequested.emit()
            e.accept()
            return
        super().keyPressEvent(e)


class SearchBar(QWidget):
    """搜索框。

    信号：
    - searchRequested(str): 用户按回车（含选中补全项）或点击补全项后请求搜索
    - textChangedDebounced(str): 防抖后的文本变化（供状态栏提示等）
    """

    searchRequested = Signal(str)
    textChangedDebounced = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("searchContainer")
        self._suggest_cb: Optional[Callable[[str], List[str]]] = None
        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        self.line_edit = SuggestionLineEdit(self)
        self.line_edit.setObjectName("searchInput")
        self.line_edit.setPlaceholderText("输入单词搜索...")
        self.line_edit.setClearButtonEnabled(False)  # 用自定义按钮
        self.line_edit.returnPressed.connect(self._on_return_pressed)
        self.line_edit.textChanged.connect(self._on_text_changed)
        self.line_edit.navDown.connect(lambda: self._on_nav(1))
        self.line_edit.navUp.connect(lambda: self._on_nav(-1))
        self.line_edit.dismissRequested.connect(self._on_dismiss)
        layout.addWidget(self.line_edit, 1)

        self.clear_btn = QPushButton("✕", self)
        self.clear_btn.setObjectName("clearButton")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setToolTip("清除")
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        self.clear_btn.setVisible(False)
        layout.addWidget(self.clear_btn, 0)

        # 防抖：停顿后再拉建议 / 发信号
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(_DEFAULT_DEBOUNCE_MS)
        self._debounce.timeout.connect(self._on_debounce_timeout)

        # 补全弹窗：浮动顶层窗口，不抢输入框焦点
        self._popup = QListWidget(self)
        self._popup.setObjectName("suggestPopup")
        self._popup.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowDoesNotAcceptFocus
        )
        self._popup.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._popup.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._popup.itemClicked.connect(self._on_suggestion_clicked)
        self._popup.hide()

    # ---------- 补全 ----------
    def set_suggest_cb(self, cb: Callable[[str], List[str]]) -> None:
        """注入建议来源：cb(prefix) -> 建议词列表（已限长）"""
        self._suggest_cb = cb

    def _on_debounce_timeout(self) -> None:
        text = self.line_edit.text()
        self.textChangedDebounced.emit(text)
        self._update_suggestions(text)

    def _update_suggestions(self, text: str) -> None:
        t = text.strip()
        if not t or self._suggest_cb is None:
            self._hide_popup()
            return
        words = self._suggest_cb(t)
        if not words:
            self._hide_popup()
            return
        self._popup.clear()
        for w in words[:_MAX_SUGGESTIONS]:
            item = QListWidgetItem(w)
            item.setData(Qt.UserRole, w)
            self._popup.addItem(item)
        self._popup.setCurrentRow(0)
        self._position_popup()
        self._popup.show()
        self._popup.raise_()

    def _position_popup(self) -> None:
        """弹窗定位在输入框下方，宽度对齐输入框（屏幕坐标）"""
        le = self.line_edit
        top_left = le.mapToGlobal(QPoint(0, le.height() + 6))
        w = le.width()
        n = self._popup.count()
        h = min(n * 30 + 10, 270)
        self._popup.setGeometry(top_left.x(), top_left.y(), w, h)

    def _hide_popup(self) -> None:
        if self._popup.isVisible():
            self._popup.hide()

    # ---------- 槽 ----------
    def _on_text_changed(self, text: str) -> None:
        self.clear_btn.setVisible(bool(text))
        self._debounce.start()

    def _on_return_pressed(self) -> None:
        text = self.line_edit.text().strip()
        sel = self._popup.currentItem()
        if self._popup.isVisible() and sel is not None:
            word = sel.data(Qt.UserRole) or sel.text().strip()
            if word:
                text = word
        self._hide_popup()
        if text:
            self.searchRequested.emit(text)

    def _on_clear_clicked(self) -> None:
        self.line_edit.clear()
        self._hide_popup()
        self.line_edit.setFocus()

    def _on_nav(self, delta: int) -> None:
        if not self._popup.isVisible() or self._popup.count() == 0:
            return
        row = self._popup.currentRow()
        new = max(0, min(row + delta, self._popup.count() - 1))
        self._popup.setCurrentRow(new)

    def _on_dismiss(self) -> None:
        self._hide_popup()

    def _on_suggestion_clicked(self, item: QListWidgetItem) -> None:
        w = item.data(Qt.UserRole)
        if w:
            self._commit(w)

    def _commit(self, word: str) -> None:
        """选中建议：回填输入框（不触发补全）并请求搜索。"""
        self._hide_popup()
        if not word:
            return
        self.line_edit.blockSignals(True)
        self.line_edit.setText(word)
        self.line_edit.blockSignals(False)
        self.clear_btn.setVisible(True)
        self.searchRequested.emit(word)

    # ---------- 公共 API ----------
    def text(self) -> str:
        return self.line_edit.text()

    def setText(self, text: str) -> None:
        self.line_edit.setText(text)

    def clear(self) -> None:
        self.line_edit.clear()

    def setFocus(self) -> None:  # type: ignore[override]
        self.line_edit.setFocus()

    def hide_popup(self) -> None:
        """外部发起搜索时隐藏弹窗。"""
        self._hide_popup()

    def popup_visible(self) -> bool:
        return self._popup.isVisible()
