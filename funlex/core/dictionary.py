"""词典管理服务 - 扫描路径、加载 MDX、维护内存索引、查询/前缀匹配"""
from __future__ import annotations

import glob
import os
from typing import Dict, List, Optional, Tuple

from .models import DictionaryEntry, DictionaryInfo
from .mdx_parser import MdxParser


class DictionaryService:
    """多词典管理。

    MVP 设计：
    - 加载时遍历 MDX 所有词条，存到内存 dict: {dict_name: {word_lower: raw_html}}
    - lookup 用大小写不敏感的小写 key
    - suggest 做简单前缀扫描，遍历 keys
    """

    def __init__(self, paths: Optional[List[str]] = None) -> None:
        # 内存索引：{dict_name: {word_lower: raw_html}}
        self._index: Dict[str, Dict[str, str]] = {}
        # 词典元信息：{dict_name: DictionaryInfo}
        self._infos: Dict[str, DictionaryInfo] = {}
        # 解析器缓存 (避免重复加载)
        self._parsers: Dict[str, MdxParser] = {}

        if paths is None:
            paths = self._default_paths()
        self._configured_paths = paths
        self.scan()

    # ---------- 路径扫描 ----------
    def _default_paths(self) -> List[str]:
        cwd = os.getcwd()
        return [cwd, os.path.join(cwd, "dictionaries")]

    def _iter_mdx_files(self) -> List[str]:
        seen: Dict[str, str] = {}
        for p in self._configured_paths:
            if not p:
                continue
            if os.path.isfile(p) and p.lower().endswith(".mdx"):
                seen[os.path.abspath(p)] = p
            elif os.path.isdir(p):
                for f in glob.glob(os.path.join(p, "*.mdx")):
                    seen[os.path.abspath(f)] = f
        return list(seen.values())

    # ---------- 加载 ----------
    def scan(self) -> List[DictionaryInfo]:
        """扫描所有 configured_paths，发现 MDX 文件并加载到内存索引"""
        loaded_infos: List[DictionaryInfo] = []
        for file_path in self._iter_mdx_files():
            info = self.load_dictionary(file_path)
            if info is not None:
                loaded_infos.append(info)
        # 按 entry_count 倒序排，方便 UI 默认选中最大的（通常是牛津第10版）
        loaded_infos.sort(key=lambda i: i.entry_count, reverse=True)
        return loaded_infos

    def load_dictionary(self, file_path: str) -> Optional[DictionaryInfo]:
        """加载单个 MDX，返回 DictionaryInfo；失败返回 None"""
        if not os.path.isfile(file_path):
            return None
        abs_path = os.path.abspath(file_path)
        name = os.path.basename(file_path)
        if name in self._index:
            return self._infos.get(name)

        try:
            parser = MdxParser(abs_path)
            # 构建小写索引
            index: Dict[str, str] = {}
            for word, content in parser.iter_entries():
                if not word:
                    continue
                index[word.lower()] = content
            info = parser.get_info()
            info.loaded = True
            self._index[name] = index
            self._infos[name] = info
            self._parsers[name] = parser
            return info
        except Exception as e:
            # 单本词典加载失败不影响其他
            print(f"[DictionaryService] Failed to load {file_path}: {e}")
            return None

    # ---------- 查询 ----------
    def list_dictionaries(self) -> List[DictionaryInfo]:
        """返回所有已加载词典（按 entry_count 倒序）"""
        infos = [i for i in self._infos.values() if i.loaded]
        infos.sort(key=lambda i: i.entry_count, reverse=True)
        return infos

    def first_dictionary(self) -> Optional[DictionaryInfo]:
        infos = self.list_dictionaries()
        return infos[0] if infos else None

    def lookup(self, word: str, dictionary_name: Optional[str] = None) -> Optional[DictionaryEntry]:
        """查单词。

        - dictionary_name=None: 默认在第一个词典查；查不到再依次尝试其他词典
        - 返回 DictionaryEntry 或 None
        """
        if not word or not word.strip():
            return None
        key = word.strip().lower()
        infos = self.list_dictionaries()
        if not infos:
            return None

        def _query(name: str) -> Optional[Tuple[str, str]]:
            idx = self._index.get(name, {})
            return (name, idx[key]) if key in idx else None

        if dictionary_name and dictionary_name in self._index:
            hit = _query(dictionary_name)
            if hit:
                return DictionaryEntry(
                    word=word.strip(),
                    dictionary_name=hit[0],
                    raw_content=hit[1],
                )
            return None

        # 默认策略：先第一个（最大词典）
        for info in infos:
            hit = _query(info.name)
            if hit:
                return DictionaryEntry(
                    word=word.strip(),
                    dictionary_name=hit[0],
                    raw_content=hit[1],
                )
        return None

    def suggest(self, prefix: str, limit: int = 20) -> List[Tuple[str, str]]:
        """前缀匹配，返回 [(word, dict_name), ...]，最多 limit 条。

        MVP 实现：遍历所有已加载词典的 keys，挑出以 prefix 小写开头的。
        """
        if not prefix:
            return []
        p = prefix.lower()
        results: List[Tuple[str, str]] = []
        # 按词典 entry_count 倒序遍历，大的优先
        for info in self.list_dictionaries():
            idx = self._index.get(info.name, {})
            for w in idx.keys():
                if w.startswith(p):
                    results.append((w, info.name))
                    if len(results) >= limit:
                        return results
        return results

    def total_entries(self) -> int:
        return sum(len(idx) for idx in self._index.values())
