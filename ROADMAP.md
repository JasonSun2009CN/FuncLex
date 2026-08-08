# FuncLex 开发路线图

## 项目概述

FuncLex 是一个基于 Python + PySide6 的本地桌面词典应用，支持读取 MDX 格式词典文件，提供现代简洁的 UI，完全离线运行。

## 当前状态

**Phase 1 (MVP 基础框架) 已完成 ✅** — commit `525ba4b`

- 6 本 MDX 实测加载 635,525 词条，启动 ~11s
- 内存索引 + 大小写不敏感查询 + 前缀匹配
- macOS 风格 QSS + 词条 HTML 渲染 + 友好提示
- 完整数据模型 + 接口约定（见 `HANDOFF.md`）

---

## 技术栈

| 类别 | 选型 | 备注 |
|------|------|------|
| 语言 | Python 3.9+ | |
| UI 框架 | PySide6 (Qt 6) | 6.5+ 已验证 6.11.0 |
| MDX 解析 | readmdict | 需 python-lzo 运行时 |
| 索引（Phase 1）| 内存 dict | `{name: {word_lower: html}}` |
| 索引（Phase 2）| SQLite (标准库) | 替代内存，启动加速 |
| 富文本渲染 | QTextBrowser | Phase 2 可升级 QWebEngineView |
| 配置（Phase 2）| JSON 文件 | 标准库 |
| 包管理 | pip / requirements.txt | |

---

## 架构设计

```
FunLex/
├── app.py                    # 应用入口
├── requirements.txt          # 依赖清单
├── config.json               # 用户配置 (Phase 2 自动生成)
├── funlex/
│   ├── core/                 # 核心逻辑层 (无 UI 依赖)
│   │   ├── models.py         # ✅ 数据模型
│   │   ├── mdx_parser.py     # ✅ MDX 解析
│   │   ├── dictionary.py     # ✅ 词典管理 + 查询
│   │   ├── indexer.py        # 🔲 Phase 2 SQLite 索引
│   │   ├── history.py        # 🔲 Phase 2 历史
│   │   └── notes.py          # 🔲 Phase 3 笔记
│   └── ui/                   # UI 层 (PySide6)
│       ├── main_window.py    # ✅ 主窗口
│       ├── search_bar.py     # ✅ 搜索框
│       ├── entry_view.py     # ✅ 词条视图
│       ├── entry_view_split.py  # 🔲 Phase 2 等分视图
│       ├── settings_dialog.py   # 🔲 Phase 2 设置
│       ├── history_panel.py     # 🔲 Phase 2 历史面板
│       ├── notes_editor.py      # 🔲 Phase 3 笔记编辑器
│       └── styles.py         # ✅ QSS + 默认 CSS
├── data/                     # 本地数据 (Phase 2 自动生成 SQLite)
└── dictionaries/             # 默认词典目录
```

---

## Phase 1: MVP 基础框架 ✅ 已完成

### 目标
建立可运行的最小化产品：能加载 MDX、搜索单词、显示词条释义。

### 任务清单
- [x] P1.1 项目目录结构与依赖配置 (`requirements.txt` + `python-lzo`)
- [x] P1.2 数据模型定义 (`models.py`)
- [x] P1.3 MDX 解析模块 (`mdx_parser.py`)
- [x] P1.4 词典管理核心类 (`DictionaryService`)
- [x] P1.5 主窗口 UI 框架 (`main_window.py` + `search_bar.py`)
- [x] P1.6 默认词条视图 (`entry_view.py` + `styles.py` 默认 CSS)
- [x] P1.7 应用入口 (`app.py`)
- [x] P1.8 MVP 联调与基本测试

### 验收标准 (实测)
1. ✅ `pip install -r requirements.txt` 安装成功
2. ✅ `python app.py` 启动无报错
3. ✅ 自动扫描项目根目录 + `dictionaries/` 下的 .mdx，自动加载
4. ✅ 输入单词能搜索并显示原始 HTML 释义
5. ✅ 支持基础 HTML 格式渲染（字体、颜色、列表、表格等）
6. ✅ 大小写不敏感查询 + 词典切换 + 状态栏提示
7. ✅ 未找到词条友好提示

### 已知遗留
- 启动偏慢（11s 加载 6 本，Phase 2 引入 SQLite 解决）
- 已 track 的 `__pycache__/*.pyc` 待清理（HANDOFF §坑 6）
- 复杂 MDX 排版偏差（Phase 2 升级 QWebEngineView）

---

## Phase 2: 核心功能增强 🔲 进行中

### 目标
完善查询体验（SQLite 索引根治启动慢），支持多词性显示 + 两种视图切换 + 历史 + 设置。

### 任务清单（按接手优先级排）

| # | 任务 | 描述 | 优先级 | 依赖 |
|---|------|------|--------|------|
| 1 | P2.5 Settings 对话框 + config.json | 先打通配置入口 | 🔴 P0 | 无 |
| 2 | P2.6 查询历史侧边栏 | 数据模型已有，立刻可做 | 🔴 P0 | 无 |
| 3 | P2.1 SQLite 本地索引 | 替代内存 dict，加速启动 + 节省内存 | 🔴 P0 | 无 |
| 4 | P2.2 词条结构化解析 | 从 HTML 提取 POS / 例句 / 习语 | 🟡 P1 | 无 |
| 5 | P2.3 Phrasal Verb / Idiom 关联搜索 | 基于 P2.2 的解析结果 | 🟡 P1 | P2.2 |
| 6 | P2.4 等分视图 UI | 按 POS 拆分 QSplitter | 🟢 P2 | P2.2 |

### 推荐接手顺序
```
P2.5 (Settings) → P2.6 (历史) → P2.1 (SQLite) → P2.2 (结构化) → P2.3 (习语) → P2.4 (等分视图)
```

### 验收标准
- 启动 < 2s（SQLite 索引预构建）
- 词典路径、默认词典、视图模式可配置
- 历史记录可点击回查
- 至少 1 个词典（牛津 10 版）的 POS / 例句 / 习语能结构化抽取
- 等分视图可切换、能按词性分块

---

## Phase 3: 体验优化 🔲 待启动

### 目标
完善用户笔记功能、搜索补全、UI 主题。

### 任务清单
- [ ] P3.1 用户笔记模块（CRUD + SQLite 持久化）
- [ ] P3.2 笔记编辑器 UI（嵌入词条页）
- [ ] P3.3 搜索自动补全 / 模糊匹配
- [ ] P3.4 历史记录侧边栏 UI（Phase 2 后端已就绪）
- [ ] P3.5 现代 QSS 样式主题（深色 / 浅色切换）
- [ ] P3.6 多词典合并查询
- [ ] P3.7 加载状态与错误提示优化

---

## Phase 4: 发布准备 🔲 待启动

### 任务清单
- [ ] P4.1 全面测试（边界情况、大型词典性能）
- [ ] P4.2 异常处理与日志系统
- [ ] P4.3 macOS 打包（PyInstaller）
- [ ] P4.4 Windows 打包（PyInstaller）
- [ ] P4.5 最终文档完善

---

## 关键设计决策

### 1. MDX 解析库选择
**选型**: `readmdict` (https://github.com/liusheng/readmdict)
- 纯 Python 实现，无需编译
- 支持 MDX (词典数据) 和 MDD (资源文件: 图片/音频)
- 社区活跃，支持最新 MDX 2.0 格式

### 2. 索引策略演进
- **Phase 1** ✅：内存 dict 全量加载，6 本 63 万词条 ~1–2GB RAM / 11s 启动
- **Phase 2**：首次加载词典时遍历所有词条写入 SQLite + FTS5
  - 表设计：`word (TEXT PK), dictionary_id, definition_blob, pos_tags`
  - 索引路径：`~/.funlex/index.db` 或项目内 `data/`
  - 启动 < 2s（只读索引）

### 3. 两种视图切换策略
- **默认视图** ✅：单栏顺序显示所有词性内容，保留原 HTML 排版
- **等分视图**：按词性 (POS) 拆分，使用 QSplitter 等分布局
- 切换通过 `QStackedWidget` 切换两个 View 组件
- 设置存储在 `config.json` 中

### 4. Phrasal Verb / Idiom 识别
- 从 MDX 词条内容中用正则匹配特定 HTML class 或关键词（`<span class="phrv">`, `PHRASAL VERB`, `IDIOM`）
- 建立反向索引：`phrase_word -> [headword1, headword2, ...]`
- 词条页底部显示"相关短语动词 / 习语"区块，可点击跳转

### 5. 配置管理
- 配置文件：`config.json`（项目根目录或 `~/.funlex/config.json`）
- 配置项：
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

### 6. UI 框架选型
- **MVP 选 QTextBrowser**：0 额外依赖，CSS 子集支持足够
- **Phase 2 视情况升级 QWebEngineView**：完整 CSS/JS 支持，但 +100MB 依赖（PySide6-Addons）

---

## 提交历史

```
180dcd5 Update README.md                  (README + 文档)
525ba4b feat: Phase 1 MVP complete        (核心 + UI 全部代码)
7646222 .mdx file being added             (词典文件)
800d10f Initial commit                     (项目骨架)
```
