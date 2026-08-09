"""词条显示区 - QTextBrowser 子类，直接 setHtml 渲染 MDX 原始 HTML"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QTextBrowser

from .styles import get_entry_default_css, is_dark, sanitize_html


def _state_colors() -> dict:
    """占位/未找到/加载页的文字配色（按当前主题）"""
    if is_dark():
        return {
            "heading": "#f2f2f7",
            "muted": "#98989d",
            "body": "#a1a1a6",
            "faint": "#8e8e93",
            "divider": "rgba(255,255,255,0.15)",
        }
    return {
        "heading": "#1d1d1f",
        "muted": "#8e8e93",
        "body": "#6e6e73",
        "faint": "#a1a1a6",
        "divider": "#d2d2d7",
    }


class EntryView(QTextBrowser):
    """词条视图。

    - set_content(html, word): 设置 HTML 内容，自动注入 fallback CSS
    - show_not_found(word): 友好的"未找到"提示
    - show_placeholder(): 启动时的占位提示
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("entryView")
        self.setOpenExternalLinks(True)
        self.setOpenLinks(False)  # 内链暂不处理，避免 anchorNavigationRequested 噪音
        self._setup_font()
        self._inject_default_css()
        # 当前展示状态（供切主题后按原状态重渲染）：placeholder/not_found/loading/content
        self._state = "placeholder"
        self._last_word = ""
        self.show_placeholder()

    def _inject_default_css(self) -> None:
        """注入 fallback CSS 到 QTextBrowser（按当前主题）"""
        css = get_entry_default_css()
        # setDefaultStyleSheet 会在 setHtml 时包裹一层 <style>
        self.document().setDefaultStyleSheet(css)

    def reapply_theme(self) -> None:
        """主题切换后重注入默认 CSS，并按原状态重渲染。"""
        self._inject_default_css()
        if self._state == "content":
            return  # 词条内容由合并视图负责重渲染
        if self._state == "not_found":
            self.show_not_found(self._last_word)
        elif self._state == "loading":
            self.show_loading(self._last_word)
        else:
            self.show_placeholder()

    def _setup_font(self) -> None:
        font = QFont()
        font.setStyleHint(QFont.SansSerif)
        # 字体族由 QSS 控制，这里只设 hint
        self.setFont(font)

    # ---------- 公共 API ----------
    def set_content(self, html: str, word: str = "") -> None:
        """设置词条 HTML 内容"""
        if not html:
            self.show_not_found(word)
            return
        # 剥离 <link>/<script>（QTextDocument 遇开头 <link> 会丢文档），再包裹渲染
        html = sanitize_html(html)
        wrapped = f"<body>{html}</body>"
        self._state = "content"
        self._last_word = word
        self.setHtml(wrapped)

    def show_not_found(self, word: str = "") -> None:
        self._state = "not_found"
        self._last_word = word
        c = _state_colors()
        msg = f"未找到该单词：<b>{word}</b>" if word else "未找到该单词"
        html = f"""
<body>
<div style="padding: 48px 40px; text-align: center; color: {c['muted']};">
    <div style="font-size: 20px; color: {c['heading']}; font-weight: 500;">{msg}</div>
    <div style="font-size: 13px; margin-top: 12px; color: {c['body']};">试试其他拼写或切换词典</div>
</div>
</body>
"""
        self.setHtml(html)

    def show_placeholder(self) -> None:
        self._state = "placeholder"
        self._last_word = ""
        c = _state_colors()
        html = f"""
<body>
<div style="padding: 64px 40px; text-align: center; color: {c['muted']};">
    <div style="font-size: 24px; color: {c['heading']}; font-weight: 600; letter-spacing: -0.3px;">FuncLex</div>
    <div style="width: 36px; height: 1px; background-color: {c['divider']}; margin: 18px auto;"></div>
    <div style="font-size: 14px; color: {c['body']};">输入单词开始查询</div>
    <div style="font-size: 12px; margin-top: 14px; color: {c['faint']};">本地 MDX 词典 · 完全离线</div>
</div>
</body>
"""
        self.setHtml(html)

    def show_loading(self, word: str = "") -> None:
        self._state = "loading"
        self._last_word = word
        c = _state_colors()
        html = f"""
<body>
<div style="padding: 48px 40px; text-align: center; color: {c['muted']};">
    <div style="font-size: 15px; color: {c['body']};">正在查询 “{word}”…</div>
</div>
</body>
"""
        self.setHtml(html)
