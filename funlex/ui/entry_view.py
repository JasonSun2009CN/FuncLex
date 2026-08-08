"""词条显示区 - QTextBrowser 子类，直接 setHtml 渲染 MDX 原始 HTML"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QTextBrowser

from .styles import get_entry_default_css


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
        self.show_placeholder()

    def _setup_font(self) -> None:
        font = QFont()
        font.setStyleHint(QFont.SansSerif)
        # 字体族由 QSS 控制，这里只设 hint
        self.setFont(font)

    def _inject_default_css(self) -> None:
        """注入 fallback CSS 到 QTextBrowser"""
        css = get_entry_default_css()
        # setDefaultStyleSheet 会在 setHtml 时包裹一层 <style>
        self.document().setDefaultStyleSheet(css)

    # ---------- 公共 API ----------
    def set_content(self, html: str, word: str = "") -> None:
        """设置词条 HTML 内容"""
        if not html:
            self.show_not_found(word)
            return
        # 用 <body> 包裹，让 setHtml 完整渲染
        # 注意：setDefaultStyleSheet 已注入 <style>，这里不要再嵌
        wrapped = f"<body>{html}</body>"
        self.setHtml(wrapped)

    def show_not_found(self, word: str = "") -> None:
        msg = f"未找到该单词：<b>{word}</b>" if word else "未找到该单词"
        html = f"""
<body>
<div style="padding: 40px; text-align: center; color: #8e8e93;">
    <div style="font-size: 48px; margin-bottom: 12px;">📖</div>
    <div style="font-size: 18px; color: #1d1d1f;">{msg}</div>
    <div style="font-size: 13px; margin-top: 12px;">试试其他拼写或切换词典</div>
</div>
</body>
"""
        self.setHtml(html)

    def show_placeholder(self) -> None:
        html = """
<body>
<div style="padding: 60px 40px; text-align: center; color: #8e8e93;">
    <div style="font-size: 56px; margin-bottom: 16px;">🔍</div>
    <div style="font-size: 20px; color: #1d1d1f; font-weight: 500;">FuncLex</div>
    <div style="font-size: 14px; margin-top: 12px; color: #6e6e73;">输入单词开始查询</div>
    <div style="font-size: 12px; margin-top: 16px; color: #8e8e93;">本地 MDX 词典 · 完全离线</div>
</div>
</body>
"""
        self.setHtml(html)

    def show_loading(self, word: str = "") -> None:
        html = f"""
<body>
<div style="padding: 40px; text-align: center; color: #8e8e93;">
    <div style="font-size: 16px;">正在查询 "{word}"...</div>
</div>
</body>
"""
        self.setHtml(html)
