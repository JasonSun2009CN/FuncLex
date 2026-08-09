"""SQLite 索引 - 替代内存 dict，根治 Phase 1 启动慢/内存高

库文件：`data/index.db`（路径由上层传入，默认 ./data/index.db）

设计：
- `entries` 主键 `(dict, word)` WITHOUT ROWID → 前缀查询直接走 PK 范围扫描，零额外索引
- `meta` 存每本词典指纹（size+mtime）与词条数：MDX 未变更时启动只 stat，不打开文件
- `@@@LINK=` 跳转在 lookup 时同词典内解析（深度 ≤5），修复 Phase 1 不解析跳转的问题
- `phrases` 存短语 → 词头反向索引（P2.3 用），构建期由结构化解析填充
- 线程：构建在后台线程、查询在主线程，二者用独立连接（WAL 支持并发读写）
"""
from __future__ import annotations

import os
import sqlite3
import zlib
from typing import Callable, List, Optional, Tuple

from .mdx_parser import MdxParser
from .models import PhraseItem
from .parser import extract_phrases

ProgressCallback = Callable[[int, int], None]  # (done, total)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
CREATE TABLE IF NOT EXISTS entries (
    dict    TEXT NOT NULL,
    word    TEXT NOT NULL,   -- 小写 key
    display TEXT NOT NULL,   -- 原样词头（首个）
    content BLOB,
    PRIMARY KEY (dict, word)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS phrases (
    phrase   TEXT NOT NULL,
    headword TEXT NOT NULL,  -- 小写
    dict     TEXT NOT NULL,
    kind     TEXT NOT NULL,  -- idiom / phrasal_verb
    PRIMARY KEY (dict, phrase, headword)
) WITHOUT ROWID;
"""

_LINK_RE_PREFIX = "@@@link="
_MAX_LINK_DEPTH = 6
_BATCH = 5000

# 索引格式版本：内容压缩方式变更时递增，旧库自动重建
FORMAT_VERSION = "2"  # 2 = content 以 zlib 压缩存储


def _pack(content: str) -> bytes:
    return zlib.compress(content.encode("utf-8"))


def _unpack(data) -> str:
    if isinstance(data, bytes) and data[:2] in (b"\x78\x01", b"\x78\x9c", b"\x78\xda"):
        return zlib.decompress(data).decode("utf-8", errors="replace")
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return str(data)


class SQLiteIndex:
    """单库承载全部词典的索引。"""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = self._connect()
        self._conn.executescript(_SCHEMA)
        # 标记格式版本：旧版本库触发全量重建
        if self._meta("format_version") != FORMAT_VERSION:
            self._conn.execute("DELETE FROM meta")
            self._conn.commit()
        self._set_meta("format_version", FORMAT_VERSION)

    # ---------- 连接 ----------
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    # ---------- 指纹 ----------
    @staticmethod
    def fingerprint(file_path: str) -> str:
        st = os.stat(file_path)
        return f"{st.st_size}:{int(st.st_mtime)}"

    def _meta(self, key: str) -> Optional[str]:
        row = self._conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def _set_meta(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)", (key, value)
        )
        self._conn.commit()

    def is_built(self, dict_name: str, file_path: str) -> bool:
        fp = self._meta(f"fp:{dict_name}")
        return fp is not None and fp == self.fingerprint(file_path)

    # ---------- 发音资源 ----------
    def mark_audio(self, dict_name: str) -> None:
        """标记某词典为发音资源（非查询词典，无需构建索引）"""
        self._set_meta(f"audio:{dict_name}", "1")

    def is_audio(self, dict_name: str) -> bool:
        return self._meta(f"audio:{dict_name}") == "1"

    def get_count(self, dict_name: str) -> int:
        """已构建词典的词条数（从 meta 读，不查表，启动更快）"""
        v = self._meta(f"count:{dict_name}")
        return int(v) if v is not None else 0

    # ---------- 构建 ----------
    def build(
        self,
        parser: MdxParser,
        dict_name: str,
        progress_cb: Optional[ProgressCallback] = None,
    ) -> int:
        """遍历 parser 全部词条写入索引 + 短语反向索引。

        在**调用线程**上开独立连接，避免与主线程读连接共享。
        返回写入词条数。
        """
        total = parser.get_entry_count()
        conn = self._connect()
        try:
            conn.execute("DELETE FROM entries WHERE dict=?", (dict_name,))
            conn.execute("DELETE FROM phrases WHERE dict=?", (dict_name,))
            conn.commit()

            cur = conn.cursor()
            batch: List[Tuple] = []
            phrase_rows: List[Tuple] = []
            inserted = 0

            for word, content in parser.iter_entries():
                if not word:
                    continue
                key = word.lower()
                batch.append((dict_name, key, word, _pack(content)))
                for p in extract_phrases(content, word):
                    phrase_rows.append((p.phrase, key, dict_name, p.kind))

                if len(batch) >= _BATCH:
                    cur.executemany("INSERT OR REPLACE INTO entries VALUES (?,?,?,?)", batch)
                    if phrase_rows:
                        cur.executemany(
                            "INSERT OR IGNORE INTO phrases VALUES (?,?,?,?)", phrase_rows
                        )
                    conn.commit()
                    inserted += len(batch)
                    batch.clear()
                    phrase_rows.clear()
                    if progress_cb:
                        progress_cb(inserted, total)

            if batch:
                cur.executemany("INSERT OR REPLACE INTO entries VALUES (?,?,?,?)", batch)
                if phrase_rows:
                    cur.executemany(
                        "INSERT OR IGNORE INTO phrases VALUES (?,?,?,?)", phrase_rows
                    )
                conn.commit()
                inserted += len(batch)

            # 记录指纹 + 词条数
            self._set_meta(f"fp:{dict_name}", self.fingerprint(parser.file_path))
            self._set_meta(f"count:{dict_name}", str(inserted))
            if progress_cb:
                progress_cb(inserted, total)
            return inserted
        finally:
            conn.close()

    # ---------- 查询 ----------
    @staticmethod
    def _link_target(content: str) -> Optional[str]:
        """@@@LINK= 跳转目标；非跳转返回 None"""
        stripped = content.lstrip("﻿\r\n ")
        if stripped.lower().startswith(_LINK_RE_PREFIX):
            return stripped[len(_LINK_RE_PREFIX):].strip()
        return None

    def lookup(self, word: str, dict_name: str) -> Optional[Tuple[str, str]]:
        """精确查找，解析 @@@LINK= 跳转链。返回 (display, content) 或 None。"""
        key = word.strip().lower()
        seen = set()
        for _ in range(_MAX_LINK_DEPTH):
            row = self._conn.execute(
                "SELECT display, content FROM entries WHERE dict=? AND word=?",
                (dict_name, key),
            ).fetchone()
            if row is None:
                return None
            display, content = row
            content = _unpack(content)
            target = self._link_target(content)
            if target is None:
                return display, content
            nxt = target.lower()
            if nxt in seen or nxt == key:
                return None
            seen.add(key)
            key = nxt
        return None

    def suggest(self, prefix: str, dict_name: str, limit: int = 20) -> List[str]:
        """前缀匹配，返回小写 word 列表（PK 范围扫描）"""
        if not prefix:
            return []
        p = prefix.lower()
        rows = self._conn.execute(
            "SELECT word FROM entries WHERE dict=? AND word >= ? AND word < ? "
            "ORDER BY word LIMIT ?",
            (dict_name, p, p + "￿", limit),
        ).fetchall()
        return [r[0] for r in rows]

    def suggest_contains(self, substring: str, dict_name: str, limit: int = 20) -> List[str]:
        """模糊匹配：词中包含子串（LIKE 全表扫，仅供前缀无果时的回退补全）"""
        s = substring.lower()
        if not s:
            return []
        rows = self._conn.execute(
            "SELECT word FROM entries WHERE dict=? AND word LIKE ? LIMIT ?",
            (dict_name, f"%{s}%", limit),
        ).fetchall()
        return [r[0] for r in rows]

    def count(self, dict_name: str) -> int:
        return self._conn.execute(
            "SELECT COUNT(*) FROM entries WHERE dict=?", (dict_name,)
        ).fetchone()[0]

    def related_phrases(self, headword: str, dict_name: str) -> List[PhraseItem]:
        """某词头的相关短语/习语（P2.3 反向索引查询）"""
        rows = self._conn.execute(
            "SELECT phrase, kind FROM phrases WHERE dict=? AND headword=? "
            "ORDER BY kind, phrase",
            (dict_name, headword.strip().lower()),
        ).fetchall()
        return [PhraseItem(phrase=r[0], kind=r[1]) for r in rows]
