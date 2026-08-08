"""查询历史 - SQLite 持久化（data/history.db），纯 Python 无 UI 依赖"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
from typing import List, Optional

from .models import HistoryItem


class HistoryStore:
    """历史记录存储。

    - 同词去重：重复查询只把时间戳顶到最前
    - 超限裁剪：只保留最新的 limit 条
    - 线程安全（RLock，add 内会调用 _trim 需可重入），兼容后台写入
    """

    def __init__(self, data_dir: str, limit: int = 100) -> None:
        os.makedirs(data_dir, exist_ok=True)
        self.db_path = os.path.join(data_dir, "history.db")
        self.limit = max(limit, 1)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS history ("
            " word TEXT PRIMARY KEY, dict TEXT, ts REAL)"
        )
        self._conn.commit()

    def set_limit(self, limit: int) -> None:
        self.limit = max(limit, 1)
        self._trim()

    def add(self, word: str, dict_name: str = "") -> None:
        w = word.strip()
        if not w:
            return
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO history(word, dict, ts) VALUES (?,?,?)",
                (w, dict_name, time.time()),
            )
            self._conn.commit()
            self._trim()

    def list(self, limit: Optional[int] = None) -> List[HistoryItem]:
        lim = limit or self.limit
        with self._lock:
            rows = self._conn.execute(
                "SELECT word, dict, ts FROM history ORDER BY ts DESC LIMIT ?",
                (lim,),
            ).fetchall()
        return [HistoryItem(word=r[0], dictionary_name=r[1], timestamp=r[2]) for r in rows]

    def delete(self, word: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM history WHERE word=?", (word,))
            self._conn.commit()

    def clear(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM history")
            self._conn.commit()

    def count(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) FROM history").fetchone()
        return row[0] if row else 0

    def _trim(self) -> None:
        with self._lock:
            self._conn.execute(
                "DELETE FROM history WHERE word NOT IN ("
                " SELECT word FROM history ORDER BY ts DESC LIMIT ?)",
                (self.limit,),
            )
            self._conn.commit()
