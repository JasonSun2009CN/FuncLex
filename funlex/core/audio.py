"""MDD 音频索引 - 从 MDict 音频资源（.mdd）定向提取音频字节

readmdict 的 items() 会解压全部记录；本模块按需**定向提取**单个 key 的字节，
避免把整个音频包载入内存。

实现说明：
- 复用 MDict 的记录块结构（MDX/MDD 相同，本逻辑已在现有 .mdx 上验证）
- `_key_list` 提供每个 key 在解压流中的偏移；`_record_block_offset` 定位块起始
- `get(key)` 定位目标块 → 解压该块 → 切片返回
- 任何异常返回 None，上层回退 TTS，保证不崩溃
"""
from __future__ import annotations

import struct
import zlib
from typing import Dict, List, Optional, Set, Tuple


class MddAudioIndex:
    """MDD 音频索引。keys 为文件名（如 take__gb_1.mp3）。"""

    def __init__(self, mdd_path: str) -> None:
        self.path = mdd_path
        self._reader = None
        self._offsets: Dict[str, int] = {}
        self._loaded = False
        self._load()

    # ---------- 加载 ----------
    def _load(self) -> None:
        try:
            from readmdict import MDD
        except Exception as e:
            print(f"[Audio] readmdict unavailable: {e}")
            return
        try:
            r = MDD(self.path)
            self._reader = r
            for off, key_b in r._key_list:
                try:
                    k = key_b.decode("utf-8", "replace")
                except Exception:
                    k = str(key_b)
                # 归一化：统一小写、去掉可能的前导 '/'
                self._offsets[k] = off
                self._offsets[k.lstrip("/")] = off
            self._loaded = True
        except Exception as e:
            print(f"[Audio] failed to load {self.path}: {e}")

    @property
    def loaded(self) -> bool:
        return self._loaded

    @property
    def size(self) -> int:
        return len(self._offsets) // 2

    # ---------- 查询 ----------
    def has(self, key: str) -> bool:
        return key in self._offsets

    def get(self, key: str) -> Optional[bytes]:
        off = self._offsets.get(key)
        if off is None:
            off = self._offsets.get(key.lstrip("/"))
        if off is None or self._reader is None:
            return None
        try:
            return self._extract(off)
        except Exception as e:
            print(f"[Audio] extract {key} failed: {e}")
            return None

    def has_audio_for(self, word: str, variant: str = "") -> bool:
        """快速判断某词头是否有（英/美音）原声（只查索引，不提取字节）"""
        base = word.strip().lower()
        order = ["gb", "us"] if not variant else [variant]
        for v in order:
            prefix = f"{base}__{v}_"
            for key in self._offsets:
                if key.startswith(prefix) and key.endswith(".mp3"):
                    return True
        return False

    def find(self, word: str, variant: str = "") -> Optional[Tuple[str, bytes]]:
        """按词头 + 变体找音频。variant: 'gb'|'us'|''（'' 优先英音再美音）。

        返回 (音频key, bytes) 或 None。
        """
        base = word.strip().lower()
        order = ["gb", "us"] if not variant else [variant]
        for v in order:
            prefix = f"{base}__{v}_"
            # 1) 在索引里前缀匹配（最准确）
            for key in self._offsets:
                if key.startswith(prefix) and key.endswith(".mp3"):
                    data = self.get(key)
                    if data:
                        return key, data
            # 2) 按常见序号 n=1..5 构造
            for n in range(1, 6):
                for cand in (f"{base}__{v}_{n}.mp3", f"/{base}__{v}_{n}.mp3"):
                    data = self.get(cand)
                    if data:
                        return cand, data
        return None

    # ---------- 定向提取 ----------
    def _extract(self, target_offset: int) -> bytes:
        r = self._reader
        nw = r._number_width
        with open(r._fname, "rb") as f:
            f.seek(r._record_block_offset)
            num_blocks = r._read_number(f)
            r._read_number(f)  # num_entries
            block_info_size = r._read_number(f)
            r._read_number(f)  # block_size
            data_start = r._record_block_offset + 4 * nw + block_info_size
            cum = 0
            for _ in range(num_blocks):
                cs = r._read_number(f)
                ds = r._read_number(f)
                if cum + ds > target_offset:
                    f.seek(data_start)
                    compressed = f.read(cs)
                    block = self._decompress(compressed, ds)
                    rel = target_offset - cum
                    if block is None or rel < 0 or rel >= len(block):
                        return b""
                    # 记录长度：到块尾（音频文件通常独占块尾部之前的连续区间）
                    return block[rel:]
                cum += ds
                data_start += cs
        return b""

    @staticmethod
    def _decompress(compressed: bytes, ds: int) -> Optional[bytes]:
        bt = compressed[:4]
        payload = compressed[8:]
        if bt == b"\x00\x00\x00\x00":
            return payload
        if bt == b"\x01\x00\x00\x00":
            import lzo

            return lzo.decompress(b"\xf0" + struct.pack(">I", ds) + payload)
        if bt == b"\x02\x00\x00\x00":
            return zlib.decompress(payload)
        return None
