"""等分视图 - 按词性(POS)把词条拆成等宽面板（QSplitter）

拆分方式：在 raw HTML 中定位 `<span class="pos">` 标记，在标记处切分。
每块包含该词性下的全部释义/例句，第一个面板附带词头+音标头部。
未解析出多个词性（如韦氏、Collins）时退化为单面板展示全部内容。
"""
from __future__ import annotations

import re

from PySide6.QtCore import QUrl, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QSplitter, QTextBrowser

from funlex.core.models import DictionaryEntry
from .styles import get_entry_default_css, sanitize_html

_POS_SPAN_RE = re.compile(r'<span class="pos"[^>]*>', re.I)


class EntryViewSplit(QSplitter):
    """按词性拆分的等分视图。"""

    linkClicked = Signal(QUrl)

    def __init__(self, parent=None) -> None:
        super().__init__(Qt.Horizontal, parent)
        self.setObjectName("entryViewSplit")
        self.setChildrenCollapsible(True)
        self.setHandleWidth(6)
        self._font: QFont | None = None

    def set_entry_font(self, font: QFont) -> None:
        """记录词条字体，新面板创建时套用（配置字号即时生效）"""
        self._font = font
        for pane in self.widgets_list():
            pane.setFont(font)

    # ---------- 公共 API ----------
    def show_entry(self, entry: DictionaryEntry) -> None:
        self._clear()
        if not entry.raw_content:
            return
        segments = self._split_by_pos(sanitize_html(entry.raw_content))
        for seg in segments:
            pane = self._make_pane(seg)
            self.addWidget(pane)
        # 调整等宽
        if len(segments) > 1:
            for w in self.widgets_list():
                w.setMinimumWidth(240)

    def show_placeholder(self, text: str = "等分视图：按词性拆分（需词典支持）") -> None:
        self._clear()
        self.addWidget(self._make_pane(
            f'<body><div style="padding:40px;text-align:center;color:#8e8e93;'
            f'font-size:14px;">{text}</div></body>'
        ))

    def widgets_list(self):
        return [self.widget(i) for i in range(self.count())]

    # ---------- 内部 ----------
    def _clear(self) -> None:
        # QSplitter 没有 removeWidget：置空 parent 即从分栏分离
        while self.count():
            w = self.widget(0)
            w.setParent(None)
            w.deleteLater()

    def _make_pane(self, html: str) -> QTextBrowser:
        pane = QTextBrowser()
        pane.setObjectName("entryView")
        pane.document().setDefaultStyleSheet(get_entry_default_css())
        pane.setOpenExternalLinks(True)
        pane.setOpenLinks(False)
        if self._font is not None:
            pane.setFont(self._font)
        pane.anchorClicked.connect(self.linkClicked)
        pane.setHtml(html)
        return pane

    def _split_by_pos(self, html: str) -> list:
        positions = [m.start() for m in _POS_SPAN_RE.finditer(html)]
        if not positions:
            return [f"<body>{html}</body>"]
        header = html[: positions[0]]
        segments = []
        for i, p in enumerate(positions):
            end = positions[i + 1] if i + 1 < len(positions) else len(html)
            seg = html[p:end]
            body = (header + seg) if i == 0 else seg
            segments.append(f"<body>{body}</body>")
        return segments
