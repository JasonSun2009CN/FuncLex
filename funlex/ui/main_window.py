"""主窗口 - 搜索栏 + 词典切换 + 发音 + 词条视图(默认/等分) + 历史侧边栏 + 状态栏"""
from __future__ import annotations

from pathlib import Path
from typing import Optional
from urllib.parse import quote, unquote
import sys

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

_UI_DIR = Path(__file__).parent
_ASSET_DIR = _UI_DIR / "assets"


def _glass_shadow(widget: QWidget, blur: int = 22, dy: int = 3, alpha: int = 30) -> None:
    """给控件挂柔和投影，强化玻璃浮起感（Liquid Glass）"""
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setColor(QColor(20, 24, 40, alpha))
    eff.setOffset(0, dy)
    widget.setGraphicsEffect(eff)


def _speaker_icon() -> QIcon:
    """发音按钮图标：启用态深色 / 禁用态浅灰（SVG，非 emoji）"""
    icon = QIcon()
    normal = str(_ASSET_DIR / "speaker.svg")
    disabled = str(_ASSET_DIR / "speaker_disabled.svg")
    icon.addFile(normal, QSize(20, 20), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addFile(disabled, QSize(20, 20), QIcon.Mode.Disabled, QIcon.State.Off)
    return icon

from funlex.core.config import ConfigManager
from funlex.core.dictionary import DictionaryService
from funlex.core.history import HistoryStore
from funlex.core.models import DictionaryEntry, DictionaryInfo

from .build_worker import IndexBuildWorker
from .entry_view import EntryView
from .entry_view_split import EntryViewSplit
from .history_panel import HistoryPanel
from .pronounce import PronounceHelper
from .search_bar import SearchBar
from .settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    """主窗口。持有 DictionaryService + ConfigManager，启动时自动加载 + 后台建索引。"""

    def __init__(
        self,
        service: DictionaryService,
        config_mgr: Optional[ConfigManager] = None,
    ) -> None:
        super().__init__()
        self.service = service
        self.config_mgr = config_mgr or ConfigManager()
        self.config = self.config_mgr.config
        self.history = HistoryStore(service.data_dir, limit=self.config.history_limit)
        self.pronounce = PronounceHelper(self)

        self._current_word = ""
        self._current_dict = ""
        self._worker: Optional[IndexBuildWorker] = None

        self.setWindowTitle("FuncLex")
        self.resize(1100, 750)
        self.setMinimumSize(900, 600)

        self._build_ui()
        self._build_menu()
        self._connect_signals()
        self._apply_appearance()
        self._apply_view_mode()  # 恢复上次会话的视图模式
        self._init_dictionaries()
        self._start_index_builds()

    # ---------- UI 构建 ----------
    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # 顶部：搜索栏（玻璃条 + 柔和投影）
        self.search_bar = SearchBar(central)
        root.addWidget(self.search_bar)
        _glass_shadow(self.search_bar, blur=22, dy=3, alpha=30)

        # header 行：发音按钮 + 词典切换
        header = QHBoxLayout()
        header.setContentsMargins(16, 0, 16, 8)
        header.setSpacing(8)
        self.pronounce_btn = QPushButton(central)
        self.pronounce_btn.setObjectName("pronounceBtn")
        self.pronounce_btn.setIcon(_speaker_icon())
        self.pronounce_btn.setIconSize(QSize(20, 20))
        self.pronounce_btn.setToolTip("朗读当前词（⌘P）")
        self.pronounce_btn.setCursor(Qt.PointingHandCursor)
        self.pronounce_btn.setEnabled(False)
        self.pronounce_btn.clicked.connect(self._on_pronounce)

        self.dict_selector = QComboBox(central)
        self.dict_selector.setObjectName("dictSelector")
        self.dict_selector.setToolTip("选择查询词典")
        header.addWidget(self.pronounce_btn)
        header.addStretch(1)
        header.addWidget(self.dict_selector)
        root.addLayout(header)

        # 中间：主分栏（词条视图 + 历史侧边栏）
        self.main_split = QSplitter(Qt.Horizontal, central)
        self.main_split.setObjectName("mainSplit")

        self.stack = QStackedWidget(self.main_split)
        self.entry_view = EntryView(self.stack)
        self.entry_view_split = EntryViewSplit(self.stack)
        self.stack.addWidget(self.entry_view)        # 页 0：默认视图
        self.stack.addWidget(self.entry_view_split)  # 页 1：等分视图
        self.main_split.addWidget(self.stack)

        self.history_panel = HistoryPanel(self.history, self.main_split)
        self.history_panel.setVisible(False)
        self.main_split.addWidget(self.history_panel)
        self.main_split.setStretchFactor(0, 1)
        self.main_split.setStretchFactor(1, 0)

        root.addWidget(self.main_split, 1)

        # 状态栏
        self.status: QStatusBar = self.statusBar()
        self.status.showMessage("就绪")

        # 快捷键（macOS 用 ⌘，其他平台用 Ctrl）
        mod = "Meta" if sys.platform == "darwin" else "Ctrl"
        focus_action = QAction("聚焦搜索", self)
        focus_action.setShortcut(QKeySequence.Find)
        focus_action.triggered.connect(self._focus_search)
        self.addAction(focus_action)

        pronounce_action = QAction("朗读", self)
        pronounce_action.setShortcut(QKeySequence(f"{mod}+P"))
        pronounce_action.triggered.connect(self._on_pronounce)
        self.addAction(pronounce_action)

    def _build_menu(self) -> None:
        mbar = self.menuBar()

        app_menu = mbar.addMenu("FuncLex")
        act_settings = QAction("设置…", self)
        act_settings.setShortcut(QKeySequence(QKeySequence.StandardKey.Preferences))
        act_settings.triggered.connect(self._open_settings)
        app_menu.addAction(act_settings)

        act_clear_history = QAction("清空历史", self)
        act_clear_history.triggered.connect(self.history_panel._on_clear)
        app_menu.addAction(act_clear_history)

        app_menu.addSeparator()
        act_quit = QAction("退出", self)
        act_quit.setShortcut(QKeySequence.Quit)
        act_quit.triggered.connect(self.close)
        app_menu.addAction(act_quit)

        view_menu = mbar.addMenu("视图")
        self.act_toggle_split = QAction("等分视图", self, checkable=True)
        self.act_toggle_split.setChecked(self.config.view_mode == "split")
        self.act_toggle_split.triggered.connect(self._on_toggle_split)
        view_menu.addAction(self.act_toggle_split)

        self.act_toggle_history = QAction("历史侧边栏", self, checkable=True)
        self.act_toggle_history.setChecked(False)
        self.act_toggle_history.triggered.connect(self._on_toggle_history)
        view_menu.addAction(self.act_toggle_history)

    # ---------- 信号 ----------
    def _connect_signals(self) -> None:
        self.search_bar.searchRequested.connect(self._on_search)
        self.search_bar.textChangedDebounced.connect(self._on_text_changed_debounced)
        self.dict_selector.currentIndexChanged.connect(self._on_dict_changed)
        self.entry_view.anchorClicked.connect(self._on_anchor_clicked)
        self.entry_view_split.linkClicked.connect(self._on_anchor_clicked)
        self.history_panel.wordClicked.connect(self._on_search)

    # ---------- 外观 ----------
    def _apply_appearance(self) -> None:
        """应用字号/字体到词条视图（配置即时生效）"""
        family = self.config.font_family or ""
        size = self.config.font_size or 14
        f = QFont(family, size)
        self.entry_view.setFont(f)
        self.entry_view_split.set_entry_font(f)

    def _apply_view_mode(self) -> None:
        split = self.config.view_mode == "split"
        self.stack.setCurrentIndex(1 if split else 0)
        if self.act_toggle_split is not None:
            self.act_toggle_split.setChecked(split)
        if split and not self._current_word:
            self.entry_view_split.show_placeholder()

    # ---------- 词典初始化 ----------
    def _init_dictionaries(self) -> None:
        self._reload_selector()
        total = self.service.total_entries()
        pending = len(self.service.pending_builds())
        if total > 0:
            self.status.showMessage(
                f"已加载 {len(self.service.list_dictionaries())} 本词典，共 {total:,} 词条"
            )
        elif pending > 0:
            self.status.showMessage(f"首次运行：正在准备 {pending} 本词典的索引…")
        else:
            self.status.showMessage(
                "未找到任何 MDX 词典文件，请将 .mdx 放到项目根目录或 dictionaries/"
            )

    def _reload_selector(self) -> None:
        """重建词典下拉（构建完成后调用），尽量保留当前选择"""
        current = self.dict_selector.currentData()
        self.dict_selector.blockSignals(True)
        self.dict_selector.clear()
        infos = self.service.list_dictionaries()
        if not infos:
            self.dict_selector.addItem("(无词典)", userData=None)
            self.dict_selector.setCurrentIndex(0)
            self.dict_selector.blockSignals(False)
            return
        for info in infos:
            self.dict_selector.addItem(
                f"{info.name} ({info.entry_count:,})", userData=info.name
            )
        # 优先恢复当前选择 / 配置的默认词典
        target = current or self.config.default_dictionary
        idx = self.dict_selector.findData(target)
        if idx >= 0:
            self.dict_selector.setCurrentIndex(idx)
        else:
            self.dict_selector.setCurrentIndex(0)
        self.dict_selector.blockSignals(False)

    # ---------- 后台索引构建 ----------
    def _start_index_builds(self) -> None:
        pending = self.service.pending_builds()
        if not pending or self._worker is not None:
            return
        self._worker = IndexBuildWorker(
            self.service, [i.name for i in pending], parent=self
        )
        self._worker.progress.connect(self._on_build_progress)
        self._worker.dict_finished.connect(self._on_dict_finished)
        self._worker.all_finished.connect(self._on_all_finished)
        self._worker.start()

    def _on_build_progress(self, name: str, done: int, total: int) -> None:
        self.status.showMessage(f"正在构建索引：{name}（{done:,}/{total:,}）")

    def _on_dict_finished(self, name: str, count: int) -> None:
        self._reload_selector()
        # 正在展示的词若属于该词典，重查以反映完整内容
        if self._current_word and name == self._current_dict:
            self._on_search(self._current_word)

    def _on_all_finished(self) -> None:
        self._worker = None
        total = self.service.total_entries()
        self.status.showMessage(
            f"已加载 {len(self.service.list_dictionaries())} 本词典，共 {total:,} 词条"
        )
        self._apply_view_mode()

    # ---------- 槽 ----------
    def _on_search(self, word: str) -> None:
        word = word.strip()
        if not word:
            self.entry_view.show_placeholder()
            self._current_word = ""
            self.pronounce_btn.setEnabled(False)
            return

        # 索引尚未构建完成
        if not self.service.list_dictionaries() and self.service.pending_builds():
            self.entry_view.show_loading(word)
            self.status.showMessage("索引构建中，请稍候再试…")
            return

        self.entry_view.show_loading(word)
        dict_name = self.dict_selector.currentData()
        entry = self.service.lookup(word, dict_name)

        if entry is None:
            self.entry_view.show_not_found(word)
            self.entry_view_split.show_placeholder()
            self.status.showMessage(f"未找到：{word}")
            self._current_word = ""
            self.pronounce_btn.setEnabled(False)
            return

        self._current_word = entry.word
        self._current_dict = entry.dictionary_name
        self._render_entry(entry)
        self.status.showMessage(
            f"已找到：{entry.word}  [{entry.dictionary_name}]"
        )
        # 发音按钮
        self.pronounce_btn.setEnabled(True)
        tip = "朗读当前词（⌘P）"
        if self.service.has_audio(entry.word):
            tip += " · 有 Collins 原声"
        self.pronounce_btn.setToolTip(tip)
        # 历史记录
        self.history.add(entry.word, entry.dictionary_name)
        self.history_panel.refresh()

    def _render_entry(self, entry: DictionaryEntry) -> None:
        related = self._related_html(entry)
        # 默认视图：原始 HTML + 相关短语区块
        self.entry_view.set_content(entry.raw_content + related, entry.word)
        # 等分视图：按词性拆分（不追加相关区块，避免重复）
        self.entry_view_split.show_entry(entry)
        self._apply_view_mode()

    def _related_html(self, entry: DictionaryEntry) -> str:
        items = entry.phrasal_verbs + entry.idioms
        if not items:
            return ""
        parts = ['<div class="related-block">']
        parts.append('<div class="related-title">相关短语动词 / 习语</div>')
        parts.append('<div class="related-items">')
        for p in items[:20]:
            safe = p.phrase.replace("&", "&amp;").replace('"', "&quot;")
            href = quote(p.phrase, safe="")
            parts.append(
                f'<a class="related-item" href="funlex://phrase/{href}">{safe}</a>'
            )
        parts.append("</div></div>")
        return "".join(parts)

    def _on_anchor_clicked(self, url: QUrl) -> None:
        s = url.toString()
        if s.startswith("funlex://phrase/"):
            self._on_search(unquote(s[len("funlex://phrase/"):]))
            return
        if s.startswith("bword://"):
            self._on_search(s[len("bword://"):])
            return
        if s.startswith("sound://"):
            self.status.showMessage("原声需要配套 .mdd 音频资源，暂不可播放")
            return
        if "://" in s or s.startswith("#"):
            return  # entry://、锚点等其他链接忽略
        if s:
            self._on_search(s)  # 裸词链接直接查询

    def _on_pronounce(self) -> None:
        if self._current_word:
            self.pronounce.speak(self._current_word)

    def _on_text_changed_debounced(self, text: str) -> None:
        if len(text.strip()) < 2:
            if not self.service.list_dictionaries():
                self.status.showMessage("索引构建中，请稍候…")
            else:
                self.status.showMessage("就绪")
            return
        suggestions = self.service.suggest(text.strip(), limit=1)
        if suggestions:
            count = len(self.service.suggest(text.strip(), limit=1000))
            self.status.showMessage(f'"{text}" 匹配到约 {count}+ 词条，按回车查询')
        else:
            self.status.showMessage(f'"{text}" 无匹配')

    def _on_dict_changed(self, _index: int) -> None:
        text = self.search_bar.text().strip()
        if text:
            self._on_search(text)

    def _on_toggle_split(self, checked: bool) -> None:
        self.config_mgr.update(view_mode="split" if checked else "default")
        self._apply_view_mode()
        # 切到等分视图时若已有词条，重渲染
        if checked and self._current_word:
            entry = self.service.lookup(self._current_word, self._current_dict)
            if entry:
                self._render_entry(entry)

    def _on_toggle_history(self, checked: bool) -> None:
        self.history_panel.setVisible(checked)

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.config_mgr, self.service, self)
        dlg.applied.connect(self._on_settings_applied)
        dlg.exec()

    def _on_settings_applied(self) -> None:
        self.history.set_limit(self.config.history_limit)
        self._apply_appearance()
        self._apply_view_mode()

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
