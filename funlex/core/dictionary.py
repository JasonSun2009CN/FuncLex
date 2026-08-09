"""词典管理服务 - 扫描路径、SQLite 索引、查询/前缀匹配/短语反向索引

Phase 2 重构：索引从内存 dict 换成 SQLite（`data/index.db`）。
- scan() 只 stat + 指纹校验：MDX 未变更时**不打开文件**，启动 <2s
- 首次见到的词典打开取词条数并分类（内容启发式识别纯音频词典为"发音资源"，不进查询列表）
- 索引构建放后台线程（build_index + pending_builds），已构建词典即查即用
- lookup 走 SQLite 并解析 @@@LINK= 跳转链；命中后懒做结构化解析（P2.2）
"""
from __future__ import annotations

import glob
import os
from typing import Dict, List, Optional, Set, Tuple

from .indexer import SQLiteIndex
from .mdx_parser import MdxParser
from .models import DictionaryEntry, DictionaryInfo, PhraseItem
from .parser import parse_entry
from .paths import default_data_dir, default_dictionary_dirs

_AUDIO_SAMPLE = 30
_AUDIO_SOUND_RATIO = 0.8
_AUDIO_MAX_AVG_LEN = 600


class DictionaryService:
    """多词典管理。公开 API 与 Phase 1 兼容，UI 层零破坏。"""

    def __init__(
        self,
        paths: Optional[List[str]] = None,
        data_dir: Optional[str] = None,
    ) -> None:
        self.data_dir = data_dir or default_data_dir()
        self._index = SQLiteIndex(os.path.join(self.data_dir, "index.db"))
        # 查询词典元信息：{name: DictionaryInfo}
        self._infos: Dict[str, DictionaryInfo] = {}
        # 待构建索引的词典名
        self._pending: List[str] = []
        # 发音资源（纯音频词典，不参与查询）
        self._audio_name: Optional[str] = None
        self._audio_path: Optional[str] = None
        self._audio_words: Optional[Set[str]] = None
        # 合并显示的词典顺序（上→下，由 config 注入）；空 = 按词条数倒序
        self._order: List[str] = []

        if paths is None:
            paths = self._default_paths()
        self._configured_paths = paths
        self.scan()

    # ---------- 路径扫描 ----------
    def _default_paths(self) -> List[str]:
        # 打包后为 用户数据目录/dictionaries；开发为 项目根 + dictionaries/（见 paths.py）
        return default_dictionary_dirs()

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

    def find_audio_mdd(self) -> Optional[str]:
        """在配置路径中查找配套的 .mdd 音频资源文件（如 oald10.mdd）。

        存在则优先用真实发音；否则发音回退 TTS。
        """
        for p in self._configured_paths:
            if not p:
                continue
            if os.path.isfile(p) and p.lower().endswith(".mdd"):
                return p
            if os.path.isdir(p):
                for f in glob.glob(os.path.join(p, "*.mdd")):
                    return f
        return None

    # ---------- 分类 ----------
    def _classify(self, parser: MdxParser) -> str:
        """内容启发式：多数词条是 sound:// 链接且内容很短 → 'audio'，否则 'query'"""
        sample = parser.sample_entries(_AUDIO_SAMPLE)
        if not sample:
            return "query"
        sound = sum(1 for _, c in sample if "sound://" in c.lower())
        avg_len = sum(len(c) for _, c in sample) / len(sample)
        if sound / len(sample) >= _AUDIO_SOUND_RATIO and avg_len <= _AUDIO_MAX_AVG_LEN:
            return "audio"
        return "query"

    # ---------- 扫描 / 加载 ----------
    def scan(self) -> List[DictionaryInfo]:
        """快速扫描：已构建的词典只做指纹校验，不加载全文。"""
        self._infos.clear()
        self._pending.clear()
        self._audio_name = None
        self._audio_path = None
        for file_path in self._iter_mdx_files():
            self._scan_one(file_path)
        return self.list_dictionaries()

    def _scan_one(self, file_path: str) -> None:
        if not os.path.isfile(file_path):
            return
        abs_path = os.path.abspath(file_path)
        name = os.path.basename(file_path)

        # 已知发音资源：跳过打开
        if self._index.is_audio(name):
            self._register_audio(name, abs_path)
            return

        # 已构建且指纹一致：不打开 MDX，词条数从 meta 读
        if self._index.is_built(name, abs_path):
            info = DictionaryInfo(
                name, abs_path, self._index.get_count(name), loaded=True
            )
            self._infos[name] = info
            return

        # 首次见：打开取词条数 + 分类
        try:
            parser = MdxParser(abs_path)
            count = parser.get_entry_count()
        except Exception as e:
            print(f"[DictionaryService] Failed to inspect {file_path}: {e}")
            return

        if self._classify(parser) == "audio":
            self._index.mark_audio(name)
            self._register_audio(name, abs_path)
            return

        info = DictionaryInfo(name, abs_path, count, loaded=False)
        self._infos[name] = info
        self._pending.append(name)

    def _register_audio(self, name: str, abs_path: str) -> None:
        self._audio_name = name
        self._audio_path = abs_path

    def load_dictionary(self, file_path: str) -> Optional[DictionaryInfo]:
        """同步加载单个 MDX 到索引（兼容旧 API / 手动重建）。"""
        abs_path = os.path.abspath(file_path)
        name = os.path.basename(file_path)
        try:
            parser = MdxParser(abs_path)
        except Exception as e:
            print(f"[DictionaryService] Failed to load {file_path}: {e}")
            return None
        if self._classify(parser) == "audio":
            self._index.mark_audio(name)
            self._register_audio(name, abs_path)
            return None
        count = self.build_index(name, parser=parser)
        info = DictionaryInfo(name, abs_path, count, loaded=True)
        self._infos[name] = info
        if name in self._pending:
            self._pending.remove(name)
        return info

    # ---------- 索引构建 ----------
    def pending_builds(self) -> List[DictionaryInfo]:
        """需要构建索引的词典（entry_count 已知，loaded=False）"""
        return [self._infos[n] for n in self._pending]

    def build_index(
        self,
        name: str,
        parser: Optional[MdxParser] = None,
        progress_cb=None,
    ) -> int:
        """构建某词典的索引（供后台线程调用）。返回词条数。"""
        if parser is None:
            info = self._infos.get(name)
            if info is None:
                return 0
            parser = MdxParser(info.file_path)
        count = self._index.build(parser, name, progress_cb)
        if name in self._infos:
            self._infos[name].entry_count = count
            self._infos[name].loaded = True
        if name in self._pending:
            self._pending.remove(name)
        return count

    # ---------- 查询 ----------
    def list_dictionaries(self) -> List[DictionaryInfo]:
        """已加载（索引就绪）的查询词典，按 entry_count 倒序"""
        infos = [i for i in self._infos.values() if i.loaded]
        infos.sort(key=lambda i: i.entry_count, reverse=True)
        return infos

    def set_dictionary_order(self, names: List[str]) -> None:
        """设置合并显示的词典顺序（上→下）。只保留已加载的词典名。"""
        loaded = {i.name for i in self.list_dictionaries()}
        self._order = [n for n in names if n in loaded]

    def ordered_dictionaries(self) -> List[DictionaryInfo]:
        """合并显示的词典顺序：按 set_dictionary_order 的顺序；未指定的按词条数倒序补在后面"""
        loaded = self.list_dictionaries()
        if not self._order:
            return loaded
        by_name = {i.name: i for i in loaded}
        ordered = [by_name[n] for n in self._order if n in by_name]
        rest = [i for i in loaded if i.name not in self._order]
        return ordered + rest

    def first_dictionary(self) -> Optional[DictionaryInfo]:
        infos = self.ordered_dictionaries()
        return infos[0] if infos else None

    def lookup_all(self, word: str) -> List[DictionaryEntry]:
        """多词典合并查询：返回所有命中词典的词条，按显示顺序（上→下）。

        每个词条已做结构化懒解析（音标/词性/例句/习语），供合并视图直接渲染。
        """
        if not word or not word.strip():
            return []
        key = word.strip().lower()
        out: List[DictionaryEntry] = []
        for info in self.ordered_dictionaries():
            hit = self._index.lookup(key, info.name)
            if hit is None:
                continue
            display, content = hit
            entry = DictionaryEntry(
                word=display, dictionary_name=info.name, raw_content=content
            )
            out.append(self._enrich(entry))
        return out

    def lookup(
        self, word: str, dictionary_name: Optional[str] = None
    ) -> Optional[DictionaryEntry]:
        """查单词。

        - dictionary_name=None: 默认在第一个（最大的）词典查，查不到依次尝试其他
        - 命中后做结构化懒解析（POS/音标/例句/习语），解析结果随词条返回
        """
        if not word or not word.strip():
            return None
        key = word.strip().lower()
        infos = self.list_dictionaries()
        if not infos:
            return None

        def _query(name: str) -> Optional[DictionaryEntry]:
            hit = self._index.lookup(key, name)
            if hit is None:
                return None
            display, content = hit
            return self._enrich(
                DictionaryEntry(word=display, dictionary_name=name, raw_content=content)
            )

        if dictionary_name and dictionary_name in self._infos:
            return _query(dictionary_name)
        for info in infos:
            hit = _query(info.name)
            if hit is not None:
                return hit
        return None

    def _enrich(self, entry: DictionaryEntry) -> DictionaryEntry:
        """懒结构化解析：一次正则抽取填充音标/词性/例句/习语（P2.2）"""
        if entry.raw_content and not entry.pos_tags:
            parsed = parse_entry(entry.word, entry.dictionary_name, entry.raw_content)
            entry.phonetic_uk = parsed.phonetic_uk
            entry.phonetic_us = parsed.phonetic_us
            entry.pos_tags = parsed.pos_tags
            entry.examples = parsed.examples
            entry.idioms = parsed.idioms
            entry.phrasal_verbs = parsed.phrasal_verbs
        return entry

    def suggest(self, prefix: str, limit: int = 20) -> List[Tuple[str, str]]:
        """前缀匹配，返回 [(word, dict_name), ...]。按词典 priority 聚合。"""
        if not prefix:
            return []
        results: List[Tuple[str, str]] = []
        for info in self.list_dictionaries():
            words = self._index.suggest(prefix, info.name, limit - len(results))
            for w in words:
                results.append((w, info.name))
            if len(results) >= limit:
                break
        return results

    def suggest_words(self, prefix: str, limit: int = 8) -> List[str]:
        """搜索建议：前缀优先（跨词典去重）；不足用首词典的包含匹配补齐（模糊）。

        前缀命中率高时只走 PK 范围扫描；仅当前缀结果不足 limit 才触发 LIKE 全表扫
        （代价可控），保证补全弹窗总是有内容。
        """
        if not prefix or not prefix.strip():
            return []
        out: List[str] = []
        seen = set()
        for w, _ in self.suggest(prefix.strip(), limit * 3):
            if w not in seen:
                seen.add(w)
                out.append(w)
            if len(out) >= limit:
                return out
        # 前缀不足：用最大词典的包含匹配补齐
        infos = self.list_dictionaries()
        if infos and len(out) < limit:
            for w in self._index.suggest_contains(
                prefix.strip(), infos[0].name, limit * 2
            ):
                if w not in seen:
                    seen.add(w)
                    out.append(w)
                if len(out) >= limit:
                    break
        return out

    def related_phrases(
        self, word: str, dictionary_name: Optional[str] = None
    ) -> List[PhraseItem]:
        """某词头的相关短语/习语（P2.3 反向索引）"""
        names = (
            [dictionary_name]
            if dictionary_name
            else [i.name for i in self.list_dictionaries()]
        )
        out: List[PhraseItem] = []
        for n in names:
            out.extend(self._index.related_phrases(word, n))
        return out

    def has_audio(self, word: str) -> bool:
        """发音资源里是否有该词的 Collins 原声（懒加载词表）"""
        if self._audio_name is None:
            return False
        self._ensure_audio_words()
        return word.strip().lower() in self._audio_words

    def _ensure_audio_words(self) -> None:
        if self._audio_words is not None:
            return
        words: Set[str] = set()
        if self._audio_path:
            try:
                parser = MdxParser(self._audio_path)
                for w, _ in parser.iter_entries():
                    if w:
                        words.add(w.lower())
            except Exception as e:
                print(f"[DictionaryService] failed to load audio words: {e}")
        self._audio_words = words

    def total_entries(self) -> int:
        return sum(i.entry_count for i in self._infos.values() if i.loaded)
