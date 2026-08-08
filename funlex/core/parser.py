"""词条 HTML 结构化解析 - 纯 Python，无 UI 依赖

主要针对牛津第10版（oald10）的语义 class：
  .headword / .pos / .phon(.phons_br|.phons_n_am) / .example / .idm / .pvrefs
其他词典尽力而为——匹配不到的字段留空，UI 会降级到默认视图。

设计取舍：用轻量正则 + HTML 实体清洗，而非完整 DOM 解析。
这类词典 HTML 结构混乱、嵌套不规范，按语义 class 定位片段更稳也更快。
"""
from __future__ import annotations

import html as html_lib
import re
from typing import List, Optional

from .models import DictionaryEntry, PhraseItem

# ---------- 正则 ----------
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")

# 短语/习语语义块（构建反向索引 + 结构化解析共用）
_PHRASE_CLASS_RE = re.compile(
    r'<span class="(idm|idm-g|idmrefs|phrv|pv|pvrefs|phrasal_verb_box|cf)"[^>]*>(.*?)</span>',
    re.S | re.I,
)

# 短语动词/习语 交叉引用列表：<ul class="pvrefs"><li><a><span class="xh">短语</span>
_PVREFS_UL_RE = re.compile(r'<ul class="(pvrefs|idmrefs)"[^>]*>(.*?)</ul>', re.S | re.I)
_XH_RE = re.compile(r'<span class="xh"[^>]*>(.*?)</span>', re.S | re.I)

# 音标：phons_br(英) / phons_n_am(美) 容器内取 .phon 文本
_PHONS_BR_RE = re.compile(r'<div class="phons_br"[^>]*>(.*?)</div>', re.S | re.I)
_PHONS_AM_RE = re.compile(r'<div class="phons_n_am"[^>]*>(.*?)</div>', re.S | re.I)
_PHON_INNER_RE = re.compile(r'<span class="phon"[^>]*>(.*?)</span>', re.S | re.I)

_POS_RE = re.compile(r'<span class="pos"[^>]*>(.*?)</span>', re.S | re.I)
_HEADWORD_RE = re.compile(r'<h1 class="headword"[^>]*>(.*?)</h1>', re.S | re.I)
# 例句：牛津 .x / 通用 .example / .examples
_EXAMPLE_RE = re.compile(
    r'<(?:span|a) class="(?:example|examples|x)"[^>]*>(.*?)</(?:span|a)>', re.S | re.I
)


def _clean_text(s: str, max_len: int = 0) -> str:
    """去标签、合并空白、反转义 HTML 实体"""
    s = _TAG_RE.sub(" ", s)
    s = html_lib.unescape(s)
    s = _WS_RE.sub(" ", s).strip()
    if max_len and len(s) > max_len:
        s = s[: max_len].rstrip() + "…"
    return s


# ---------- 快捷短语抽取 ----------
def extract_phrases(html: str, headword: str = "") -> List[PhraseItem]:
    """从 HTML 抽取短语/习语项（供构建反向索引、结构化解析共用）。

    - `.idm*` / `.cf` → kind=idiom
    - `.phrv` / `.pv` / `.pvrefs` / `phrasal_verb_box` / pvrefs 列表内的 `.xh` → phrasal_verb
    """
    out: List[PhraseItem] = []
    hw = headword.strip().lower()
    seen = set()

    def _add(text: str, kind: str) -> None:
        text = _clean_text(text)
        if not text or text.lower() == hw:
            return
        key = (kind, text.lower())
        if key in seen:
            return
        seen.add(key)
        out.append(PhraseItem(phrase=text, kind=kind, related_headword=headword))

    for m in _PHRASE_CLASS_RE.finditer(html):
        cls = m.group(1).lower()
        kind = "idiom" if cls in ("idm", "idm-g", "idmrefs", "cf") else "phrasal_verb"
        _add(m.group(2), kind)

    # pvrefs/idmrefs 列表中的交叉引用短语
    for ul in _PVREFS_UL_RE.finditer(html):
        kind = "idiom" if ul.group(1).lower() == "idmrefs" else "phrasal_verb"
        for xh in _XH_RE.finditer(ul.group(2)):
            _add(xh.group(1), kind)

    return out


def _find_phonetic(container_html: str) -> str:
    m = _PHON_INNER_RE.search(container_html)
    return _clean_text(m.group(1), 40) if m else ""


# ---------- 完整词条解析 ----------
def parse_entry(word: str, dictionary_name: str, html: str) -> DictionaryEntry:
    """把 raw HTML 解析为结构化的 DictionaryEntry（懒调用，命中时缓存）。

    尽力而为：未知结构不抛错，字段留空。
    """
    entry = DictionaryEntry(word=word, dictionary_name=dictionary_name, raw_content=html)

    # 词头
    m = _HEADWORD_RE.search(html)
    if m:
        entry.word = _clean_text(m.group(1)) or word

    # 音标（英 / 美）
    br = _PHONS_BR_RE.search(html)
    am = _PHONS_AM_RE.search(html)
    if br:
        entry.phonetic_uk = _find_phonetic(br.group(1))
    if am:
        entry.phonetic_us = _find_phonetic(am.group(1))

    # 词性（去重保序）
    seen: List[str] = []
    for m in _POS_RE.finditer(html):
        p = _clean_text(m.group(1))
        if p and p not in seen:
            seen.append(p)
    entry.pos_tags = seen

    # 例句
    for m in _EXAMPLE_RE.finditer(html):
        ex = _clean_text(m.group(1))
        if ex and ex not in entry.examples:
            entry.examples.append(ex)
        if len(entry.examples) >= 5:  # 释义页例句很多，取前几条足够
            break

    # 习语 / 短语动词（用同一个抽取器，按 kind 分流）
    for p in extract_phrases(html, word):
        if p.kind == "idiom":
            entry.idioms.append(p)
        else:
            entry.phrasal_verbs.append(p)
    return entry


# 兼容旧名：外部可调 parse 而非 parse_entry
parse = parse_entry
