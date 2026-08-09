"""设置对话框 - 编辑并持久化 config.json"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from funlex.core.config import ConfigManager
from funlex.core.dictionary import DictionaryService

_COMMON_FONTS = [
    "",
    "PingFang SC",
    "-apple-system",
    "Helvetica Neue",
    "Microsoft YaHei",
    "Courier New",
    "Times New Roman",
]

# 主题选项：(显示名, config 值)
_THEME_OPTIONS = [
    ("浅色", "light"),
    ("深色", "dark"),
    ("跟随系统", "system"),
]


class SettingsDialog(QDialog):
    """配置项：词典路径 / 词典显示顺序 / 历史条数 / 字号 / 字体。

    词典显示顺序即合并显示时各词典从上到下的顺序（上移=更靠前）。
    保存时写入 config.json 并 emit applied，主窗口据此即时生效。
    """

    applied = Signal()

    def __init__(
        self,
        config_mgr: ConfigManager,
        service: DictionaryService,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.config_mgr = config_mgr
        self.service = service
        self.setWindowTitle("设置")
        self.setMinimumWidth(500)
        self._build_ui()
        self._load_values()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        root.addWidget(QLabel("词典路径（新增路径需重启生效）"))
        self.paths_list = QListWidget()
        root.addWidget(self.paths_list)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        add_btn = QPushButton("添加…")
        rm_btn = QPushButton("移除")
        add_btn.clicked.connect(self._add_path)
        rm_btn.clicked.connect(self._remove_path)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(rm_btn)
        root.addLayout(btn_row)

        root.addWidget(QLabel("词典显示顺序（上→下，查词时同时显示）"))
        self.order_list = QListWidget()
        root.addWidget(self.order_list)
        order_row = QHBoxLayout()
        order_row.addStretch(1)
        up_btn = QPushButton("↑ 上移")
        down_btn = QPushButton("↓ 下移")
        up_btn.clicked.connect(self._move_up)
        down_btn.clicked.connect(self._move_down)
        order_row.addWidget(up_btn)
        order_row.addWidget(down_btn)
        root.addLayout(order_row)

        form = QFormLayout()
        form.setContentsMargins(0, 12, 0, 0)
        self.theme_combo = QComboBox()
        for label, _ in _THEME_OPTIONS:
            self.theme_combo.addItem(label)
        form.addRow("主题", self.theme_combo)

        self.history_limit = QSpinBox()
        self.history_limit.setRange(10, 10000)
        self.history_limit.setSuffix(" 条")
        form.addRow("历史条数", self.history_limit)

        self.font_size = QSpinBox()
        self.font_size.setRange(9, 28)
        self.font_size.setSuffix(" pt")
        form.addRow("字号", self.font_size)

        self.font_family = QComboBox()
        self.font_family.addItems(_COMMON_FONTS)
        form.addRow("字体", self.font_family)
        root.addLayout(form)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        self.buttons.accepted.connect(self._save)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

    # ---------- 数据 ----------
    def _load_values(self) -> None:
        cfg = self.config_mgr.config
        for p in cfg.dictionary_paths:
            self.paths_list.addItem(p)

        # 词典顺序：当前已配置顺序 + 未配置的按词条数倒序补全
        infos = self.service.list_dictionaries()
        by_name = {i.name: i for i in infos}
        ordered = [n for n in cfg.dictionary_order if n in by_name]
        for i in infos:
            if i.name not in ordered:
                ordered.append(i.name)
        for name in ordered:
            self.order_list.addItem(f"{name}  ({by_name[name].entry_count:,})")

        self.history_limit.setValue(cfg.history_limit)
        self.font_size.setValue(cfg.font_size)
        self.font_family.setCurrentText(cfg.font_family or "")
        theme = cfg.theme if cfg.theme in ("light", "dark", "system") else "light"
        idx = next((i for i, (_, v) in enumerate(_THEME_OPTIONS) if v == theme), 0)
        self.theme_combo.setCurrentIndex(idx)

    # ---------- 保存 ----------
    def _save(self) -> None:
        paths = [self.paths_list.item(i).text() for i in range(self.paths_list.count())]
        order = [
            self.order_list.item(i).text().split("  (")[0]
            for i in range(self.order_list.count())
        ]
        theme = _THEME_OPTIONS[self.theme_combo.currentIndex()][1]
        self.config_mgr.update(
            dictionary_paths=paths,
            dictionary_order=order,
            theme=theme,
            history_limit=self.history_limit.value(),
            font_family=self.font_family.currentText().strip(),
            font_size=self.font_size.value(),
        )
        self.applied.emit()
        self.accept()

    # ---------- 槽 ----------
    def _add_path(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择词典目录")
        if path:
            self.paths_list.addItem(path)

    def _remove_path(self) -> None:
        row = self.paths_list.currentRow()
        if row >= 0:
            self.paths_list.takeItem(row)

    def _move_up(self) -> None:
        self._move(-1)

    def _move_down(self) -> None:
        self._move(1)

    def _move(self, delta: int) -> None:
        row = self.order_list.currentRow()
        if row < 0:
            return
        new_row = row + delta
        if new_row < 0 or new_row >= self.order_list.count():
            return
        item = self.order_list.takeItem(row)
        self.order_list.insertItem(new_row, item)
        self.order_list.setCurrentRow(new_row)
