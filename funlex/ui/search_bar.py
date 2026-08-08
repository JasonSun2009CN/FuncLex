"""搜索框组件 - QLineEdit 封装"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QWidget


class SearchBar(QWidget):
    """搜索框。

    信号：
    - searchRequested(str): 用户按回车或点击清除后请求搜索
    - textChangedDebounced(str): 文本变化（可后续接入 suggest）
    """

    searchRequested = Signal(str)
    textChangedDebounced = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("searchContainer")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        self.line_edit = QLineEdit(self)
        self.line_edit.setObjectName("searchInput")
        self.line_edit.setPlaceholderText("输入单词搜索...")
        self.line_edit.setClearButtonEnabled(False)  # 用自定义按钮
        self.line_edit.returnPressed.connect(self._on_return_pressed)
        self.line_edit.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.line_edit, 1)

        self.clear_btn = QPushButton("✕", self)
        self.clear_btn.setObjectName("clearButton")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setToolTip("清除")
        self.clear_btn.clicked.connect(self._on_clear_clicked)
        self.clear_btn.setVisible(False)
        layout.addWidget(self.clear_btn, 0)

    # ---------- 槽 ----------
    def _on_return_pressed(self) -> None:
        text = self.line_edit.text().strip()
        self.searchRequested.emit(text)

    def _on_text_changed(self, text: str) -> None:
        self.clear_btn.setVisible(bool(text))
        self.textChangedDebounced.emit(text)

    def _on_clear_clicked(self) -> None:
        self.line_edit.clear()
        self.line_edit.setFocus()

    # ---------- 公共 API ----------
    def text(self) -> str:
        return self.line_edit.text()

    def setText(self, text: str) -> None:
        self.line_edit.setText(text)

    def clear(self) -> None:
        self.line_edit.clear()

    def setFocus(self) -> None:  # type: ignore[override]
        self.line_edit.setFocus()
