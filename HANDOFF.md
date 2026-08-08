# HANDOFF - FuncLex Phase 1 交接文档

> 交接时间: 2026-08-08
> 阶段: Phase 1 (MVP 基础框架) - 进行中，约完成 60%

---

## 一、已完成工作

### 1.1 文档 & 规划
| 文件 | 状态 | 说明 |
|------|------|------|
| [ROADMAP.md](file:///Users/fiona/Documents/trae_projects/FuncLex/ROADMAP.md) | ✅ 完成 | 4 阶段开发路线图，含架构设计、技术选型、任务拆解 |
| [README.md](file:///Users/fiona/Documents/trae_projects/FuncLex/README.md) | ✅ 完成 | 安装说明、项目结构、配置说明 |
| [requirements.txt](file:///Users/fiona/Documents/trae_projects/FuncLex/requirements.txt) | ✅ 完成 | PySide6 + readmdict（运行时还需 python-lzo） |

### 1.2 目录结构 & 包初始化
```
funlex/
├── __init__.py           ✅ 版本号 0.1.0
├── core/
│   ├── __init__.py       ✅ 空模块标记
│   └── models.py         ✅ 全部数据类
└── ui/
    └── __init__.py       ✅ 空模块标记
```

### 1.3 核心数据模型 ([models.py](file:///Users/fiona/Documents/trae_projects/FuncLex/funlex/core/models.py))
全部为 `@dataclass`，纯 Python，无依赖：
- `DictionaryInfo` - 词典元信息（name / path / entry_count）
- `DictionaryEntry` - 完整词条（word / raw_content / phonetic / pos_tags / phrasal_verbs / idioms）
- `PhraseItem` - 短语/习语项（phrase / meaning / kind: phrasal_verb \| idiom）
- `HistoryItem` - 查询历史
- `NoteItem` - 用户笔记
- `AppConfig` - 应用配置 + `to_dict()` / `from_dict()` 序列化

### 1.4 技术验证（关键，已跑通）
- ✅ **readmdict API 验证**: 成功加载项目中 6 个 MDX 文件
- ✅ **牛津高阶 第10版**: 310,088 词条，内容为标准 HTML（含 CSS class: `headword` / `pos` / `phon` / `phons_br` 等）
- ✅ **python-lzo**: MDX 解压依赖，已 pip 安装成功
- ✅ **PySide6**: 6.11.0 已安装可用

### 1.5 自动生成的目录
- `data/` - 放 SQLite 数据库（Phase 2 才用）
- `dictionaries/` - 默认词典目录（可选）

---

## 二、未完成工作（Phase 1 剩余）

### 🔴 P1 高优先级（MVP 必须）
| # | 模块 | 文件 | 说明 |
|---|------|------|------|
| 1 | Core | `funlex/core/mdx_parser.py` | 封装 readmdict：加载 MDX → 遍历 (word, content) 对；内容 bytes→utf-8 decode；**不要做过度结构化解析，MVP 只返回 raw HTML** |
| 2 | Core | `funlex/core/dictionary.py` | `DictionaryService` 类：<br>• 扫描 `dictionary_paths`，自动发现项目根目录的 `*.mdx`<br>• 维护 `{dict_name: {word_lower: raw_html}}` 内存索引<br>• 接口：`list_dictionaries()` / `lookup(word, dict_name=None)` / `suggest(prefix)` 前缀匹配（遍历 keys 即可） |
| 3 | UI | `funlex/ui/styles.py` | 写一份现代简洁的 QSS，参考 macOS 风格：浅灰背景 (#f5f5f7)、卡片圆角、蓝色主色 (#007aff)、搜索框圆角 8px |
| 4 | UI | `funlex/ui/search_bar.py` | QLineEdit 封装：placeholder "输入单词搜索..."，回车触发信号 `searchRequested(str)`，右侧可选清除按钮 |
| 5 | UI | `funlex/ui/entry_view.py` | QTextBrowser 子类：<br>• `set_content(html: str, word: str)` 设置 HTML 内容<br>• 对 QTextBrowser 的 `document().setDefaultStyleSheet()` 注入一些基础 CSS（让 `<h1>` `<span class="pos">` 等有默认样式）<br>• **不要过度处理 HTML，直接 setHtml 让 Qt 渲染** |
| 6 | UI | `funlex/ui/main_window.py` | QMainWindow：<br>• 顶部 QVBoxLayout: SearchBar<br>• 中间: EntryView<br>• 底部状态栏: "已加载 X 本词典，共 Y 词条"<br>• 持有 DictionaryService 引用，信号槽连接<br>• 启动时 auto-load 词典，默认选第一个可用的 |
| 7 | 入口 | `app.py` | `QApplication` 启动：<br>• 加载 QSS<br>• 创建 DictionaryService + MainWindow<br>• try/except 包裹，出错弹 QMessageBox |

### 🟡 P2 可选（做了体验更好，但不阻塞 MVP）
- `DictionaryService` 支持大小写不敏感查找
- SearchBar 加简单 suggest（输入 2 字符后在状态栏显示匹配数）
- 窗口最小尺寸 900x600，默认 1100x750

---

## 三、关键实现约定

### 3.1 MDX Parser 接口约定（写 mdx_parser.py 时照着写）
```python
# funlex/core/mdx_parser.py
from typing import Iterator, Tuple, Optional
from .models import DictionaryInfo

class MdxParser:
    def __init__(self, file_path: str): ...
    def get_info(self) -> DictionaryInfo: ...
    def iter_entries(self) -> Iterator[Tuple[str, str]]:
        """yield (word, raw_html_content)，bytes 自动 decode utf-8，失败用 errors='replace'"""
    def get_entry_count(self) -> int: ...
```

### 3.2 DictionaryService 接口约定
```python
# funlex/core/dictionary.py
from typing import List, Optional, Dict, Tuple
from .models import DictionaryInfo, DictionaryEntry
from .mdx_parser import MdxParser
import os, glob

class DictionaryService:
    def __init__(self, paths: Optional[List[str]] = None):
        """paths 为 None 时默认扫描 os.getcwd() 下的 *.mdx"""
    def scan(self) -> List[DictionaryInfo]: ...
    def load_dictionary(self, file_path: str) -> bool: ...
    def list_dictionaries(self) -> List[DictionaryInfo]: ...
    def lookup(self, word: str, dictionary_name: Optional[str] = None) -> Optional[DictionaryEntry]:
        """查不到返回 None；不指定 dict 则用第一个加载的"""
    def suggest(self, prefix: str, limit: int = 20) -> List[Tuple[str, str]]:
        """返回 [(word, dict_name), ...] 前缀匹配"""
```

### 3.3 UI 代码约定
- **所有 UI 文件第一行**: `from PySide6.QtWidgets import ...`
- **禁止 UI 层 import readmdict**，只能调 DictionaryService
- **信号槽优先**，不要回调函数传参
- 颜色值用命名颜色或 hex，不要硬编码在多处，集中在 styles.py 的 QString 里

### 3.4 词典加载路径的约定
MVP 阶段，`DictionaryService()` 不传 paths 时：
1. 扫描 `os.getcwd()/*.mdx`（项目根目录那 6 本）
2. 扫描 `os.path.join(os.getcwd(), "dictionaries")/*.mdx`
3. 全部 load 进内存（6 本加起来约 50 万词条，现代机器内存 OK）

---

## 四、验证 & 验收清单（Phase 1 完成后跑一遍）

- [ ] `pip install -r requirements.txt` 干净环境可装
- [ ] 额外 `pip install python-lzo`（readmdict 运行时需要，requirements 可以补进去）
- [ ] `python app.py` 启动无报错，窗口正常出现
- [ ] 搜索 "take"，能看到 HTML 排版（粗体 headword、音标蓝色、词性标签等）
- [ ] 搜索 "happy" / "love" / "a" 都能出结果
- [ ] 搜索不存在的词 "xyz123"，显示 "未找到该单词" 友好提示
- [ ] 窗口 resize，内容区自适应
- [ ] 回车触发搜索，搜索框清空按钮可用

---

## 五、已知坑 & 注意事项

1. **readmdict 的 key/value 都是 bytes**，必须 `.decode('utf-8', errors='replace')`，部分生僻词 key 可能有编码异常，用 replace 兜底
2. **Collins Cobuild Audio.mdx** 只有发音链接，没有释义，默认词典优先级要排后面（可以在 list_dictionaries 里按 entry_count 倒序排，牛津第10版 31 万条排第一）
3. **QTextBrowser 对 CSS 支持有限**：flex / grid 不行，只能用基础 color / font-size / margin / padding / border-radius。复杂的 MDX 样式可能有偏差，MVP 接受，后续可用 QWebEngineView 替换（但 QWebEngineView 依赖大，MVP 先不用）
4. **MDX content 里有 `<link rel="stylesheet" href="oald10.css">` 这种外链**，QTextBrowser 加载不到，需要在 entry_view.py 注入一段 fallback CSS，对应牛津常见的 class（`.pos`, `.phon`, `.headword`, `.example` 等）
5. **python-lzo 是 C 扩展**，Windows 用户可能需要 VS Build Tools，README 里可以加一句 "Windows 安装报错请先安装 Visual C++ Build Tools 或用 conda install python-lzo"

---

## 六、下一步（Phase 1 完成后的 Phase 2 预告，不用现在做）

- SQLite 索引替代内存 dict（几十万词条启动会变慢）
- 按 POS 拆分 HTML 做 split view
- Settings 对话框 + config.json 读写
- History / Notes 模块
