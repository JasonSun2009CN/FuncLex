# FuncLex 开发路线图

## 项目概述

FuncLex 是一个基于 Python + PySide6 的本地桌面词典应用，支持读取 MDX 格式词典文件，提供现代简洁的 UI，完全离线运行。

## 当前状态

**Phase 1 (MVP 基础框架) 已完成 ✅** — commit `525ba4b`
**Phase 2 (核心功能增强) 已完成 ✅** — commit 待定

- 5 本真实词典 + 1 个发音资源，共 616,158 词条
- SQLite 索引 + zlib 压缩，**二次启动 <1s**，内存占用大幅下降
- 设置 / 历史 / 结构化解析 / 习语关联 / **多词典合并显示** / 发音 全部落地

***

## 技术栈

| 类别     | 选型                     | 备注                            |
| ------ | ---------------------- | ----------------------------- |
| 语言     | Python 3.9+            | <br />                        |
| UI 框架  | PySide6 (Qt 6)         | 6.5+ 已验证 6.11.1               |
| MDX 解析 | readmdict              | 需 python-lzo 运行时              |
| 索引     | SQLite (标准库) + zlib    | `data/index.db`，内容压缩存储        |
| 富文本渲染  | QTextBrowser           | 合并视图每词典一个 QTextBrowser        |
| 发音     | QTextToSpeech          | 系统离线 TTS；QtMultimedia 备接 .mdd |
| 配置     | `config.json`          | 项目根目录，标准库                     |
| 历史     | SQLite                 | `data/history.db`             |
| 包管理    | pip / requirements.txt | <br />                        |

***

## 架构设计

```
FunLex/
├── app.py                    # 应用入口
├── requirements.txt          # 依赖清单
├── config.json               # 用户配置（自动生成，gitignore）
├── funlex/
│   ├── core/                 # 核心逻辑层 (无 UI 依赖)
│   │   ├── models.py         # ✅ 数据模型
│   │   ├── mdx_parser.py     # ✅ MDX 解析（惰性迭代）
│   │   ├── dictionary.py     # ✅ 词典服务（扫描/分类/查询/发音资源）
│   │   ├── indexer.py        # ✅ SQLite 索引 + 短语反向索引
│   │   ├── parser.py         # ✅ 词条结构化解析
│   │   ├── history.py        # ✅ 查询历史
│   │   └── config.py         # ✅ config.json 读写
│   └── ui/                   # UI 层 (PySide6)
│       ├── main_window.py    # ✅ 主窗口
│       ├── search_bar.py     # ✅ 搜索框
│       ├── entry_view.py     # ✅ 词条视图（默认）
│       ├── entry_view_merged.py # ✅ 多词典合并视图（可折叠卡片）
│       ├── settings_dialog.py   # ✅ 设置
│       ├── history_panel.py     # ✅ 历史面板
│       ├── pronounce.py         # ✅ 发音助手
│       ├── build_worker.py      # ✅ 后台索引构建
│       └── styles.py         # ✅ QSS + 默认 CSS
├── data/                     # 运行时数据（SQLite 索引/历史，gitignore）
└── dictionaries/             # 默认词典目录
```

***

## Phase 1: MVP 基础框架 ✅ 已完成

- [x] P1.1 项目目录结构与依赖配置
- [x] P1.2 数据模型定义 (`models.py`)
- [x] P1.3 MDX 解析模块 (`mdx_parser.py`)
- [x] P1.4 词典管理核心类 (`DictionaryService`)
- [x] P1.5 主窗口 UI 框架
- [x] P1.6 默认词条视图
- [x] P1.7 应用入口 (`app.py`)
- [x] P1.8 MVP 联调与基本测试

***

## Phase 2: 核心功能增强 ✅ 已完成

### 目标

根治启动慢（SQLite 索引）、补齐设置/历史/结构化解析/习语关联/多词典合并显示，并新增发音功能。

### 任务清单

- [x] P2.1 SQLite 本地索引（替代内存 dict，二次启动 <1s）
  - `data/index.db`：`entries` 表 PK(dict, word) WITHOUT ROWID，zlib 压缩内容
  - 指纹（size+mtime）免重建；`@@@LINK=` 跳转解析（深度≤6）
- [x] P2.2 词条结构化解析（`parser.py`，正则抽取牛津类语义 class）
  - 音标（英/美 `.phons_br`/`.phons_n_am`）、词性 `.pos`、例句 `.x`、习语 `.idm`、短语 `.pvrefs/.xh`
- [x] P2.3 Phrasal Verb / Idiom 关联搜索
  - 构建期写入 `phrases` 反向索引表；词条底部"相关短语动词 / 习语"区块，点击跳转查询
- [x] P2.4 等分视图 UI（`entry_view_split.py`）→ **已移除**，被 P3.6 多词典合并显示取代
  （合并显示每词典一张可折叠卡片，按词性分块不再必要）
- [x] P2.5 Settings 对话框 + config.json（`config.py` + `settings_dialog.py`）
  - 词典路径 / 默认词典 / 视图模式 / 历史条数 / 字号 / 字体
- [x] P2.6 查询历史侧边栏（`history.py` + `history_panel.py`）
  - SQLite 持久化、去重置顶、点击回查、右键删除、一键清空、超限裁剪
- [x] P2.7 发音功能（`pronounce.py`，用户新增需求）
  - 🔊 按钮 + ⌘P 朗读当前词（QTextToSpeech 离线）
  - Collins Cobuild Audio.mdx 内容启发式识别为"发音资源"（不进查询列表），`has_audio()` 标记原声词头

### 验收标准（实测）

1. ✅ 启动 < 2s（实测二次启动 <1s，仅 stat + 指纹校验）
2. ✅ 词典路径、默认词典、视图模式可配置（config.json + 设置对话框）
3. ✅ 历史记录可点击回查
4. ✅ 牛津第10版 POS / 例句 / 习语 / 短语动词能结构化抽取
5. ✅ 多词典合并显示：查词同时显示所有词典，可折叠，顺序可在设置调整
6. ✅ 发音按钮可朗读；audio 词典正确分类为发音资源

### 遗留

- 结构化解析主要针对牛津系 class（Collins/韦氏尽力而为）；多词典 class 全覆盖留待 Phase 3
- 真实发音需配套 `.mdd` 音频资源（无则 TTS 合成并标注）；`.mdd` 需自行从论坛/网盘获取
- 启动后首次构建索引约 1 分钟（一次性）

***

## Phase 3: 体验优化 🔲 待启动

### 目标

完善用户笔记功能、搜索补全、UI 主题。

### 任务清单

- [x] P3.1 用户笔记模块（CRUD + SQLite 持久化）
- [x] P3.2 笔记编辑器 UI（嵌入词条页）
  - 合并视图底部固定"我的笔记"卡片，随查词切换；输入即标记未保存，⌘S / 保存按钮落盘
  - 切词自动保存未提交改动；"所有笔记…"对话框（菜单入口）浏览/搜索/删除/回查
- [ ] P3.3 搜索自动补全 / 模糊匹配
- [ ] P3.4 历史记录侧边栏 UI 增强
- [ ] P3.5 现代 QSS 样式主题（深色 / 浅色切换）
- [x] P3.6 多词典合并查询（每词典可折叠卡片 + 设置中调整顺序 + 折叠偏好持久化）
- [ ] P3.7 加载状态与错误提示优化
- [ ] P3.8 复杂 MDX 排版升级 QWebEngineView

***

## Phase 4: 发布准备 🔲 待启动

- [ ] P4.1 全面测试（边界情况、大型词典性能）
- [ ] P4.2 异常处理与日志系统
- [ ] P4.3 macOS 打包（PyInstaller）
- [ ] P4.4 Windows 打包（PyInstaller）
- [ ] P4.5 最终文档完善

***

## 关键设计决策

### 1. MDX 解析库选择

**选型**: `readmdict`（纯 Python，支持 MDX 2.0，社区活跃）。

### 2. 索引策略

- **Phase 1** ✅：内存 dict 全量加载（启动 11s、1–2GB RAM）→ 已弃用
- **Phase 2** ✅：SQLite `data/index.db`，构建一次、终身读取
  - `entries(dict, word, display, content)` PK(dict,word) WITHOUT ROWID，前缀查询走 PK 范围扫描
  - 内容 zlib 压缩（`FORMAT_VERSION` 标记，格式变更自动重建）
  - 指纹（size+mtime）存 meta 表，MDX 未变更不重建
  - 构建在后台线程，进度显示于状态栏，已构建词典即查即用

### 3. 多词典合并显示（取代等分视图）

- 查词时 `lookup_all()` 返回所有命中词典词条，按显示顺序堆叠
- 每本词典一张可折叠玻璃卡片（`entry_view_merged.py`），折叠偏好存 `config.collapsed_dictionaries`
- 显示顺序存 `config.dictionary_order`，设置中上移/下移调整
- 相关短语/习语聚合去重后显示在底部一张卡片

### 4. Phrasal Verb / Idiom 关联

- 构建期 `extract_phrases()` 从 `.idm/.phrv/.pvrefs/.xh` 抽取，写入 `phrases(phrase, headword, dict, kind)`
- 词条页底部渲染相关短语，点击以短语为词头重新查询

### 5. 发音功能

- **真实音频优先**：`core/audio.py` 的 `MddAudioIndex` 定向提取 `.mdd` 音频字节（同 readmdict 记录格式，已在 mdx 验证）；检测到 `.mdd` 时自动优先播放牛津原声（英/美音，`sound://` 与 🔊 按钮均可）
- **TTS 回退 + 标注**：无 `.mdd` 时回退系统 TTS（QTextToSpeech，macOS/Windows/Linux 原生），并在 UI 明确标注"TTS 合成（非牛津原声）"（悬浮提示 + 状态栏）
- **英/美音选择**：TTS 自动选 en_GB/en_US 声音；真实音频按 `__gb_`/`__us_` 变体匹配
- Collins Audio.mdx 内容启发式分类（`>80% sound://` 且平均 <600B）为发音资源，词头集供 `has_audio()`

### 6. 配置管理

- `config.json`（项目根），`ConfigManager` 读写，字段校验兜底

### 7. UI 框架

- QTextBrowser（0 额外依赖）；复杂排版可升级 QWebEngineView（Phase 3 可选）

### 8. 用户笔记

- Core `NotesStore`（`data/notes.db`）：每词一条，`word` 小写主键，空内容保存=删除该条；RLock 线程安全，与 HistoryStore 同风格
- UI：合并视图底部固定笔记卡片（输入即标记未保存、⌘S/按钮保存、切词自动保存、可删除）；"所有笔记"对话框浏览/搜索/删除/双击回查

***

## 提交历史

```
ba61595 docs: refresh README/ROADMAP/HANDOFF for Phase 1 complete + handoff
525ba4b feat: Phase 1 MVP complete
7646222 .mdx file being added
800d10f Initial commit
```

