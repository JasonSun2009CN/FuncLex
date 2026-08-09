"""QSS 样式 - Liquid Glass Minimalism（Minimalism 2.0 + Liquid Glass）

设计系统（ui-ux-pro-max 推荐）：
- STYLE: Liquid Glass —— 半透明玻璃面板、柔和冷灰渐变背景、系统蓝点缀
- COLORS: 玻璃白 #FFFFFF / 次色 #E5E5E5 / CTA #007AFF / 文字 #1D1D1F
- TYPOGRAPHY: 系统字体栈（PingFang SC / SF Pro / Inter）
- 原则：克制留白、细发丝边框、小圆角(12-16px)、低饱和辅助色、焦点环明显

说明：Qt 6.11 未暴露 macOS 原生 vibrancy，采用纯 QSS 半透明"假玻璃"，
面板叠在柔和渐变背景上形成浮起感，稳定且无渲染风险。

主题：浅色 = MAIN_QSS（默认，原样保留）；深色 = 在其后叠加 DARK_QSS
（同选择器等优先级后者胜），Entry 词条 HTML 用 ENTRY_CSS_TPL 渲染两套 token。
模块级 `_current_theme` 由 set_theme()/refresh_theme() 维护，全 app 单一主题。
"""
from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication

# QTextDocument 的 HTML 导入器遇到开头的 <link> 会丢弃整个文档
# （实测：raw_content 以 <link rel="stylesheet"> 开头时 setHtml 后 blockCount==1、正文为空）。
# 渲染前剥离 <link>/<script>/注释，避免内容丢失。
_HTML_STRIP_RE = re.compile(
    r"<link[^>]*>|<script[^>]*>.*?</script>|<!--.*?-->", re.I | re.S
)


def sanitize_html(html: str) -> str:
    """剥离会破坏 QTextDocument HTML 导入的标签（link/script/注释）。"""
    if not html:
        return html
    return _HTML_STRIP_RE.sub("", html)


# ---------- 主题状态（浅色/深色/跟随系统，全 app 单一） ----------
_THEME_SETTING = "light"   # 用户选择：light / dark / system
_CURRENT_THEME = "light"   # 生效主题：light / dark


def resolve_theme(theme: str) -> str:
    """把用户设置解析为生效主题；'system' 跟随系统外观。"""
    if theme == "system":
        try:
            if QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark:
                return "dark"
        except Exception:
            pass
        return "light"
    return theme if theme in ("light", "dark") else "light"


def set_theme(theme: str) -> None:
    """设置用户主题选择并立即解析生效。"""
    global _THEME_SETTING, _CURRENT_THEME
    _THEME_SETTING = theme if theme in ("light", "dark", "system") else "light"
    _CURRENT_THEME = resolve_theme(_THEME_SETTING)


def refresh_theme() -> bool:
    """'system' 模式下按当前系统外观刷新；返回生效主题是否变化（供重设 QSS）。"""
    global _CURRENT_THEME
    new = resolve_theme(_THEME_SETTING)
    changed = new != _CURRENT_THEME
    _CURRENT_THEME = new
    return changed


def current_theme() -> str:
    return _CURRENT_THEME


def is_dark() -> bool:
    return _CURRENT_THEME == "dark"


# 主样式（Liquid Glass Minimalism）
MAIN_QSS = """
/* ============ 全局 ============ */
QMainWindow {
    /* 柔和冷灰渐变背景，玻璃卡片在其上"浮起" */
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #eff0f5, stop:1 #e4e5ee);
}
QWidget {
    font-family: -apple-system, "PingFang SC", "SF Pro Text", "Inter", "Helvetica Neue", "Microsoft YaHei", sans-serif;
    color: #1d1d1f;
    font-size: 13px;
}
QToolTip {
    background-color: rgba(255,255,255,0.95);
    color: #1d1d1f;
    border: 1px solid rgba(0,0,0,0.08);
    border-radius: 8px;
    padding: 6px 10px;
}

/* ============ 搜索区（顶部玻璃条） ============ */
QWidget#searchContainer {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 rgba(255,255,255,0.82), stop:1 rgba(255,255,255,0.45));
    border-bottom: 1px solid rgba(255,255,255,0.85);
}
QLineEdit#searchInput {
    background-color: rgba(255,255,255,0.55);
    border: 1px solid rgba(0,0,0,0.05);
    border-radius: 12px;
    padding: 9px 14px;
    font-size: 15px;
    color: #1d1d1f;
    selection-background-color: #007aff;
    selection-color: #ffffff;
}
QLineEdit#searchInput:hover {
    background-color: rgba(255,255,255,0.7);
}
QLineEdit#searchInput:focus {
    border: 1px solid rgba(0,122,255,0.55);
    background-color: rgba(255,255,255,0.88);
}
QLineEdit#searchInput::placeholder {
    color: #8e8e93;
}
QPushButton#clearButton {
    background-color: transparent;
    border: none;
    color: #8e8e93;
    font-size: 14px;
    padding: 4px 8px;
    border-radius: 6px;
}
QPushButton#clearButton:hover {
    background-color: rgba(0,0,0,0.06);
    color: #1d1d1f;
}

/* ============ 搜索补全弹窗 ============ */
QListWidget#suggestPopup {
    background-color: rgba(255,255,255,0.96);
    border: 1px solid rgba(0,0,0,0.08);
    border-radius: 10px;
    padding: 4px;
    outline: none;
    font-size: 13px;
    color: #1d1d1f;
}
QListWidget#suggestPopup::item {
    padding: 6px 12px;
    border-radius: 6px;
    margin: 1px 2px;
}
QListWidget#suggestPopup::item:hover {
    background-color: rgba(0,122,255,0.08);
}
QListWidget#suggestPopup::item:selected {
    background-color: rgba(0,122,255,0.18);
    color: #0a4fa0;
}
QListWidget#suggestPopup::item:selected:hover {
    background-color: rgba(0,122,255,0.24);
}

/* ============ 发音按钮（玻璃胶囊） ============ */
QPushButton#pronounceBtn {
    background-color: rgba(255,255,255,0.6);
    border: 1px solid rgba(255,255,255,0.9);
    border-radius: 10px;
    font-size: 14px;
    padding: 5px 12px;
    min-width: 34px;
}
QPushButton#pronounceBtn:hover:enabled {
    border: 1px solid rgba(0,122,255,0.5);
    background-color: rgba(0,122,255,0.12);
}
QPushButton#pronounceBtn:pressed:enabled {
    background-color: rgba(0,122,255,0.2);
}
QPushButton#pronounceBtn:disabled {
    color: #c7c7cc;
    background-color: rgba(255,255,255,0.35);
}

/* ============ 内容区（玻璃卡片） ============ */
QStackedWidget, QSplitter {
    background: transparent;
}
QTextBrowser#entryView {
    background-color: rgba(255,255,255,0.78);
    border: 1px solid rgba(255,255,255,0.95);
    border-radius: 14px;
    margin: 12px;
    padding: 14px 20px;
    font-size: 15px;
    line-height: 1.6;
}
QTextBrowser#entryView:focus {
    border: 1px solid rgba(0,122,255,0.35);
}
QSplitter::handle {
    background: transparent;
    width: 8px;
    margin: 14px 2px;
    border-radius: 4px;
}
QSplitter::handle:hover {
    background: rgba(0,122,255,0.2);
}

/* ============ 多词典合并视图（可折叠玻璃卡片） ============ */
QScrollArea#mergedView,
QScrollArea#mergedView > QWidget > QWidget {
    background: transparent;
    border: none;
}
QFrame#dictCard {
    background-color: rgba(255,255,255,0.78);
    border: 1px solid rgba(255,255,255,0.95);
    border-radius: 14px;
}
QPushButton#dictCardHeader {
    background: transparent;
    border: none;
    border-bottom: 1px solid rgba(0,0,0,0.06);
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
    text-align: left;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 600;
    color: #1d1d1f;
}
QPushButton#dictCardHeader:hover {
    background-color: rgba(0,122,255,0.07);
}
/* 卡片内部词条：去掉浮起卡片的独立边距/边框，贴合卡片 */
QFrame#dictCard QTextBrowser#entryView {
    margin: 0;
    border: none;
    border-radius: 0;
    background: transparent;
    padding: 8px 18px 14px 18px;
}
QLabel#mergedPlaceholder {
    color: #8e8e93;
    font-size: 14px;
    padding: 60px;
}

/* ============ 笔记卡片（合并视图底部，蓝色描边区分词典卡） ============ */
QFrame#notesCard {
    background-color: rgba(255,255,255,0.72);
    border: 1px solid rgba(0,122,255,0.18);
    border-radius: 14px;
}
QLabel#notesTitle {
    font-size: 13px;
    font-weight: 600;
    color: #1d1d1f;
}
QLabel#notesWord {
    font-size: 12px;
    color: #007aff;
}
QLabel#notesDirty {
    font-size: 11px;
    color: #ff9500;
}
QTextEdit#notesEdit {
    background-color: rgba(255,255,255,0.6);
    border: 1px solid rgba(0,0,0,0.06);
    border-radius: 8px;
    padding: 6px 8px;
    font-size: 13px;
    color: #1d1d1f;
    selection-background-color: #007aff;
    selection-color: #ffffff;
}
QTextEdit#notesEdit:focus {
    border: 1px solid rgba(0,122,255,0.5);
    background-color: rgba(255,255,255,0.85);
}
QTextEdit#notesEdit::placeholder {
    color: #a1a1a6;
}
QLabel#notesHint {
    font-size: 11px;
    color: #a1a1a6;
}
QPushButton#notesSaveBtn {
    background-color: #007aff;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 5px 16px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton#notesSaveBtn:hover:enabled {
    background-color: #0a84ff;
}
QPushButton#notesSaveBtn:disabled {
    background-color: rgba(0,122,255,0.35);
    color: rgba(255,255,255,0.85);
}
QPushButton#notesDeleteBtn {
    background: transparent;
    border: 1px solid rgba(255,69,58,0.35);
    border-radius: 8px;
    color: #ff453a;
    font-size: 12px;
    padding: 5px 12px;
}
QPushButton#notesDeleteBtn:hover {
    background-color: rgba(255,69,58,0.1);
    border-color: rgba(255,69,58,0.6);
}

/* ============ 历史侧边栏（玻璃侧板） ============ */
QWidget#historyPanel {
    background: qlineargradient(x1:1,y1:0,x2:0,y2:0,
                stop:0 rgba(255,255,255,0.5), stop:1 rgba(255,255,255,0.28));
    border-left: 1px solid rgba(255,255,255,0.9);
}
QLabel#panelTitle {
    font-size: 13px;
    font-weight: 600;
    color: #1d1d1f;
}
QLabel#panelCount {
    font-size: 11px;
    color: #6e6e73;
    background-color: rgba(0,0,0,0.05);
    border-radius: 8px;
    padding: 1px 7px;
}
QPushButton#panelClearBtn {
    background: transparent;
    border: none;
    color: #007aff;
    font-size: 12px;
    padding: 2px 6px;
    border-radius: 6px;
}
QPushButton#panelClearBtn:hover {
    background-color: rgba(0,122,255,0.12);
}
QLineEdit#historyFilter {
    background-color: rgba(255,255,255,0.5);
    border: 1px solid rgba(0,0,0,0.05);
    border-radius: 8px;
    padding: 5px 10px;
    margin: 0 8px;
    font-size: 12px;
    color: #1d1d1f;
}
QLineEdit#historyFilter:focus {
    border: 1px solid rgba(0,122,255,0.5);
    background-color: rgba(255,255,255,0.75);
}
QLineEdit#historyFilter::placeholder {
    color: #a1a1a6;
}
QTreeWidget#historyList {
    background-color: transparent;
    border: none;
    font-size: 13px;
    color: #1d1d1f;
    outline: none;
}
QTreeWidget#historyList::item {
    padding: 5px 8px;
    border-radius: 8px;
    margin: 1px 6px;
}
QTreeWidget#historyList::item:hover {
    background-color: rgba(255,255,255,0.55);
}
QTreeWidget#historyList::item:selected {
    background-color: rgba(0,122,255,0.14);
    color: #0a4fa0;
}

/* ============ 设置对话框（玻璃卡片） ============ */
QDialog {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #f4f4f8, stop:1 #e8e9f0);
}
QDialog QLineEdit, QDialog QSpinBox, QDialog QComboBox {
    background-color: rgba(255,255,255,0.8);
    border: 1px solid rgba(0,0,0,0.07);
    border-radius: 8px;
    padding: 5px 9px;
}
QDialog QLineEdit:focus, QDialog QSpinBox:focus {
    border: 1px solid rgba(0,122,255,0.5);
}
QDialog QListWidget {
    background-color: rgba(255,255,255,0.75);
    border: 1px solid rgba(0,0,0,0.07);
    border-radius: 10px;
    padding: 4px;
    outline: none;
}
QDialog QPushButton {
    background-color: rgba(255,255,255,0.7);
    border: 1px solid rgba(0,0,0,0.07);
    border-radius: 8px;
    padding: 6px 14px;
}
QDialog QPushButton:hover {
    background-color: rgba(255,255,255,0.95);
    border-color: rgba(0,122,255,0.4);
}
QDialog QPushButton:default {
    background-color: #007aff;
    color: #ffffff;
    border: none;
}
QDialog QPushButton:default:hover {
    background-color: #0a84ff;
}
QDialog QRadioButton::indicator {
    width: 14px; height: 14px;
}
QDialog QRadioButton::indicator:checked {
    background-color: #007aff;
    border: 2px solid #ffffff;
    border-radius: 7px;
}

/* ============ 所有笔记对话框 ============ */
QLineEdit#notesFilter {
    background-color: rgba(255,255,255,0.8);
    border: 1px solid rgba(0,0,0,0.07);
    border-radius: 8px;
    padding: 5px 10px;
    max-width: 220px;
}
QLineEdit#notesFilter:focus {
    border: 1px solid rgba(0,122,255,0.5);
}
QListWidget#notesList {
    background-color: rgba(255,255,255,0.75);
    border: 1px solid rgba(0,0,0,0.07);
    border-radius: 10px;
    padding: 4px;
    outline: none;
    font-size: 13px;
    color: #1d1d1f;
}
QListWidget#notesList::item {
    padding: 7px 10px;
    border-radius: 6px;
    margin: 1px 0;
}
QListWidget#notesList::item:hover {
    background-color: rgba(0,122,255,0.08);
}
QListWidget#notesList::item:selected {
    background-color: rgba(0,122,255,0.18);
    color: #0a4fa0;
}

/* ============ 状态栏（极简） ============ */
QStatusBar {
    background: transparent;
    color: #6e6e73;
    border-top: 1px solid rgba(255,255,255,0.6);
    font-size: 12px;
    padding: 3px 12px;
}
QStatusBar::item { border: none; }

/* ============ 滚动条（细、半透明） ============ */
QScrollBar:vertical {
    background: transparent;
    width: 9px;
    margin: 4px;
}
QScrollBar::handle:vertical {
    background: rgba(0,0,0,0.14);
    border-radius: 4px;
    min-height: 32px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(0,0,0,0.24);
}
QScrollBar:horizontal {
    background: transparent;
    height: 9px;
    margin: 4px;
}
QScrollBar::handle:horizontal {
    background: rgba(0,0,0,0.14);
    border-radius: 4px;
    min-width: 32px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(0,0,0,0.24);
}
QScrollBar::add-line, QScrollBar::sub-line {
    height: 0; width: 0;
    background: none;
}
QScrollBar::add-page, QScrollBar::sub-page {
    background: transparent;
}
"""


# 深色主题覆盖块：叠加在浅色之上，同选择器等优先级后者胜（浅色主题零改动）。
# 覆盖原则：只重写"表面/文字/边框"的浅色值；强调色(#007aff)、语义色(#ff9500/#af52de/#ff453a)两主题通用。
DARK_QSS = """
/* ============ 深色主题（Liquid Glass Dark） ============ */
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #1c1d24, stop:1 #141519);
}
QWidget {
    color: #f2f2f7;
}
QToolTip {
    background-color: rgba(42,44,54,0.97);
    color: #f2f2f7;
    border: 1px solid rgba(255,255,255,0.10);
}

/* 搜索区 */
QWidget#searchContainer {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 rgba(32,33,41,0.88), stop:1 rgba(28,29,36,0.6));
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
QLineEdit#searchInput {
    background-color: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.08);
    color: #f2f2f7;
    selection-background-color: #007aff;
    selection-color: #ffffff;
}
QLineEdit#searchInput:hover {
    background-color: rgba(255,255,255,0.10);
}
QLineEdit#searchInput:focus {
    border: 1px solid rgba(0,122,255,0.6);
    background-color: rgba(255,255,255,0.12);
}
QLineEdit#searchInput::placeholder {
    color: #8e8e93;
}
QPushButton#clearButton {
    color: #8e8e93;
}
QPushButton#clearButton:hover {
    background-color: rgba(255,255,255,0.08);
    color: #f2f2f7;
}

/* 搜索补全弹窗 */
QListWidget#suggestPopup {
    background-color: rgba(38,40,50,0.97);
    border: 1px solid rgba(255,255,255,0.12);
    color: #f2f2f7;
}
QListWidget#suggestPopup::item:hover {
    background-color: rgba(0,122,255,0.12);
}
QListWidget#suggestPopup::item:selected {
    background-color: rgba(0,122,255,0.3);
    color: #bcd9ff;
}
QListWidget#suggestPopup::item:selected:hover {
    background-color: rgba(0,122,255,0.38);
}

/* 发音按钮 */
QPushButton#pronounceBtn {
    background-color: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.10);
}
QPushButton#pronounceBtn:hover:enabled {
    border: 1px solid rgba(0,122,255,0.5);
    background-color: rgba(0,122,255,0.18);
}
QPushButton#pronounceBtn:pressed:enabled {
    background-color: rgba(0,122,255,0.28);
}
QPushButton#pronounceBtn:disabled {
    color: #5c5c66;
    background-color: rgba(255,255,255,0.04);
}

/* 词条玻璃卡片 */
QTextBrowser#entryView {
    background-color: rgba(38,40,50,0.8);
    border: 1px solid rgba(255,255,255,0.08);
}
QTextBrowser#entryView:focus {
    border: 1px solid rgba(0,122,255,0.4);
}
QFrame#dictCard {
    background-color: rgba(38,40,50,0.8);
    border: 1px solid rgba(255,255,255,0.08);
}
QPushButton#dictCardHeader {
    border-bottom: 1px solid rgba(255,255,255,0.08);
    color: #f2f2f7;
}
QPushButton#dictCardHeader:hover {
    background-color: rgba(0,122,255,0.12);
}
QLabel#mergedPlaceholder {
    color: #8e8e93;
}

/* 历史侧边栏 */
QWidget#historyPanel {
    background: qlineargradient(x1:1,y1:0,x2:0,y2:0,
                stop:0 rgba(34,35,43,0.72), stop:1 rgba(28,29,36,0.45));
    border-left: 1px solid rgba(255,255,255,0.06);
}
QLabel#panelTitle {
    color: #f2f2f7;
}
QLabel#panelCount {
    color: #a1a1a6;
    background-color: rgba(255,255,255,0.07);
}
QPushButton#panelClearBtn {
    color: #4d9fff;
}
QPushButton#panelClearBtn:hover {
    background-color: rgba(0,122,255,0.18);
}
QLineEdit#historyFilter {
    background-color: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.08);
    color: #f2f2f7;
}
QLineEdit#historyFilter:focus {
    border: 1px solid rgba(0,122,255,0.6);
    background-color: rgba(255,255,255,0.10);
}
QLineEdit#historyFilter::placeholder {
    color: #8e8e93;
}
QTreeWidget#historyList {
    color: #f2f2f7;
}
QTreeWidget#historyList::item:hover {
    background-color: rgba(255,255,255,0.07);
}
QTreeWidget#historyList::item:selected {
    background-color: rgba(0,122,255,0.28);
    color: #bcd9ff;
}

/* 笔记卡片 */
QFrame#notesCard {
    background-color: rgba(38,40,50,0.76);
    border: 1px solid rgba(0,122,255,0.35);
}
QLabel#notesTitle {
    color: #f2f2f7;
}
QLabel#notesWord {
    color: #4d9fff;
}
QTextEdit#notesEdit {
    background-color: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.08);
    color: #f2f2f7;
    selection-background-color: #007aff;
    selection-color: #ffffff;
}
QTextEdit#notesEdit:focus {
    border: 1px solid rgba(0,122,255,0.6);
    background-color: rgba(255,255,255,0.10);
}
QTextEdit#notesEdit::placeholder {
    color: #8e8e93;
}
QLabel#notesHint {
    color: #8e8e93;
}
QPushButton#notesSaveBtn:disabled {
    background-color: rgba(0,122,255,0.25);
    color: rgba(255,255,255,0.6);
}
QPushButton#notesDeleteBtn {
    border: 1px solid rgba(255,69,58,0.4);
    color: #ff6b61;
}
QPushButton#notesDeleteBtn:hover {
    background-color: rgba(255,69,58,0.16);
    border-color: rgba(255,69,58,0.6);
}

/* 设置 / 笔记对话框 */
QDialog {
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #22242c, stop:1 #191a20);
}
QDialog QLineEdit, QDialog QSpinBox, QDialog QComboBox {
    background-color: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.10);
    color: #f2f2f7;
    selection-background-color: #007aff;
    selection-color: #ffffff;
}
QDialog QLineEdit:focus, QDialog QSpinBox:focus {
    border: 1px solid rgba(0,122,255,0.6);
}
QDialog QComboBox QAbstractItemView {
    background-color: #22242c;
    color: #f2f2f7;
    selection-background-color: rgba(0,122,255,0.3);
    border: 1px solid rgba(255,255,255,0.10);
}
QDialog QListWidget {
    background-color: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.10);
    color: #f2f2f7;
}
QDialog QPushButton {
    background-color: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.10);
    color: #f2f2f7;
}
QDialog QPushButton:hover {
    background-color: rgba(255,255,255,0.14);
    border-color: rgba(0,122,255,0.5);
}
QDialog QPushButton:default {
    background-color: #007aff;
    color: #ffffff;
}
QDialog QPushButton:default:hover {
    background-color: #0a84ff;
}
QDialog QRadioButton::indicator:checked {
    background-color: #007aff;
    border: 2px solid #ffffff;
}

/* 笔记对话框控件 */
QLineEdit#notesFilter {
    background-color: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.10);
    color: #f2f2f7;
}
QLineEdit#notesFilter:focus {
    border: 1px solid rgba(0,122,255,0.6);
}
QListWidget#notesList {
    background-color: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.10);
    color: #f2f2f7;
}
QListWidget#notesList::item:hover {
    background-color: rgba(0,122,255,0.12);
}
QListWidget#notesList::item:selected {
    background-color: rgba(0,122,255,0.28);
    color: #bcd9ff;
}

/* 状态栏 / 滚动条 */
QStatusBar {
    color: #8e8e93;
    border-top: 1px solid rgba(255,255,255,0.06);
}
QScrollBar::handle:vertical {
    background: rgba(255,255,255,0.14);
}
QScrollBar::handle:vertical:hover {
    background: rgba(255,255,255,0.24);
}
QScrollBar::handle:horizontal {
    background: rgba(255,255,255,0.14);
}
QScrollBar::handle:horizontal:hover {
    background: rgba(255,255,255,0.24);
}
"""


# EntryView 内嵌 HTML 的默认样式（Liquid Glass 一致、保证词条可读性）
# 用 token 渲染两套主题；`{text}` 等替换自 _ENTRY_PALETTES。
ENTRY_CSS_TPL = """
<style>
body {
    font-family: -apple-system, "PingFang SC", "SF Pro Text", "Inter", "Helvetica Neue", sans-serif;
    color: {text};
    line-height: 1.7;
    margin: 0;
    padding: 0;
}
h1, h2, h3 {
    color: {text};
    margin-top: 14px;
    margin-bottom: 8px;
}
/* 牛津 headword */
.headword, .hw {
    font-size: 24px;
    font-weight: 600;
    letter-spacing: -0.2px;
    color: {text};
}
/* 音标 */
.phon, .phons_br, .phons_am, .pron {
    color: #007aff;
    font-size: 14px;
    margin-left: 6px;
    font-style: normal;
}
/* 词性标签 */
.pos, .posi, .partofspeech {
    color: {muted};
    font-style: italic;
    font-size: 13px;
    margin-right: 4px;
}
/* 例句 */
.example, .eg, .examples, .x {
    color: {text_subtle};
    font-style: italic;
    margin: 4px 0 4px 16px;
    display: block;
}
/* 中文释义块 */
.cn, .chn, .def_cn, .trans {
    color: {text};
}
/* 短语动词 / 习语 */
.phrv, .phrasalverb, .pv {
    color: #ff9500;
    font-weight: 500;
}
.idm, .idiom {
    color: #af52de;
    font-weight: 500;
}
/* 链接 */
a {
    color: #007aff;
    text-decoration: none;
}
a:hover {
    text-decoration: underline;
}
p {
    margin: 6px 0;
}
ul, ol {
    margin: 4px 0;
    padding-left: 24px;
}
li {
    margin: 3px 0;
}
/* 相关短语 / 习语区块（P2.3） */
.related-block {
    margin-top: 26px;
    padding-top: 16px;
    border-top: 1px solid {divider};
}
.related-title {
    font-size: 13px;
    font-weight: 600;
    color: {muted};
    letter-spacing: 0.3px;
    margin-bottom: 10px;
}
.related-items {
    display: block;
}
a.related-item {
    display: inline-block;
    margin: 3px 6px 3px 0;
    padding: 4px 12px;
    border-radius: 14px;
    background-color: {chip_bg};
    color: {chip_text};
    font-size: 13px;
    text-decoration: none;
}
a.related-item:hover {
    background-color: {chip_bg_hover};
}
</style>
"""

# 词条 HTML 的两套配色 token
_ENTRY_PALETTES = {
    "light": {
        "text": "#1d1d1f",
        "text_subtle": "#3a3a3c",
        "muted": "#8e8e93",
        "divider": "rgba(0,0,0,0.08)",
        "chip_text": "#0a5cbf",
        "chip_bg": "rgba(0,122,255,0.08)",
        "chip_bg_hover": "rgba(0,122,255,0.16)",
    },
    "dark": {
        "text": "#f2f2f7",
        "text_subtle": "#c7c7cc",
        "muted": "#98989d",
        "divider": "rgba(255,255,255,0.12)",
        "chip_text": "#6ab0ff",
        "chip_bg": "rgba(0,122,255,0.18)",
        "chip_bg_hover": "rgba(0,122,255,0.28)",
    },
}


def get_main_qss() -> str:
    """返回主窗口 QSS（浅色原样；深色叠加 DARK_QSS 覆盖块）"""
    if _CURRENT_THEME == "dark":
        return MAIN_QSS + DARK_QSS
    return MAIN_QSS


def get_entry_default_css(theme: str | None = None) -> str:
    """返回 EntryView 注入的默认 CSS（HTML 片段形式），按生效主题渲染 token。

    用逐 token replace（而非 str.format），避免与 CSS 块花括号 `{}` 冲突。
    """
    key = theme if theme in _ENTRY_PALETTES else _CURRENT_THEME
    out = ENTRY_CSS_TPL
    for k, v in _ENTRY_PALETTES[key].items():
        out = out.replace("{" + k + "}", v)
    return out
