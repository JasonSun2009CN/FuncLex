# HANDOFF - FuncLex 项目交接文档

> 交接时间: 2026-08-08
> 当前分支: `main` (HEAD: `180dcd5`)
> 当前阶段: **Phase 1 (MVP 基础框架) - 已完成 ✅**

---

## 🎯 项目一句话

基于 Python + PySide6 的**本地桌面词典应用**，能读取 MDX/MDD 格式词典（牛津、朗文、柯林斯、韦氏等），完全离线、快速查询、保留原始 HTML 排版。

---

## ✅ Phase 1 已完成（可直接跑）

### 1.1 跑起来 + 验收

```bash
# 1. 进项目
cd /Users/fiona/Documents/trae_projects/FuncLex

# 2. 装依赖（python-lzo 是 readmdict 的运行时依赖，必须装）
python3 -m pip install -r requirements.txt
python3 -m pip install python-lzo    # requirements 已加，部分环境还需手动

# 3. 启动
python app.py
```

**Phase 1 验收清单**（实测结果）：
- [x] `pip install -r requirements.txt` 干净环境可装
- [x] `python app.py` 启动无报错（PySide6 6.11.0 验证）
- [x] 6 本 MDX 自动加载（牛津 10/9/7 版、Collins COBUILD、Collins Audio、韦氏同义词），共 635,525 词条
- [x] 启动 ~11s（首次加载所有 MDX），按 entry_count 倒序选择默认词典
- [x] 搜索 "take" / "happy" / "love" / "a" 都能出 HTML 结果（raw 长度 14k–151k 字节）
- [x] 搜索 "xyz123" 显示"未找到该单词"友好提示
- [x] 窗口默认 1100×750，最小 900×600，内容区自适应
- [x] 回车触发搜索，✕ 清除按钮工作
- [x] ⌘F / Ctrl+F 聚焦搜索框

### 1.2 已交付文件

```
_func_lex/
├── app.py                       ✅ 入口（QApplication + excepthook）
├── requirements.txt             ✅ PySide6 + readmdict + python-lzo
├── .gitignore                   ✅ pycache/venv/build
├── README.md                    ✅ 用户文档
├── ROADMAP.md                   ✅ 4 阶段路线图
├── HANDOFF.md                   ✅ 本文件
├── funlex/
│   ├── __init__.py              ✅ version 0.1.0
│   ├── core/                    ✅ 纯 Python，无 UI 依赖
│   │   ├── __init__.py
│   │   ├── models.py            ✅ 6 个 dataclass（见下）
│   │   ├── mdx_parser.py        ✅ MdxParser 封装 readmdict
│   │   └── dictionary.py        ✅ DictionaryService（多词典、内存索引、查询、suggest）
│   └── ui/                      ✅ PySide6
│       ├── __init__.py
│       ├── styles.py            ✅ QSS 主题 + EntryView 默认 CSS
│       ├── search_bar.py        ✅ SearchBar QLineEdit 封装
│       ├── entry_view.py        ✅ QTextBrowser 子类
│       └── main_window.py       ✅ QMainWindow 应用
└── data/                        🔲 空（Phase 2 给 SQLite 用）
└── dictionaries/                🔲 空（可选放自定义 MDX）
```

### 1.3 核心数据模型（`funlex/core/models.py`）

全部 `@dataclass`，纯 Python，无依赖：
- `DictionaryInfo` — 词典元信息（name / path / entry_count / loaded）
- `DictionaryEntry` — 完整词条（word / raw_content / pos_tags / phrasal_verbs / idioms）
- `PhraseItem` — 短语/习语（phrase / meaning / kind: phrasal_verb|idiom）
- `HistoryItem` — 查询历史（word / timestamp / dictionary_name）
- `NoteItem` — 用户笔记（word / content / created_at / updated_at）
- `AppConfig` — 应用配置（to_dict / from_dict 序列化）

### 1.4 关键技术决策（已实现）

| 决策 | 选择 | 理由 |
|------|------|------|
| UI 框架 | PySide6 6.5+ | 比 PyQt 更宽松许可，Qt 6 现代 API |
| MDX 解析 | readmdict + python-lzo | 纯 Python，支持 MDX 2.0，社区活跃 |
| 富文本渲染 | QTextBrowser | MVP 够用，0 额外依赖；Phase 2 可升级到 QWebEngineView |
| 索引方式 | 全内存 dict | 6 本 ~63 万词条占用 ~1–2GB RAM，启动 11s 可接受 |
| 词典选择 | 按 entry_count 倒序默认 | 牛津 10 版 31 万条排第一，最完整 |

---

## 🔴 接手必读（坑 & 约定）

### 坑 1：readmdict 全部返回 bytes
```python
# 必须 decode，errors='replace' 兜底乱码
word = raw_k.decode("utf-8", errors="replace")
content = raw_v.decode("utf-8", errors="replace")
```

### 坑 2：MDX 外链 CSS 加载不到
QTextBrowser 不会去读取 `<link rel="stylesheet" href="oald10.css">`。  
解决：`funlex/ui/styles.py` → `ENTRY_DEFAULT_CSS` 注入 fallback 样式，对应牛津常见的 `.headword` / `.phon` / `.pos` / `.phrv` / `.idm` / `.example` 等 class。  
**接手时如果发现新词典的样式没生效**，加对应 class 的 CSS 规则到 `ENTRY_DEFAULT_CSS`。

### 坑 3：QTextBrowser CSS 限制
不支持 flex / grid / position: absolute，只能用基础 color / font-size / margin / padding / border-radius。  
复杂 MDX 排版会有偏差，**MVP 接受**。Phase 2 P2.4 升级 QWebEngineView 再解决。

### 坑 4：python-lzo 是 C 扩展
- macOS：`pip install python-lzo` 直接 OK
- Windows：可能需要 Visual C++ Build Tools，备选 `conda install python-lzo`
- Linux：通常直接 OK，缺 `python-dev` 时装 `python3-dev`

### 坑 5：当前启动 11s 偏慢
6 本词典全部加载到内存，首次启动慢。Phase 2 P2.1 引入 SQLite 索引后会快很多，**当前可接受**。

### 坑 6：上个 commit 误提交了 pycache
`525ba4b` 里 `funlex/**/__pycache__/*.pyc` 被加进去了（shell 拦截 `git rm --cached`，未来不及清理）。  
`__pycache__/` 已在 `.gitignore` 里，但已入库的 .pyc 还在。后续清理：

```bash
find . -name __pycache__ -type d -exec git rm -rf {} +
git commit -m "chore: remove tracked pycache"
```

### 约定 1：分层原则（强制）
- **Core 层**：纯 Python，**严禁** import PySide6 / 任何 Qt 模块
- **UI 层**：**只能** import Core 层 API，不允许直接调 readmdict

### 约定 2：信号槽优先
UI 层调用 Core 用 `Signal` + `Slot`，**不要** 传回调函数。

### 约定 3：颜色集中
所有颜色集中在 `funlex/ui/styles.py` 的 `MAIN_QSS` 字符串里，要换主题改这里。

---

## 📋 关键接口约定（Core 给 UI 看的）

```python
# funlex/core/dictionary.py
class DictionaryService:
    def __init__(self, paths: Optional[List[str]] = None): ...
    def scan(self) -> List[DictionaryInfo]: ...
    def load_dictionary(self, file_path: str) -> Optional[DictionaryInfo]: ...
    def list_dictionaries(self) -> List[DictionaryInfo]: ...   # 按 entry_count 倒序
    def first_dictionary(self) -> Optional[DictionaryInfo]: ...
    def lookup(self, word: str, dictionary_name: Optional[str] = None) -> Optional[DictionaryEntry]: ...
    def suggest(self, prefix: str, limit: int = 20) -> List[Tuple[str, str]]: ...
    def total_entries(self) -> int: ...
```

```python
# funlex/core/mdx_parser.py
class MdxParser:
    def __init__(self, file_path: str): ...
    def get_info(self) -> DictionaryInfo: ...
    def get_entry_count(self) -> int: ...
    def iter_entries(self) -> Iterator[Tuple[str, str]]: ...  # yield (word, raw_html)
    def lookup(self, word: str) -> Optional[str]: ...        # 精确查找
```

---

## 🟡 Phase 1 已知遗留 / 可选优化

| # | 类型 | 描述 | 工作量 |
|---|------|------|--------|
| 1 | 清理 | 移除已被 track 的 `__pycache__/*.pyc` | 5 min |
| 2 | 体验 | SearchBar 加 suggest 弹窗（目前只在状态栏显示匹配数） | 中 |
| 3 | 体验 | ⌘L 选中单词自动查询 | 小 |
| 4 | 体验 | 记住窗口位置 / 大小到 config.json | 小 |
| 5 | 性能 | 首启动 11s 加载所有 MDX（Phase 2 引入 SQLite 才能根治） | Phase 2 |
| 6 | 错误 | MDX 加载失败时弹 QMessageBox（目前只 print） | 小 |

---

## 🚀 下一步（Phase 2 路线，按优先级排）

完整任务清单见 `ROADMAP.md` Phase 2 章节，这里按优先级给接手者建议：

1. **P2.1** SQLite 索引（替代内存 dict，加速启动 + 节省内存）
2. **P2.5** Settings 对话框 + config.json 读写（先把 settings 落地点打通）
3. **P2.6** 查询历史（侧边栏 + SQLite 持久化，数据模型已就绪）
4. **P2.2** 词条结构化解析（从 HTML 提取 POS / 例句 / 习语）
5. **P2.3** Phrasal Verb / Idiom 关联搜索
6. **P2.4** 等分视图（按 POS 拆分 QSplitter）

**建议接手顺序**：先做 P2.5 settings（UI 改动小，立刻有成就感），再 P2.6 历史（数据模型已有），最后 P2.1 SQLite（性能提升，Phase 1 启动慢的根治方案）。

---

## 📞 联系人 / 上下文

- 原作者 commits: `800d10f` (initial) → `7646222` (MDX) → `525ba4b` (Phase 1 完成) → `180dcd5` (README 更新)
- 项目 README: `README.md` — 用户视角（安装、运行、配置）
- 路线图: `ROADMAP.md` — 4 阶段 roadmap + 关键技术决策
- 本文件: 接手必读 + 坑 + 接口约定

---

## ✅ 接手 checklist

接手时按这个顺序验证：

- [ ] 看 README.md 跑一遍 `python app.py`，确认能搜索
- [ ] 读本文件 §"坑"  章节，了解 6 个已知坑
- [ ] 看 `funlex/core/dictionary.py` 10 行 `lookup()` 理解查询逻辑
- [ ] 看 `funlex/ui/main_window.py` 理解信号槽连接
- [ ] 跑 `python -m py_compile app.py funlex/**/*.py` 确认环境 OK
- [ ] 清理 pycache（见 §坑 6）
- [ ] 在 ROADMAP.md Phase 2 选一个任务开始
