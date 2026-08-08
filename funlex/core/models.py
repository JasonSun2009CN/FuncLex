"""数据模型定义 - 纯 Python 数据类，无外部依赖"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import time


@dataclass
class DictionaryInfo:
    """词典文件信息"""
    name: str
    file_path: str
    entry_count: int = 0
    description: str = ""
    loaded: bool = False

    def __hash__(self):
        return hash(self.file_path)


@dataclass
class DictionaryEntry:
    """完整词条数据"""
    word: str
    dictionary_name: str
    raw_content: str = ""
    definition: str = ""
    phonetic_uk: str = ""
    phonetic_us: str = ""
    pos_tags: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    phrasal_verbs: List["PhraseItem"] = field(default_factory=list)
    idioms: List["PhraseItem"] = field(default_factory=list)


@dataclass
class PhraseItem:
    """短语动词 / 习语项"""
    phrase: str
    meaning: str = ""
    example: str = ""
    related_headword: str = ""
    kind: str = "phrasal_verb"  # phrasal_verb / idiom


@dataclass
class HistoryItem:
    """查询历史记录"""
    word: str
    timestamp: float = field(default_factory=time.time)
    dictionary_name: str = ""

    @property
    def time_str(self) -> str:
        from datetime import datetime
        return datetime.fromtimestamp(self.timestamp).strftime("%H:%M")


@dataclass
class NoteItem:
    """用户笔记"""
    word: str
    content: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class AppConfig:
    """应用配置"""
    dictionary_paths: List[str] = field(default_factory=list)
    default_dictionary: str = ""
    view_mode: str = "default"  # default / split
    theme: str = "light"  # light / dark
    history_limit: int = 100
    font_family: str = ""
    font_size: int = 14

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dictionary_paths": self.dictionary_paths,
            "default_dictionary": self.default_dictionary,
            "view_mode": self.view_mode,
            "theme": self.theme,
            "history_limit": self.history_limit,
            "font_family": self.font_family,
            "font_size": self.font_size,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        cfg = cls()
        for k, v in data.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        return cfg
