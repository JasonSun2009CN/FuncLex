"""MDX 文件解析 - 封装 readmdict，返回 (word, raw_html) 迭代器"""
from __future__ import annotations

from typing import Iterator, Tuple, Optional

from readmdict import MDX

from .models import DictionaryInfo


class MdxParser:
    """单个 MDX 文件的封装。

    设计原则：MVP 不做过度结构化解析，只把 content bytes 安全 decode 成 utf-8 字符串。
    上层 (DictionaryService) 自行决定如何消费 raw HTML。
    """

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self._mdx: Optional[MDX] = None
        self._entries = None
        self._name: Optional[str] = None
        self._count: Optional[int] = None

    # ---------- 内部 ----------
    def _ensure_loaded(self) -> None:
        if self._mdx is None:
            self._mdx = MDX(self.file_path)
            # readmdict 的 keys/values 是 [(bytes, bytes), ...] 列表
            self._entries = list(self._mdix_items())

    def _mdix_items(self):
        """兼容不同版本 readmdict 的 keys/items 接口"""
        mdx = self._mdx
        # 新版 (>=0.1.1) 通常提供 keys() / items()
        if hasattr(mdx, "items"):
            return mdx.items()
        # 兜底：直接拿私有 keys/values
        keys = mdx.keys() if hasattr(mdx, "keys") else getattr(mdx, "_keys", [])
        values = mdx.values() if hasattr(mdx, "values") else getattr(mdx, "_values", [])
        return zip(keys, values)

    # ---------- 对外 API ----------
    def get_info(self) -> DictionaryInfo:
        """词典元信息 (首次调用会触发加载以取 entry_count)"""
        import os
        name = os.path.basename(self.file_path)
        if self._name is None:
            self._name = name
        if self._count is None:
            self._ensure_loaded()
            self._count = len(self._entries) if self._entries is not None else 0
        return DictionaryInfo(
            name=self._name,
            file_path=self.file_path,
            entry_count=self._count or 0,
            loaded=True,
        )

    def get_entry_count(self) -> int:
        if self._count is None:
            self._ensure_loaded()
            self._count = len(self._entries) if self._entries is not None else 0
        return self._count

    def iter_entries(self) -> Iterator[Tuple[str, str]]:
        """yield (word, raw_html)"""
        self._ensure_loaded()
        if self._entries is None:
            return
        for raw_k, raw_v in self._entries:
            word = raw_k.decode("utf-8", errors="replace") if isinstance(raw_k, bytes) else str(raw_k)
            content = raw_v.decode("utf-8", errors="replace") if isinstance(raw_v, bytes) else str(raw_v)
            yield word, content

    def lookup(self, word: str) -> Optional[str]:
        """精确查找单个词，返回 raw_html 或 None"""
        self._ensure_loaded()
        if self._entries is None:
            return None
        target = word.lower().encode("utf-8")
        # 优先用 readmdict 自带 keys 索引 (如果提供)
        if self._mdx is not None and hasattr(self._mdx, "keys"):
            try:
                # 牛津等 MDX 的 key 是 case-sensitive 的小写形式，但部分有大小写差异
                # 这里做一次小写线性扫描以保证大小写不敏感
                for raw_k, raw_v in self._entries:
                    if isinstance(raw_k, bytes):
                        if raw_k.lower() == target:
                            return raw_v.decode("utf-8", errors="replace")
                    else:
                        if str(raw_k).lower() == word.lower():
                            return str(raw_v)
                return None
            except Exception:
                pass
        # 兜底遍历
        for raw_k, raw_v in self._entries:
            key_str = raw_k.decode("utf-8", errors="replace") if isinstance(raw_k, bytes) else str(raw_k)
            if key_str.lower() == word.lower():
                return raw_v.decode("utf-8", errors="replace") if isinstance(raw_v, bytes) else str(raw_v)
        return None
