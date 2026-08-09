"""应用配置读写 - 纯 Python，无 UI 依赖

配置文件默认放项目根目录 `config.json`，内容即 `AppConfig` 的 JSON 序列化。
读取时逐字段容错（缺字段/类型错误用默认值兜底），写入时保留未知字段不覆盖。
"""
from __future__ import annotations

import json
import os
from typing import Optional

from .models import AppConfig
from .paths import default_config_path

DEFAULT_CONFIG_FILENAME = "config.json"


class ConfigManager:
    """config.json 的读写器，持有 AppConfig 实例。

    - load(): 从磁盘读 JSON → AppConfig（失败或缺失则用全默认）
    - save(): 将当前 config 写回磁盘
    """

    def __init__(self, path: Optional[str] = None) -> None:
        # 默认路径：打包后为平台用户目录，开发为项目根（见 paths.py）
        self.path = path or default_config_path()
        self.config: AppConfig = self.load()

    # ---------- 读写 ----------
    def load(self) -> AppConfig:
        cfg = AppConfig()
        if not os.path.isfile(self.path):
            return cfg
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                cfg = AppConfig.from_dict(data)
        except (json.JSONDecodeError, OSError, TypeError) as e:
            # 配置损坏不阻塞启动，用默认值
            print(f"[ConfigManager] failed to load {self.path}: {e}")
        return cfg

    def save(self) -> None:
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.config.to_dict(), f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"[ConfigManager] failed to save {self.path}: {e}")

    # ---------- 便捷字段 ----------
    def update(self, **kwargs) -> None:
        """批量更新字段并立即落盘。"""
        for k, v in kwargs.items():
            if hasattr(self.config, k):
                setattr(self.config, k, v)
        self.save()
