# FuncLex 开发路线图

## 项目概述
FuncLex 是一个基于 Python + PySide6 的本地桌面词典应用，支持读取 MDX 格式词典文件，提供现代简洁的 UI，完全离线运行。

## 技术栈
- **语言**: Python 3.9+
- **UI 框架**: PySide6 (Qt 6)
- **MDX 解析**: readmdict (纯 Python MDX/MDD 解析库)
- **本地索引**: SQLite (标准库 sqlite3)
- **富文本渲染**: QTextBrowser (支持 HTML/CSS)
- **配置管理**: JSON 配置文件
- **包管理**: pip / requirements.txt

## 架构设计

```
FunLex/
├── app.py                    # 应用入口
├── requirements.txt          # 依赖清单
├── config.json               # 用户配置 (自动生成)
├── data/
│   └── funlex.db             # SQLite 索引数据库 (自动生成)
├── funlex/
│   ├── __init__.py
│   ├── core/                 # 核心逻辑层 (与 UI 完全解耦)
│   │   ├── __init__.py
│   │   ├── models.py         # 数据模型定义
│   │   ├── mdx_parser.py     # MDX 文件解析
│   │   ├── dictionary.py     # 词典管理、查询逻辑
│   │   ├── indexer.py        # SQLite 索引构建与查询
│   │   ├── history.py        # 查询历史管理
│   │   └── notes.py          # 用户笔记管理
│   └── ui/                   # UI 层 (仅依赖 core 层)
│       ├── __init__.py
│       ├── main_window.py    # 主窗口
│       ├── search_bar.py     # 搜索框组件
│       ├── entry_view.py     # 词条显示区 (默认视图)
│       ├── entry_view_split.py  # 词条显示区 (等分视图)
│       ├── history_panel.py  # 历史记录面板
│       ├── notes_editor.py   # 笔记编辑器
│       ├── settings_dialog.py # 设置对话框
│       └── styles.py         # QSS 样式
└── dictionaries/             # 默认词典目录 (用户可配置)
    └── (放置 .mdx 文件)
```

### 分层原则
- **Core 层**: 纯 Python，不依赖 PySide6/Qt。负责所有业务逻辑：MDX 解析、搜索、索引、历史、笔记。
- **UI 层**: 仅依赖 Core 层的公开 API，通过信号槽与 Core 交互。负责渲染和用户交互。

---

## Phase 1: MVP 基础框架 (当前阶段)

### 目标
建立可运行的最小化产品：能加载 MDX、搜索单词、显示词条释义。

### 任务清单
- [x] P1.1 项目目录结构与依赖配置 (requirements.txt)
- [x] P1.2 数据模型定义 (Entry, DictionaryInfo, etc.)
- [x] P1.3 MDX 解析模块 (基于 readmdict 库)
- [ ] P1.4 词典管理核心类 (DictionaryService)
- [ ] P1.5 主窗口 UI 框架 (搜索框 + 显示区)
- [ ] P1.6 默认词条视图 (支持 HTML/CSS 渲染)
- [ ] P1.7 应用入口 (app.py)
- [ ] P1.8 MVP 联调与基本测试

### Phase 1 验收标准
1. `pip install -r requirements.txt` 安装依赖成功
2. `python app.py` 启动应用无报错
3. 能自动扫描项目根目录下的 .mdx 文件并加载
4. 输入单词能搜索并显示基本释义
5. 支持基本的 HTML 格式渲染 (字体、颜色、列表等)

---

## Phase 2: 核心功能增强

### 目标
完善查询体验，支持多词性显示与两种视图切换。

### 任务清单
- [ ] P2.1 SQLite 本地索引构建 (加速大型词典查询)
- [ ] P2.2 词条结构化解析 (提取音标、词性、释义、例句)
- [ ] P2.3 Phrasal Verb / Idiom 识别与关联搜索
- [ ] P2.4 等分视图 UI 实现 (每个词性一个区域)
- [ ] P2.5 设置对话框 (视图切换、词典路径配置)
- [ ] P2.6 查询历史记录 (增删查、持久化)

---

## Phase 3: 体验优化

### 目标
完善用户笔记功能，打磨 UI 细节。

### 任务清单
- [ ] P3.1 用户笔记模块 (CRUD + SQLite 持久化)
- [ ] P3.2 笔记编辑器 UI (嵌入词条页)
- [ ] P3.3 搜索自动补全 / 模糊匹配
- [ ] P3.4 历史记录侧边栏 UI
- [ ] P3.5 现代 QSS 样式主题 (浅色/深色)
- [ ] P3.6 多词典切换 / 合并查询
- [ ] P3.7 加载状态与错误提示优化

---

## Phase 4: 发布准备

### 任务清单
- [ ] P4.1 全面测试 (边界情况、大型词典性能)
- [ ] P4.2 异常处理与日志系统
- [ ] P4.3 macOS 打包 (PyInstaller)
- [ ] P4.4 Windows 打包 (PyInstaller)
- [ ] P4.5 最终文档完善

---

## 关键设计决策

### 1. MDX 解析库选择
**选型**: `readmdict` (https://github.com/liusheng/readmdict)
- 纯 Python 实现，无需编译
- 支持 MDX (词典数据) 和 MDD (资源文件: 图片/音频)
- 社区活跃，支持最新 MDX 2.0 格式

### 2. 索引策略
- 首次加载词典时，遍历所有词条写入 SQLite
- 索引表: `word (TEXT PK), dictionary_id, definition_blob, pos_tags`
- 搜索走 SQLite LIKE + FTS5 (如启用)
- 索引文件路径可配置，默认 `~/.funlex/index.db` 或项目内 `data/`

### 3. 两种视图切换策略
- **默认视图**: 单栏顺序显示所有词性内容，保留原 HTML 排版
- **等分视图**: 按词性 (POS) 拆分，使用 QSplitter 或 QHBoxLayout 等分布局
- 切换通过 `QStackedWidget` 切换两个 View 组件
- 设置存储在 `config.json` 中

### 4. Phrasal Verb / Idiom 识别
- 从 MDX 词条内容中用正则匹配特定 HTML class 或关键词 (如 `<span class="phrv">`, `PHRASAL VERB`, `IDIOM`)
- 建立反向索引: `phrase_word -> [headword1, headword2, ...]`
- 词条页底部显示 "相关短语动词" / "相关习语" 区块，可点击跳转

### 5. 配置管理
- 配置文件: `config.json` (项目根目录或 `~/.funlex/config.json`)
- 配置项:
  ```json
  {
    "dictionary_paths": ["dictionaries/", "/path/to/custom.mdx"],
    "default_dictionary": "牛津高阶英汉双解词典 第10版.mdx",
    "view_mode": "default",
    "theme": "light",
    "history_limit": 100,
    "font_family": "PingFang SC",
    "font_size": 14
  }
  ```
