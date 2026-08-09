"""笔记卡片 - 内嵌在合并视图底部，随查词即时切换当前单词的笔记

交互：
- 输入即标记"未保存"，点"保存"或 ⌘S（Windows/Linux 为 Ctrl+S）落盘
- 切词时若编辑器有未保存改动，由主窗口自动保存
- "删除笔记"在有内容时出现：清除编辑器并删除该条
- 卡片只发信号不做持久化，主窗口持有 NotesStore 负责读写
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class NotesCard(QFrame):
    """我的笔记：标题 + 纯文本编辑器 + 保存/删除。

    信号：
    - saveRequested(str): 用户点保存（含空内容=删除该条）
    - deleteRequested(): 用户点删除
    """

    saveRequested = Signal(str)
    deleteRequested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("notesCard")
        self._word = ""
        self._saved_text = ""   # 最近一次已保存的内容（用于判定脏状态）
        self._build_ui()
        self._set_dirty(False)
        self._refresh_buttons()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 10)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setSpacing(8)
        self.title = QLabel("我的笔记")
        self.title.setObjectName("notesTitle")
        self.word_label = QLabel("")
        self.word_label.setObjectName("notesWord")
        self.dirty_label = QLabel("")
        self.dirty_label.setObjectName("notesDirty")
        header.addWidget(self.title)
        header.addWidget(self.word_label)
        header.addWidget(self.dirty_label)
        header.addStretch(1)
        layout.addLayout(header)

        self.editor = QTextEdit(self)
        self.editor.setObjectName("notesEdit")
        self.editor.setPlaceholderText("写下这个单词的笔记，如用法、例句、易错点…")
        self.editor.setAcceptRichText(False)  # 纯文本
        self.editor.setMaximumHeight(92)
        self.editor.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.editor)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        self.hint = QLabel("⌘S 保存（Windows/Linux Ctrl+S）")
        self.hint.setObjectName("notesHint")
        self.delete_btn = QPushButton("删除笔记")
        self.delete_btn.setObjectName("notesDeleteBtn")
        self.save_btn = QPushButton("保存")
        self.save_btn.setObjectName("notesSaveBtn")
        footer.addWidget(self.hint)
        footer.addStretch(1)
        footer.addWidget(self.delete_btn)
        footer.addWidget(self.save_btn)
        layout.addLayout(footer)

        self.save_btn.clicked.connect(self._on_save)
        self.delete_btn.clicked.connect(self._on_delete)
        QShortcut(QKeySequence.StandardKey.Save, self.editor, activated=self._on_save)

    # ---------- 内部 ----------
    def _on_text_changed(self) -> None:
        self._set_dirty(self.editor.toPlainText() != self._saved_text)
        self._refresh_buttons()

    def _set_dirty(self, dirty: bool) -> None:
        self.dirty_label.setText("未保存" if dirty else "")
        self.save_btn.setEnabled(dirty)

    def _refresh_buttons(self) -> None:
        has_text = bool(self.editor.toPlainText().strip())
        self.delete_btn.setVisible(has_text)
        self.save_btn.setEnabled(self._is_dirty())

    def _is_dirty(self) -> bool:
        return self.editor.toPlainText() != self._saved_text

    # ---------- 槽 ----------
    def _on_save(self) -> None:
        text = self.editor.toPlainText()
        self.saveRequested.emit(text)

    def _on_delete(self) -> None:
        self.deleteRequested.emit()

    # ---------- 公共 API ----------
    def set_word(self, word: str) -> None:
        """设置当前单词（显示在标题旁）；空串清空。"""
        self._word = word.strip()
        self.word_label.setText(f"· {self._word}" if self._word else "")

    def set_content(self, content: str | None) -> None:
        """填充编辑器内容并重置脏状态（程序化填充不触发 textChanged）。"""
        self._saved_text = (content or "").strip()
        self.editor.blockSignals(True)
        self.editor.setPlainText(self._saved_text)
        self.editor.blockSignals(False)
        self._set_dirty(False)
        self._refresh_buttons()

    def is_dirty(self) -> bool:
        return self._is_dirty()

    def current_text(self) -> str:
        return self.editor.toPlainText()

    @property
    def word(self) -> str:
        return self._word
