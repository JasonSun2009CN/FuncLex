"""用户笔记 - SQLite 持久化（data/notes.db），纯 Python 无 UI 依赖

设计（与 HistoryStore 同风格）：
- 每词一条笔记，`word`（小写）为主键，天然去重、覆盖更新
- `save()` 传入空内容 = 删除该条（空笔记无意义）
- RLock 线程安全，兼容后台写入；排序字段为更新时间倒序
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
from typing import List, Optional

from .models import NoteItem


class NotesStore:
    def __init__(self, data_dir: str) -> None:
        os.makedirs(data_dir, exist_ok=True)
        self.db_path = os.path.join(data_dir, "notes.db")
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS notes ("
            " word    TEXT PRIMARY KEY,"
            " content TEXT NOT NULL,"
            " created REAL,"
            " updated REAL)"
        )
        self._conn.commit()

    def get(self, word: str) -> Optional[NoteItem]:
        """取某词笔记；无则 None。"""
        w = word.strip().lower()
        if not w:
            return None
        with self._lock:
            row = self._conn.execute(
                "SELECT word, content, created, updated FROM notes WHERE word=?",
                (w,),
            ).fetchone()
        if row is None:
            return None
        return NoteItem(
            word=row[0],
            content=row[1],
            created_at=row[2],
            updated_at=row[3],
        )

    def save(self, word: str, content: str) -> bool:
        """保存笔记；返回是否仍有内容（空内容则删除该条并返回 False）。"""
        w = word.strip().lower()
        content = content.strip()
        if not w:
            return False
        now = time.time()
        with self._lock:
            if not content:
                self._conn.execute("DELETE FROM notes WHERE word=?", (w,))
                self._conn.commit()
                return False
            self._conn.execute(
                "INSERT INTO notes(word, content, created, updated) VALUES (?,?,?,?) "
                "ON CONFLICT(word) DO UPDATE SET content=excluded.content, "
                "updated=excluded.updated",
                (w, content, now, now),
            )
            self._conn.commit()
        return True

    def delete(self, word: str) -> None:
        w = word.strip().lower()
        if not w:
            return
        with self._lock:
            self._conn.execute("DELETE FROM notes WHERE word=?", (w,))
            self._conn.commit()

    def list(self, limit: int = 500) -> List[NoteItem]:
        """全部笔记，按更新时间倒序。"""
        with self._lock:
            rows = self._conn.execute(
                "SELECT word, content, created, updated FROM notes "
                "ORDER BY updated DESC LIMIT ?",
                (max(limit, 1),),
            ).fetchall()
        return [
            NoteItem(word=r[0], content=r[1], created_at=r[2], updated_at=r[3])
            for r in rows
        ]

    def count(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) FROM notes").fetchone()
        return row[0] if row else 0
