"""MDX 文件解析 - 封装 readmdict，返回 (word, raw_html) 迭代器

内存模型（readmdict 实测）：
- `MDX(path)` 构造时把**所有 key** 读进内存（获取词条数/前缀元数据），但**不加载内容**
- `items()` 是惰性生成器，逐块解压 record block，内容不驻留内存
因此这里不再 `list(items())` 物化全部内容（Phase 1 内存/启动慢的根源），
内容消费交给上层按需迭代（如 SQLite 索引构建）。
"""
from __future__ import annotations

from typing import Iterator, List, Optional, Tuple

from readmdict import MDX

from .models import DictionaryInfo


class MdxParser:
    """单个 MDX 文件的封装。

    - get_entry_count(): 读取全部 key 后得到词条数（构造即加载 key，是唯一较大的扫描成本）
    - iter_entries(): 惰性迭代 (word, raw_html)，可重复调用
    - lookup(word): 线性扫描查找（仅在非索引路径使用，SQLite 就绪后不是热点）
    """

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self._mdx: Optional[MDX] = None
        self._name: Optional[str] = None
        self._count: Optional[int] = None

    # ---------- 内部 ----------
    def _ensure_loaded(self) -> None:
        if self._mdx is None:
            self._mdx = MDX(self.file_path)
            self._count = len(self._mdx)

    def _decode(self, b) -> str:
        """readmdict 返回 bytes，统一 decode 兜底乱码"""
        if isinstance(b, bytes):
            return b.decode("utf-8", errors="replace")
        return str(b)

    # ---------- 对外 API ----------
    def get_info(self) -> DictionaryInfo:
        """词典元信息（会触发 key 加载以取 entry_count）"""
        import os

        name = os.path.basename(self.file_path)
        if self._name is None:
            self._name = name
        if self._count is None:
            self._ensure_loaded()
        return DictionaryInfo(
            name=self._name,
            file_path=self.file_path,
            entry_count=self._count or 0,
            loaded=True,
        )

    def get_entry_count(self) -> int:
        if self._count is None:
            self._ensure_loaded()
        return self._count or 0

    def iter_entries(self) -> Iterator[Tuple[str, str]]:
        """yield (word, raw_html)，惰性，可重复迭代"""
        self._ensure_loaded()
        for raw_k, raw_v in self._mdx.items():  # type: ignore[union-attr]
            yield self._decode(raw_k), self._decode(raw_v)

    def sample_entries(self, n: int = 20) -> List[Tuple[str, str]]:
        """取前 n 条 (word, raw_html)，用于内容启发式分类（如识别纯音频词典）"""
        out: List[Tuple[str, str]] = []
        for i, (w, c) in enumerate(self.iter_entries()):
            if i >= n:
                break
            out.append((w, c))
        return out

    def lookup(self, word: str) -> Optional[str]:
        """精确查找单个词，返回 raw_html 或 None（大小写不敏感线性扫描）"""
        target = word.strip().lower()
        for w, content in self.iter_entries():
            if w.lower() == target:
                return content
        return None
