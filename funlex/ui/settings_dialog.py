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
    QRadioButton,
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


class SettingsDialog(QDialog):
    """配置项：词典路径（重启生效）/ 默认词典 / 视图模式 / 历史条数 / 字号 / 字体。

    保存时写入 config.json 并 emit applied，主窗口据此即时应用字号、视图模式等。
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
        self.setMinimumWidth(480)
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

        form = QFormLayout()
        form.setContentsMargins(0, 12, 0, 0)

        self.default_dict = QComboBox()
        form.addRow("默认词典", self.default_dict)

        vm_row = QHBoxLayout()
        self.view_default = QRadioButton("单栏顺序")
        self.view_split = QRadioButton("按词性等分")
        self.view_default.setToolTip("一个滚动视图展示全部词性内容")
        self.view_split.setToolTip("按词性拆分为等宽面板（需已解析出词性）")
        vm_row.addWidget(self.view_default)
        vm_row.addWidget(self.view_split)
        form.addRow("视图模式", vm_row)

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

        # 默认词典下拉：当前配置项 + 已加载词典
        self.default_dict.addItem(cfg.default_dictionary or "")
        for info in self.service.list_dictionaries():
            if info.name != cfg.default_dictionary:
                self.default_dict.addItem(info.name)
        self.default_dict.setCurrentText(cfg.default_dictionary or "")

        if cfg.view_mode == "split":
            self.view_split.setChecked(True)
        else:
            self.view_default.setChecked(True)

        self.history_limit.setValue(cfg.history_limit)
        self.font_size.setValue(cfg.font_size)
        self.font_family.setCurrentText(cfg.font_family or "")

    # ---------- 保存 ----------
    def _save(self) -> None:
        paths = [self.paths_list.item(i).text() for i in range(self.paths_list.count())]
        self.config_mgr.update(
            dictionary_paths=paths,
            default_dictionary=self.default_dict.currentText().strip(),
            view_mode="split" if self.view_split.isChecked() else "default",
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
