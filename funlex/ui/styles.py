"""QSS 样式 - macOS 风格的现代简洁主题"""

# 主样式（颜色集中管理，方便后续切换暗色主题）
MAIN_QSS = """
/* 全局 */
QMainWindow {
    background-color: #f5f5f7;
}

QWidget {
    font-family: -apple-system, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif;
    color: #1d1d1f;
}

/* 搜索框 */
QFrame#searchContainer {
    background-color: #ffffff;
    border-bottom: 1px solid #e5e5ea;
}

QLineEdit#searchInput {
    background-color: #f5f5f7;
    border: 1px solid #d2d2d7;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 15px;
    color: #1d1d1f;
    selection-background-color: #007aff;
    selection-color: #ffffff;
}

QLineEdit#searchInput:focus {
    border: 1px solid #007aff;
    background-color: #ffffff;
}

QPushButton#clearButton {
    background-color: transparent;
    border: none;
    color: #8e8e93;
    font-size: 14px;
    padding: 4px 8px;
    border-radius: 4px;
}

QPushButton#clearButton:hover {
    background-color: #e5e5ea;
    color: #1d1d1f;
}

/* 词典切换下拉框 */
QComboBox#dictSelector {
    background-color: #ffffff;
    border: 1px solid #d2d2d7;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
    min-width: 180px;
}

QComboBox#dictSelector:hover {
    border: 1px solid #007aff;
}

QComboBox#dictSelector::drop-down {
    border: none;
    width: 18px;
}

QComboBox#dictSelector QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #d2d2d7;
    selection-background-color: #007aff;
    selection-color: #ffffff;
    padding: 4px;
}

/* 词条显示区 */
QTextBrowser#entryView {
    background-color: #ffffff;
    border: none;
    padding: 16px 24px;
    font-size: 15px;
    line-height: 1.5;
}

/* 状态栏 */
QStatusBar {
    background-color: #f5f5f7;
    color: #6e6e73;
    border-top: 1px solid #e5e5ea;
    font-size: 12px;
}

/* 滚动条 */
QScrollBar:vertical {
    background-color: transparent;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #c7c7cc;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background-color: #a1a1a6;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
    background: none;
}
QScrollBar:horizontal {
    background-color: transparent;
    height: 10px;
}
QScrollBar::handle:horizontal {
    background-color: #c7c7cc;
    border-radius: 5px;
    min-width: 30px;
}
"""


# EntryView 内嵌的 HTML CSS（用于美化 MDX 原始 HTML 排版）
# QTextBrowser 不支持 flex/grid，只能用基础 CSS
ENTRY_DEFAULT_CSS = """
<style>
body {
    font-family: -apple-system, "PingFang SC", "Helvetica Neue", "Microsoft YaHei", sans-serif;
    color: #1d1d1f;
    line-height: 1.6;
    margin: 0;
    padding: 0;
}
h1, h2, h3 {
    color: #1d1d1f;
    margin-top: 12px;
    margin-bottom: 8px;
}
/* 牛津 headword */
.headword, .hw {
    font-size: 22px;
    font-weight: 600;
    color: #1d1d1f;
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
    color: #6e6e73;
    font-style: italic;
    font-size: 13px;
    margin-right: 4px;
}
/* 例句 */
.example, .eg, .examples {
    color: #424245;
    font-style: italic;
    margin: 4px 0 4px 16px;
    display: block;
}
/* 中文释义块 */
.cn, .chn, .def_cn, .trans {
    color: #1d1d1f;
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
/* 段落 */
p {
    margin: 6px 0;
}
ul, ol {
    margin: 4px 0;
    padding-left: 24px;
}
li {
    margin: 2px 0;
}
/* 折叠块 / 隐藏 oald10.css 外链 */
link[rel="stylesheet"] {
    display: none;
}
</style>
"""


def get_main_qss() -> str:
    """返回主窗口 QSS"""
    return MAIN_QSS


def get_entry_default_css() -> str:
    """返回 EntryView 注入的默认 CSS（HTML 片段形式）"""
    return ENTRY_DEFAULT_CSS
