"""多词典合并视图 - 各词典释义以可折叠玻璃卡片堆叠显示

- 每本命中词典一张卡片：标题 = 词典名 + 词条数 + 折叠箭头
- 固定展开、可点击折叠；折叠偏好由上层（config）传入并在查词时沿用
- 相关短语/习语以底部卡片形式出现一次
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from funlex.core.models import DictionaryEntry

from .styles import get_entry_default_css, sanitize_html


class AutoResizeTextBrowser(QTextBrowser):
    """随内容自动撑高的 QTextBrowser。

    卡片内部不出现滚动条：高度按文档排版所需动态计算（heightForWidth），
    整屏由外层 QScrollArea 统一滚动，保证卡片显示词条的全部内容。
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.document().setDocumentMargin(8)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        doc = self.document()
        doc.setTextWidth(max(width, 1))
        h = doc.size().height()
        # 文档高度 + 边框 + 少量余量，避免裁切
        return int(h) + self.frameWidth() * 2 + 8


class DictCard(QFrame):
    """单个词典的玻璃卡片：标题（词典名+词条数+箭头）+ 可折叠内容"""

    toggled = Signal(str, bool)  # (dict_name, collapsed)
    anchorClicked = Signal(QUrl)  # 转发内容区链接点击

    def __init__(
        self,
        name: str,
        count: int,
        html: str,
        collapsed: bool = False,
        font: Optional[QFont] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.name = name
        self._count = count
        self._collapsed = collapsed
        self.setObjectName("dictCard")

        self._body = AutoResizeTextBrowser(self)
        self._body.setObjectName("entryView")  # 复用词条玻璃卡片样式
        self._body.document().setDefaultStyleSheet(get_entry_default_css())
        self._body.setOpenExternalLinks(True)
        self._body.setOpenLinks(False)
        self._body.anchorClicked.connect(self.anchorClicked)
        if font is not None:
            self._body.setFont(font)
        self._body.setHtml(f"<body>{sanitize_html(html)}</body>")

        self._header = QPushButton(self)
        self._header.setObjectName("dictCardHeader")
        self._header.setCursor(Qt.PointingHandCursor)
        self._header.clicked.connect(self._on_header_clicked)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._header)
        layout.addWidget(self._body)

        self._refresh_header()
        self._body.setVisible(not collapsed)

    # ---------- 内部 ----------
    def _header_text(self) -> str:
        chevron = "▾" if not self._collapsed else "▸"
        return f"{chevron}  {self.name}  ({self._count:,})"

    def _refresh_header(self) -> None:
        self._header.setText(self._header_text())

    def _on_header_clicked(self) -> None:
        self.set_collapsed(not self._collapsed)
        self.toggled.emit(self.name, self._collapsed)

    # ---------- 公共 API ----------
    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        self._body.setVisible(not collapsed)
        self._refresh_header()

    def set_font(self, font: QFont) -> None:
        self._body.setFont(font)


class MergedEntryView(QScrollArea):
    """多词典合并显示：可折叠词典卡片纵向堆叠。"""

    anchorClicked = Signal(QUrl)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("mergedView")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(12, 12, 12, 12)
        self._layout.setSpacing(12)
        self.setWidget(self._container)

        self._cards: List[DictCard] = []
        self._on_toggle: Optional[Callable[[str, bool], None]] = None
        self._font: Optional[QFont] = None

    # ---------- 内部 ----------
    def _clear(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._cards.clear()

    def _on_card_toggled(self, name: str, collapsed: bool) -> None:
        if self._on_toggle is not None:
            self._on_toggle(name, collapsed)

    def _make_card(
        self,
        entry: DictionaryEntry,
        count: int,
        collapsed: bool,
    ) -> DictCard:
        card = DictCard(
            entry.dictionary_name,
            count,
            entry.raw_content,
            collapsed=collapsed,
            font=self._font,
        )
        card.toggled.connect(self._on_card_toggled)
        card.anchorClicked.connect(self.anchorClicked)
        return card

    # ---------- 公共 API ----------
    def set_entry_font(self, font: QFont) -> None:
        self._font = font
        for card in self._cards:
            card.set_font(font)

    def show_entries(
        self,
        items: List[Tuple[DictionaryEntry, int]],
        collapsed_names: tuple = (),
        related_html: str = "",
        on_toggle: Optional[Callable[[str, bool], None]] = None,
    ) -> None:
        """items = [(DictionaryEntry, 词典词条数), ...]，按显示顺序传入。"""
        self._clear()
        self._on_toggle = on_toggle
        collapsed_set = set(collapsed_names)
        for entry, count in items:
            card = self._make_card(entry, count, entry.dictionary_name in collapsed_set)
            self._layout.addWidget(card)
            self._cards.append(card)
        if related_html:
            card = self._make_related_card(related_html)
            self._layout.addWidget(card)
            self._cards.append(card)  # 纳入字体更新跟踪
        self._layout.addStretch(1)

    def _make_related_card(self, related_html: str) -> DictCard:
        # related_html 已是完整 related-block 区块；可折叠但不持久化（非词典）
        card = DictCard(
            "相关短语动词 / 习语",
            0,
            related_html,
            font=self._font,
        )
        card.anchorClicked.connect(self.anchorClicked)
        return card

    def show_empty(self, text: str = "输入单词开始查询") -> None:
        self._clear()
        label = QLabel(text)
        label.setObjectName("mergedPlaceholder")
        label.setAlignment(Qt.AlignCenter)
        self._layout.addWidget(label)
        self._layout.addStretch(1)
