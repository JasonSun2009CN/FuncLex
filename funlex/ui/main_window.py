"""主窗口 - 顶部搜索栏 + 中间词条视图 + 底部状态栏"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QMainWindow,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from funlex.core.dictionary import DictionaryService
from funlex.core.models import DictionaryInfo

from .entry_view import EntryView
from .search_bar import SearchBar


class MainWindow(QMainWindow):
    """主窗口。持有 DictionaryService 引用，启动时 auto-load。"""

    def __init__(self, service: DictionaryService) -> None:
        super().__init__()
        self.service = service
        self.setWindowTitle("FuncLex")
        self.resize(1100, 750)
        self.setMinimumSize(900, 600)

        self._build_ui()
        self._connect_signals()
        self._init_dictionaries()

    # ---------- UI 构建 ----------
    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 顶部：搜索栏 + 词典切换
        self.search_bar = SearchBar(central)
        root.addWidget(self.search_bar)

        self.dict_selector = QComboBox(central)
        self.dict_selector.setObjectName("dictSelector")
        self.dict_selector.setToolTip("选择查询词典")
        # 把词典切换器放在 search_bar 右侧
        # 简单做法：直接在 root 加一行 header
        from PySide6.QtWidgets import QHBoxLayout
        header_container = QWidget(central)
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(16, 0, 16, 8)
        header_layout.setSpacing(8)
        header_layout.addStretch(1)
        header_layout.addWidget(self.dict_selector)
        root.addWidget(header_container)

        # 中间：词条视图
        self.entry_view = EntryView(central)
        root.addWidget(self.entry_view, 1)

        # 底部：状态栏
        self.status: QStatusBar = self.statusBar()
        self.status.showMessage("就绪")

        # 快捷键：聚焦搜索框 ⌘F / Ctrl+F
        focus_search = QAction("聚焦搜索", self)
        focus_search.setShortcut(QKeySequence.Find)
        focus_search.triggered.connect(self._focus_search)
        self.addAction(focus_search)

    def _connect_signals(self) -> None:
        self.search_bar.searchRequested.connect(self._on_search)
        self.search_bar.textChangedDebounced.connect(self._on_text_changed_debounced)
        self.dict_selector.currentIndexChanged.connect(self._on_dict_changed)

    # ---------- 初始化 ----------
    def _init_dictionaries(self) -> None:
        infos = self.service.list_dictionaries()
        if not infos:
            self.dict_selector.addItem("(无词典)", userData=None)
            self.status.showMessage("未找到任何 MDX 词典文件，请将 .mdx 放到项目根目录或 dictionaries/")
            return

        for info in infos:
            self.dict_selector.addItem(
                f"{info.name} ({info.entry_count:,})",
                userData=info.name,
            )
        self.dict_selector.setCurrentIndex(0)
        total = self.service.total_entries()
        self.status.showMessage(f"已加载 {len(infos)} 本词典，共 {total:,} 词条")

    # ---------- 槽 ----------
    def _on_search(self, word: str) -> None:
        if not word:
            self.entry_view.show_placeholder()
            return
        self.entry_view.show_loading(word)
        dict_name = self.dict_selector.currentData()
        entry = self.service.lookup(word, dict_name)
        if entry is None:
            self.entry_view.show_not_found(word)
            self.status.showMessage(f"未找到：{word}")
        else:
            self.entry_view.set_content(entry.raw_content, entry.word)
            self.status.showMessage(f"已找到：{entry.word}  [{entry.dictionary_name}]")

    def _on_text_changed_debounced(self, text: str) -> None:
        """输入时显示简单状态提示（MVP：仅在长度>=2 时显示匹配数）"""
        if len(text.strip()) < 2:
            self.status.showMessage("就绪")
            return
        suggestions = self.service.suggest(text.strip(), limit=1)
        if suggestions:
            count = len(self.service.suggest(text.strip(), limit=1000))
            self.status.showMessage(f'"{text}" 匹配到约 {count}+ 词条，按回车查询')
        else:
            self.status.showMessage(f'"{text}" 无匹配')

    def _on_dict_changed(self, _index: int) -> None:
        # 切换词典后自动重查当前输入
        text = self.search_bar.text().strip()
        if text:
            self._on_search(text)

    def _focus_search(self) -> None:
        self.search_bar.setFocus()

    # ---------- 公共 API ----------
    def selected_dictionary(self) -> Optional[DictionaryInfo]:
        name = self.dict_selector.currentData()
        if not name:
            return None
        for info in self.service.list_dictionaries():
            if info.name == name:
                return info
        return None
