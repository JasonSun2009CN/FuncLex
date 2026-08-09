# HANDOFF - FuncLex 项目交接文档

> 交接时间: 2026-08-09
> 当前分支: `main`
> 当前阶段: **Phase 1 + Phase 2 已完成 ✅**

---

## 🎯 项目一句话

基于 Python + PySide6 的**本地桌面词典应用**，能读取 MDX/MDD 格式词典（牛津、朗文、柯林斯、韦氏等），完全离线、快速查询、保留原始 HTML 排版，支持多词典合并显示、发音、历史与设置。

---

## ✅ 已完成（可直接跑）

### 1.1 跑起来 + 验收

```bash
cd /Users/fiona/Documents/trae_projects/FuncLex
# 环境：venv 在工作区外 ~/funlex-venv（见 §坑 11：Trae 会隐藏工作区 venv）
~/funlex-venv/bin/python -m pip install -r requirements.txt
~/funlex-venv/bin/python -m pip install python-lzo
~/funlex-venv/bin/python app.py
```

**Phase 2 验收清单**（实测）：
- [x] 二次启动 **<1s**（实测 0.004s，仅 stat + 指纹校验，不打开 MDX）
- [x] 首次运行后台构建索引（进度在状态栏），已构建词典即查即用
- [x] 5 本查询词典共 616,158 词条；Collins Audio 识别为发音资源（不进查询列表）
- [x] `data/index.db` 564MB（zlib 压缩，格式版本标记自动重建）
- [x] 结构化解析：`take` → 音标 /teɪk/、pos [verb, noun]、41 习语、23 短语动词
- [x] `@@@LINK=` 跳转解析（`%` → `per cent`）
- [x] 词条底部"相关短语动词 / 习语"区块，点击跳转查询
- [x] 多词典合并显示（每词典可折叠卡片 + 设置调整顺序 + 折叠偏好持久化；取代原等分视图）
- [x] 设置对话框（词典路径/默认词典/视图/历史条数/字号/字体 → config.json）
- [x] 历史侧边栏（点击回查/右键删除/清空）
- [x] 🔊 发音：检测到 `.mdd` 自动优先真实牛津原声；无则 TTS 合成并**标注"TTS 合成（非牛津原声）"**；⌘P 快捷键；词条内 `sound://` 图标可点击
- [x] 📝 笔记（P3.1/P3.2）：合并视图底部固定"我的笔记"卡片，随查词切换；输入标"未保存"，⌘S/保存落盘，切词自动保存；菜单"所有笔记…"浏览/搜索/删除/回查；**删除笔记均有确认弹窗**（按钮删除 / 清空保存=删除 / 对话框删除）
- [x] 🌓 主题（P3.5）：设置对话框"浅色 / 深色 / 跟随系统"即时生效并持久化；浅色零改动（DARK_QSS 叠加），词条 HTML 双主题 token，system 模式监听 colorSchemeChanged 实时跟随
- [x] 🔍 搜索补全（P3.3）：输入防抖(150ms)弹玻璃下拉（前缀跨词典去重，不足模糊包含补齐）；↑↓/回车/点击选中并回填；Esc 关闭；回车不拦截兼容中文输入法
- [x] 已清理误入库的 `__pycache__/*.pyc`

### 1.2 文件清单

```
_func_lex/
├── app.py                       ✅ 入口（配置加载 + 词典服务 + 主窗口）
├── requirements.txt             ✅ PySide6 + readmdict + python-lzo
├── .gitignore                   ✅ 新增 data/ 与 config.json
├── README.md / ROADMAP.md / HANDOFF.md
├── funlex/
│   ├── __init__.py              version 0.2.0（待 bump）
│   ├── core/                    ✅ 纯 Python，无 UI 依赖
│   │   ├── models.py            ✅ 数据模型（DictionaryEntry 已含 phonetics/pos/phrases；NoteItem）
│   │   ├── mdx_parser.py        ✅ 惰性迭代（不物化内容，修复 Phase1 内存根源）
│   │   ├── indexer.py           ✅ SQLiteIndex（meta/entries/phrases，压缩，跳转解析）
│   │   ├── dictionary.py        ✅ DictionaryService（扫描/分类/查询/发音资源）
│   │   ├── audio.py             ✅ MddAudioIndex（.mdd 音频定向提取）
│   │   ├── parser.py            ✅ EntryParser + extract_phrases + extract_audio_refs
│   │   ├── history.py           ✅ HistoryStore（SQLite）
│   │   ├── notes.py             ✅ NotesStore（P3.1：每词一条笔记，SQLite）
│   │   └── config.py            ✅ ConfigManager（config.json）
│   └── ui/                      ✅ PySide6
│       ├── styles.py            QSS + EntryView 默认 CSS + 主题（浅色/深色 token，DARK_QSS 叠加）
│       ├── search_bar.py        ✅ 搜索框：防抖 + 补全弹窗（SuggestionLineEdit 方向键/Esc，回车走 returnPressed）
│       ├── entry_view.py / main_window.py
│       ├── entry_view_merged.py 多词典合并视图（可折叠卡片 + 底部笔记卡片）
│       ├── notes_card.py        ✅ 笔记编辑卡片（P3.2：输入即脏、⌘S 保存、切词自动保存）
│       ├── notes_dialog.py      ✅ 所有笔记列表对话框（搜索/删除/双击回查）
│       ├── history_panel.py / settings_dialog.py / pronounce.py / build_worker.py
├── data/                        🔲 运行时（index.db / history.db，gitignore）
└── dictionaries/                🔲 可选放自定义 MDX
```

### 1.3 Core 关键接口（新增/变更）

```python
# funlex/core/dictionary.py
class DictionaryService:
    def __init__(self, paths=None, data_dir=None)     # data_dir 默认 ./data
    def scan(self) -> List[DictionaryInfo]            # 快扫：stat + 指纹，不打开 MDX
    def pending_builds(self) -> List[DictionaryInfo]  # 需构建索引的词典
    def build_index(self, name, parser=None, progress_cb=None) -> int
    def list_dictionaries(self)                       # 仅已构建（loaded）词典，entry_count 倒序
    def lookup(self, word, dict_name=None) -> Optional[DictionaryEntry]  # 单词典（兼容保留）
    def lookup_all(self, word) -> List[DictionaryEntry]  # 多词典合并查询（按显示顺序）
    def ordered_dictionaries(self) -> List[DictionaryInfo]  # 合并显示顺序
    def set_dictionary_order(self, names)  # 注入显示顺序
    def suggest(self, prefix, limit=20)
    def related_phrases(self, word, dict_name=None) -> List[PhraseItem]
    def has_audio(self, word) -> bool                 # 发音资源词头（懒加载）
    def find_audio_mdd(self) -> Optional[str]         # 配置路径中找 .mdd（真实发音）
    def total_entries(self) -> int

# funlex/core/audio.py
class MddAudioIndex:
    def __init__(self, mdd_path)                      # readmdict.MDD，按需定向提取
    def has(key) -> bool / get(key) -> Optional[bytes]  # 文件名 key（如 take__gb_1.mp3）
    def has_audio_for(word, variant='') -> bool
    def find(word, variant='') -> Optional[(key, bytes)]  # 英/美音匹配

# funlex/core/parser.py 追加
def extract_audio_refs(html) -> List[(key, variant)]  # sound:// 引用 → (key, gb/us)

# funlex/core/indexer.py
class SQLiteIndex:
    def build(parser, dict_name, progress_cb=None) -> int   # 压缩存储 + phrases 反向索引
    def lookup(word, dict_name) -> Optional[(display, content)]  # 解析 @@@LINK= 链
    def suggest(prefix, dict_name, limit) -> List[str]
    def related_phrases(headword, dict_name) -> List[PhraseItem]
    def is_built(dict_name, file_path) / get_count(dict_name) / mark_audio / is_audio

# funlex/core/history.py
class HistoryStore: add / list(limit) / delete / clear / count / set_limit(limit)

# funlex/core/notes.py（P3.1 新增）
class NotesStore:
    def __init__(self, data_dir)                       # data/notes.db
    def get(word) -> Optional[NoteItem]                # 无则 None
    def save(word, content) -> bool                    # 空内容 = 删除该条，返回 False
    def delete(word)
    def list(limit=500) -> List[NoteItem]              # 按 updated 倒序
    def count() -> int

# funlex/core/parser.py
def parse_entry(word, dict_name, html) -> DictionaryEntry
def extract_phrases(html, headword="") -> List[PhraseItem]

# funlex/core/config.py
class ConfigManager: load() / save() / update(**kwargs)
```

---

## 🔴 接手必读（坑 & 约定）

### 坑 1：readmdict 全部返回 bytes
```python
word = raw_k.decode("utf-8", errors="replace")
content = raw_v.decode("utf-8", errors="replace")
```

### 坑 2：MDX 外链 CSS 加载不到
QTextBrowser 不读 `<link rel="stylesheet">`。`funlex/ui/styles.py` 的 `ENTRY_DEFAULT_CSS` 注入 fallback 样式。新词典样式不生效时，往这里加规则。

### 坑 3：QTextBrowser CSS 限制
不支持 flex/grid/absolute。复杂 MDX 排版有偏差，MVP 接受（Phase 3 可升 QWebEngineView）。

### 坑 4：python-lzo 是 C 扩展
macOS/Linux 直接 pip；Windows 可能要 Visual C++ Build Tools 或 `conda install python-lzo`。

### 坑 5：**索引格式版本（新）**
`SQLiteIndex.FORMAT_VERSION`（现为 "2"，zlib 压缩）。**内容压缩方式变更时必须递增版本**，否则旧库被 `_unpack` 误读。构造时检测版本不符会清空 meta 触发全量重建。

### 坑 6：**SQLite 线程模型（新）**
构建（后台 QThread）与查询（主线程）各自开独立连接（`_connect()`），用 WAL 并发；**不要**跨线程共享同一 connection。

### 坑 7：**词典分类启发式（新）**
`_classify()`：前 30 条里 `>80%` 含 `sound://` 且平均内容 <600B → "发音资源"（不进查询列表，词头集供 `has_audio()`）。命名含 Audio 的词典通常命中。

### 坑 8：**结构化解析以牛津为主**
`parser.py` 的正则按牛津第10版 class（`.pos/.phon/.phons_br/.phons_n_am/.x/.idm/.pvrefs/.xh`）。Collins（`C1_*`、`phrasal_verb_box`）和韦氏（`bword://`）尽力而为；新增词典 class 需扩展正则。`class="x"` 在牛津是例句。

### 坑 9：**真实发音依赖 .mdd（新）**
词条内 `sound://` 是音频引用，真实音频在配套 `.mdd`（如 oald10.mdd）里。`.mdd` 需自行获取（FreeMdict/52pojie 论坛 + 百度网盘）。放项目根或 `dictionaries/` 后 `MddAudioIndex` 自动检测并优先播放原声；无则 TTS 合成，UI 标注"TTS 合成（非牛津原声）"。`MddAudioIndex._extract` 复用 readmdict 记录格式（已验证），按 key 定向提取不载入全量。`.mdd` key 需与 `sound://` 文件名一致（小写、可能带前导 `/`，已归一化处理）。

### 坑 10：GUI 无法在无头环境验证
本环境 `QApplication` 平台插件无法加载（QKeySequence 构造会段错误），UI 只能实机运行验证。Core 层全部可无头测试。

### 坑 11：**Trae 会隐藏工作区 venv（重点）**
macOS + Trae IDE：Trae 会把工作区内 `.venv`/`venv` 的**文件逐批设置 `hidden` BSD 标志**（实测 `.venv` 内 5697 个文件被隐藏）。
Qt 的 QDir 用 `getattrlist` 枚举目录，会**跳过 `hidden` 文件** → 平台插件 `libqcocoa.dylib` 找不到 → 报
`Could not find the Qt platform plugin "cocoa"`，app 崩溃。
- 特征：`os.listdir` 看得到文件、`ls -lO` 显示 `hidden` 标志、`QDir.entryList()` 返回空
- **解法：venv 放在工作区之外**（本项目在 `~/funlex-venv`）。`chflags -R nohidden` 只能临时解决，Trae 会重新隐藏。
- 排查工具：`find venv -flags +hidden | wc -l`、`ls -ldO venv`、`QT_DEBUG_PLUGINS=1 python app.py`

### 坑 12：**深色主题是"叠加"而非"参数化"（新）**

浅色 = `MAIN_QSS` 原样；深色 = 其后追加 `DARK_QSS`（同选择器等优先级后者胜）。**新增控件的浅色样式后，必须同步在 `DARK_QSS` 补一条深色覆盖**，否则深色下该控件保持浅色（反色 bug）。词条 HTML（QTextBrowser 内）走 `ENTRY_CSS_TPL` + 两套 token（`_ENTRY_PALETTES`），新增颜色规则需加 token 并双主题填值。占位/未找到页配色在 `entry_view._state_colors()`。

### 约定 1：分层原则（强制）
Core 层**严禁** import PySide6；UI 层**只能**调 Core 公开 API。

### 约定 2：信号槽优先
UI 调 Core 用 `Signal` + `Slot`，不要传回调。

### 约定 3：颜色集中
颜色集中在 `funlex/ui/styles.py` 的 `MAIN_QSS`，换主题改这里。

### 约定 4：index.db / history.db / config.json 不入库
`.gitignore` 已含 `data/` 与 `config.json`。词典数据文件（`.mdx`）保留入库（已有）。

---

## 🟡 已知遗留 / 可选优化

| # | 类型 | 描述 | 工作量 |
|---|------|------|--------|
| 1 | 体验 | `README 2.md`（项目根，中文版特性草稿，含旧"笔记"设想）待整合/删除；笔记已独立实现，README 2.md 中相关段落可删 | 小 |
| 2 | 解析 | 多词典 class 全覆盖（Collins/韦氏结构化） | 中 |
| 3 | 发音 | 已支持 `.mdd` 真实音频（需用户自行获取 .mdd 放入词典目录）；可做"无 .mdd 时的发音设置开关" | 小 |
| 4 | 性能 | 首构建约 1 分钟（一次性）；可加"仅构建常用词典"选项 | 中 |
| 5 | 体验 | 补全建议按字典序较原始；可做常用词优先/词频排序（现为 PK 字典序） | 中 |
| 6 | 功能 | `related_phrases()` 已暴露，UI 暂用 entry 字段（parse 结果），可直接切换 | 小 |
| 7 | 笔记 | 未收录单词（词典查不到）暂无法记笔记；可扩展"未命中也显示笔记卡片" | 小 |

---

## 🚀 下一步（Phase 3 路线）

完整清单见 `ROADMAP.md`。建议顺序：
1. ~~P3.1/P3.2 笔记~~ ✅ 已完成（NotesStore + 笔记卡片 + 所有笔记对话框 + 删除确认）
2. ~~P3.5 深色主题~~ ✅ 已完成（DARK_QSS 叠加 + 词条 HTML token + 设置切换/跟随系统）
3. ~~P3.3 搜索自动补全/模糊~~ ✅ 已完成（防抖 + 补全弹窗 + 前缀/模糊建议）
4. ~~P3.6 多词典合并查询~~ ✅ 已完成（见 Phase 2 交付）
5. **P3.4 历史侧边栏 UI 增强**（分组、搜索）

---

## 📞 联系人 / 上下文

- 项目 README: `README.md` — 用户视角
- 路线图: `ROADMAP.md` — 4 阶段 roadmap + 关键决策
- 本文件: 接手必读 + 坑 + 接口约定

---

## ✅ 接手 checklist

- [ ] `python app.py` 跑一遍：搜索 `take`，看默认视图 + 🔊 发音
- [ ] 查词 `take` 看多词典合并显示，点击词典标题折叠/展开
- [ ] 设置里改字号/默认词典，确认 config.json 生成
- [ ] 查几个词后开历史侧边栏，点击回查
- [ ] 读本文件 §"坑" 10 条
- [ ] `python -m py_compile app.py funlex/**/*.py` 确认环境 OK
- [ ] 在 ROADMAP.md Phase 3 选一个任务开始
