"""主窗口 - 搜索栏 + 发音 + 多词典合并视图 + 历史侧边栏 + 状态栏

- 搜索时**同时显示所有词典**的释义（合并显示），顺序在设置里调整
- 每本词典一张可折叠玻璃卡片，折叠偏好沿用上次选择（config 持久化）
- 不再有词典切换下拉与等分视图
"""
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote, unquote
import sys

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QKeySequence
from PySide6.QtWidgets import (
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

from funlex.core.audio import MddAudioIndex
from funlex.core.config import ConfigManager
from funlex.core.dictionary import DictionaryService
from funlex.core.history import HistoryStore
from funlex.core.models import DictionaryEntry, PhraseItem
from funlex.core.parser import extract_audio_refs

from .build_worker import IndexBuildWorker
from .entry_view import EntryView
from .entry_view_merged import MergedEntryView
from .history_panel import HistoryPanel
from .pronounce import PronounceHelper
from .search_bar import SearchBar
from .settings_dialog import SettingsDialog

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
    icon.addFile(str(_ASSET_DIR / "speaker.svg"), QSize(20, 20), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addFile(str(_ASSET_DIR / "speaker_disabled.svg"), QSize(20, 20), QIcon.Mode.Disabled, QIcon.State.Off)
    return icon


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
        self._worker: Optional[IndexBuildWorker] = None

        # 注入合并显示顺序
        self.service.set_dictionary_order(self.config.dictionary_order)

        # 检测配套 .mdd 音频资源：存在则优先真实发音
        self._load_audio_index()

    def _load_audio_index(self) -> None:
        """查找 .mdd 并挂到发音助手；无则发音回退 TTS（并明确标注）"""
        try:
            mdd = self.service.find_audio_mdd()
            if mdd:
                index = MddAudioIndex(mdd)
                self.pronounce.set_audio_index(index)
                print(f"[FuncLex] 检测到音频资源：{mdd}（将优先播放原声）")
        except Exception as e:
            print(f"[FuncLex] 加载音频资源失败（回退 TTS）：{e}")

        self.setWindowTitle("FuncLex")
        self.resize(1100, 750)
        self.setMinimumSize(900, 600)

        self._build_ui()
        self._build_menu()
        self._connect_signals()
        self._apply_appearance()
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

        # header 行：发音按钮（右对齐）
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
        header.addStretch(1)
        header.addWidget(self.pronounce_btn)
        root.addLayout(header)

        # 内容区：状态页（占位/加载/未找到）+ 合并视图页
        self.main_split = QSplitter(Qt.Horizontal, central)
        self.main_split.setObjectName("mainSplit")

        self.stack = QStackedWidget(self.main_split)
        self.entry_view = EntryView(self.stack)          # 页 0：占位/加载/未找到
        self.merged_view = MergedEntryView(self.stack)   # 页 1：多词典合并显示
        self.stack.addWidget(self.entry_view)
        self.stack.addWidget(self.merged_view)
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
        self.act_toggle_history = QAction("历史侧边栏", self, checkable=True)
        self.act_toggle_history.setChecked(False)
        self.act_toggle_history.triggered.connect(self._on_toggle_history)
        view_menu.addAction(self.act_toggle_history)

    # ---------- 信号 ----------
    def _connect_signals(self) -> None:
        self.search_bar.searchRequested.connect(self._on_search)
        self.search_bar.textChangedDebounced.connect(self._on_text_changed_debounced)
        self.entry_view.anchorClicked.connect(self._on_anchor_clicked)
        self.merged_view.anchorClicked.connect(self._on_anchor_clicked)
        self.history_panel.wordClicked.connect(self._on_search)

    # ---------- 外观 ----------
    def _apply_appearance(self) -> None:
        """应用字号/字体到词条视图（配置即时生效）"""
        family = self.config.font_family or ""
        size = self.config.font_size or 14
        f = QFont(family, size)
        self.entry_view.setFont(f)
        self.merged_view.set_entry_font(f)

    # ---------- 词典初始化 ----------
    def _init_dictionaries(self) -> None:
        total = self.service.total_entries()
        pending = len(self.service.pending_builds())
        if total > 0:
            self.status.showMessage(
                f"已加载 {len(self.service.ordered_dictionaries())} 本词典，共 {total:,} 词条"
            )
        elif pending > 0:
            self.status.showMessage(f"首次运行：正在准备 {pending} 本词典的索引…")
        else:
            self.status.showMessage(
                "未找到任何 MDX 词典文件，请将 .mdx 放到项目根目录或 dictionaries/"
            )

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
        # 新词典索引就绪，当前词若有更多词典命中则刷新
        if self._current_word:
            self._on_search(self._current_word)

    def _on_all_finished(self) -> None:
        self._worker = None
        total = self.service.total_entries()
        self.status.showMessage(
            f"已加载 {len(self.service.ordered_dictionaries())} 本词典，共 {total:,} 词条"
        )

    # ---------- 槽 ----------
    def _show_state(self, method, *args) -> None:
        self.stack.setCurrentIndex(0)
        method(*args)

    def _on_search(self, word: str) -> None:
        word = word.strip()
        if not word:
            self._show_state(self.entry_view.show_placeholder)
            self._current_word = ""
            self.pronounce_btn.setEnabled(False)
            return

        # 索引尚未构建完成
        if not self.service.ordered_dictionaries() and self.service.pending_builds():
            self._show_state(self.entry_view.show_loading, word)
            self.status.showMessage("索引构建中，请稍候再试…")
            return

        entries = self.service.lookup_all(word)
        if not entries:
            self._show_state(self.entry_view.show_not_found, word)
            self.status.showMessage(f"未找到：{word}")
            self._current_word = ""
            self.pronounce_btn.setEnabled(False)
            return

        self._current_word = entries[0].word
        self._render_merged(entries)
        self.status.showMessage(f"已找到 {len(entries)} 本词典：{self._current_word}")

        # 发音按钮：标注发音来源（牛津原声 / TTS 合成）
        self.pronounce_btn.setEnabled(True)
        if self.pronounce.has_audio(self._current_word):
            tip = "朗读当前词（⌘P）· 牛津原声"
        else:
            tip = "朗读当前词（⌘P）· TTS 合成（非牛津原声）"
        self.pronounce_btn.setToolTip(tip)

        # 历史记录
        self.history.add(self._current_word, entries[0].dictionary_name)
        self.history_panel.refresh()

    def _render_merged(self, entries: List[DictionaryEntry]) -> None:
        counts = {i.name: i.entry_count for i in self.service.ordered_dictionaries()}
        items = [(e, counts.get(e.dictionary_name, 0)) for e in entries]
        related = self._related_html(entries)
        self.merged_view.show_entries(
            items,
            collapsed_names=tuple(self.config.collapsed_dictionaries),
            related_html=related,
            on_toggle=self._on_card_toggle,
        )
        self.stack.setCurrentIndex(1)

    def _on_card_toggle(self, name: str, collapsed: bool) -> None:
        """折叠偏好持久化到 config：下次查词沿用"""
        names = [n for n in self.config.collapsed_dictionaries if n != name]
        if collapsed:
            names.append(name)
        self.config_mgr.update(collapsed_dictionaries=names)

    def _related_html(self, entries: List[DictionaryEntry]) -> str:
        """聚合所有词典的短语/习语，去重后渲染为相关区块"""
        items: List[PhraseItem] = []
        seen = set()
        for e in entries:
            for p in e.phrasal_verbs + e.idioms:
                key = (p.kind, p.phrase.lower())
                if key not in seen:
                    seen.add(key)
                    items.append(p)
        if not items:
            return ""
        parts = ['<div class="related-title">相关短语动词 / 习语</div>', '<div class="related-items">']
        for p in items[:20]:
            safe = p.phrase.replace("&", "&amp;").replace('"', "&quot;")
            href = quote(p.phrase, safe="")
            parts.append(f'<a class="related-item" href="funlex://phrase/{href}">{safe}</a>')
        parts.append("</div>")
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
            key = s[len("sound://"):]
            self.pronounce.play_key(key, fallback_word=self._current_word)
            self.status.showMessage(f"发音：{self.pronounce.source_label()}")
            return
        if "://" in s or s.startswith("#"):
            return  # entry://、锚点等其他链接忽略
        if s:
            self._on_search(s)  # 裸词链接直接查询

    def _on_pronounce(self) -> None:
        if self._current_word:
            self.pronounce.speak(self._current_word, variant="gb")
            self.status.showMessage(f"发音：{self.pronounce.source_label()}")

    def _on_text_changed_debounced(self, text: str) -> None:
        if len(text.strip()) < 2:
            if not self.service.ordered_dictionaries():
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

    def _on_toggle_history(self, checked: bool) -> None:
        self.history_panel.setVisible(checked)

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self.config_mgr, self.service, self)
        dlg.applied.connect(self._on_settings_applied)
        dlg.exec()

    def _on_settings_applied(self) -> None:
        self.history.set_limit(self.config.history_limit)
        self._apply_appearance()
        self.service.set_dictionary_order(self.config.dictionary_order)
        # 词典顺序可能变化，重渲当前词
        if self._current_word:
            entries = self.service.lookup_all(self._current_word)
            if entries:
                self._render_merged(entries)

    def _focus_search(self) -> None:
        self.search_bar.setFocus()
