# FuncLex

基于 Python + PySide6 的**本地桌面词典应用**，支持 MDX 格式词典（牛津、朗文、柯林斯、韦氏等），完全离线运行，保留原始 HTML 排版与音标。

---

## ✨ 功能特性

- 📚 **MDX 格式支持**: 直接读取主流 MDX 词典文件
- 🚀 **秒开启动**: SQLite 索引（`data/index.db`），二次启动 <1s，告别首版 11s 加载
- 🔍 **快速查询**: 前缀补全 + 大小写不敏感查找 + `@@@LINK=` 跳转自动解析
- 📖 **丰富排版**: 保留原始 HTML/CSS 格式（音标、词性、释义、例句）
- 🔤 **结构化解析**: 自动抽取音标（英/美）、词性、例句
- 🎯 **短语 & 习语**: 词条底部显示"相关短语动词 / 习语"，点击可跳转查询
- 🎨 **Liquid Glass 主题**: Minimalism 2.0 风格——半透明玻璃面板、柔和渐变背景、系统蓝点缀；**浅色 / 深色 / 跟随系统**可在设置中切换并即时生效
- 📚 **多词典合并显示**: 查词时**同时显示所有词典**释义，每本词典一张**可折叠卡片**（折叠偏好自动沿用），顺序在设置中调整
- 🔊 **发音功能**: 一键朗读当前词 + 词条内发音图标可点击
  - 检测到配套 `.mdd` 音频资源时**自动优先播放真实原声**（英/美音，如牛津 `sound://`）
  - 无 `.mdd` 时回退系统 **TTS 合成**，并在软件中**明确标注"TTS 合成（非牛津原声）"**
  - 支持 ⌘P 快捷键
- 🕒 **查询历史**: 自动记录 + 右侧栏点击回查 + 一键清空
- 📝 **用户笔记**: 每个单词底部"我的笔记"卡片，输入即标未保存，⌘S / 保存按钮落盘，切词自动保存；菜单"所有笔记…"浏览/搜索/删除/回查
- ⚙️ **可配置**: 词典路径 / **词典显示顺序** / 主题 / 历史条数 / 字号 / 字体（`config.json`）
- 🔒 **完全本地**: 词典文件、索引、历史、配置全部存储在本地，不上传任何数据

---

## 🚀 快速开始

### 环境要求

- Python 3.9 或更高版本
- macOS / Windows / Linux

### 安装步骤

> ⚠️ **macOS + Trae IDE 注意**：Trae 会把工作区内的 venv 目录/文件设置成 `hidden` 标志，导致 Qt 无法枚举平台插件而启动失败（报 `Could not find the Qt platform plugin "cocoa"`）。
> 因此**虚拟环境放在工作区之外**（本项目已就绪于 `~/funlex-venv`）。

```bash
# 1. 克隆 / 进入项目
cd FuncLex

# 2. (推荐) 在工作区外创建虚拟环境（避免 Trae 隐藏干扰）
python3 -m venv ~/funlex-venv
source ~/funlex-venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt
pip install python-lzo           # readmdict 运行时依赖，部分环境需手动

# Windows 用户若 python-lzo 安装失败：
#   conda install python-lzo
#   或安装 Visual C++ Build Tools 后再 pip install
```

### 运行

```bash
cd FuncLex
~/funlex-venv/bin/python app.py
# 或 source ~/funlex-venv/bin/activate 后 python app.py
```

应用启动后会**自动扫描**以下目录的所有 `.mdx` 文件并建立索引：
- 当前工作目录（项目根目录）
- `./dictionaries/`（可选，也可在"设置"中添加更多路径）

**首次运行**会在后台构建 SQLite 索引（状态栏显示进度，构建完成后词典即可查询，全程不阻塞 UI）。**之后的启动 <1s**。

> 查词时**同时显示所有词典**的释义（默认按词条数倒序），各词典的显示顺序可在"设置 → 词典显示顺序"中调整。

### 🎙️ 关于真实发音音频（.mdd）

牛津第10版等词条内置 `sound://` 发音引用，真实音频需配套的 `.mdd` 资源文件。
将 `.mdd` 放到词典目录（项目根或 `dictionaries/`）后，应用**自动检测并优先播放原声**；没有则用 TTS 合成并标注。

`.mdd` 资源常见来源（需自行下载，均为论坛分享，请自辨可用性）：
- FreeMdict 论坛《牛津高阶双解第10版完美版》（例句离线发音包）
- FreeMdict 论坛《牛津高阶 OALD 2024.09 英汉双解 Final》（单词发音包）
- 52pojie 论坛相关资源帖（百度网盘分享）

---

## 📁 项目结构

```
FuncLex/
├── app.py                       # 应用入口
├── requirements.txt             # Python 依赖
├── config.json                  # 用户配置（首次运行时生成，自动 gitignore）
├── README.md                    # 用户文档
├── ROADMAP.md                   # 4 阶段开发路线图
├── HANDOFF.md                   # 开发者交接文档（接手必读）
├── funlex/
│   ├── __init__.py              # version 0.2.0
│   ├── core/                    # 核心逻辑层（纯 Python，无 UI 依赖）
│   │   ├── models.py            # 数据模型
│   │   ├── mdx_parser.py        # MDX 文件解析（惰性迭代，不物化内容）
│   │   ├── indexer.py           # SQLite 索引（构建/查询/跳转解析/短语反向索引）
│   │   ├── dictionary.py        # 词典服务（扫描/分类/查询/发音资源）
│   │   ├── parser.py            # 词条 HTML 结构化解析（音标/词性/例句/习语）
│   │   ├── history.py           # 查询历史（SQLite 持久化）
│   │   └── config.py            # config.json 读写
│   └── ui/                      # UI 层（PySide6）
│       ├── styles.py            # QSS 主题 + EntryView 默认 CSS
│       ├── search_bar.py        # 搜索框组件
│       ├── entry_view.py        # 词条显示区（占位/加载/未找到）
│       ├── entry_view_merged.py # 多词典合并视图（可折叠词典卡片）
│       ├── history_panel.py     # 历史侧边栏
│       ├── settings_dialog.py   # 设置对话框
│       ├── pronounce.py         # 发音助手（QTextToSpeech）
│       ├── build_worker.py      # 后台索引构建线程
│       └── main_window.py       # 主窗口
├── data/                        # 运行时数据（SQLite 索引 / 历史，自动 gitignore）
└── dictionaries/                # 默认词典目录（可选）
```

### 分层原则

- **Core 层**: 纯 Python 实现，**不依赖 PySide6**。可独立测试、可替换 UI。
- **UI 层**: 仅调用 Core 层公开 API，通过信号槽异步通信。

---

## ⌨️ 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Enter` | 搜索当前输入 |
| `⌘F` / `Ctrl+F` | 聚焦搜索框 |
| `⌘P` / `Ctrl+P` | 朗读当前词 |
| `⌘,` | 打开设置 |
| `⌘S`（笔记编辑时） | 保存当前笔记 |
| `✕` 按钮 | 清除搜索内容 |

---

## 🧪 已验证（Phase 2）

实测环境（macOS / Python 3.11）：

**启动性能**
- 二次启动（索引已构建）：**<1s**（仅扫描文件指纹，不打开 MDX）
- 首次构建索引：5 本词典共 **616,158 词条，~1 分钟**，后台进度显示
- 索引体积：`data/index.db` 约 **564MB**（内容 zlib 压缩，较未压缩 1.3GB 减半以上）

**查询与解析（牛津第10版）**
- `take` → 音标 `/teɪk/`、词性 `verb/noun`、例句、41 个习语、23 个短语动词全部抽取
- `@@@LINK=` 跳转解析：`%` → `per cent`
- 相关短语底部区块 + 点击跳转查询

**发音**
- 🔊 按钮朗读当前词（QTextToSpeech 离线可用）
- Collins Cobuild Audio.mdx 识别为"发音资源"（33,796 个原声词头，有原声标识）；其 `sound://` 引用需配套 `.mdd` 才可播放，暂以 TTS 覆盖

完整接口约定与已知坑见 `HANDOFF.md`，4 阶段路线图见 `ROADMAP.md`。

---

## 🛠️ 开发计划

详细开发计划请参考 [ROADMAP.md](./ROADMAP.md)。

当前状态：**Phase 1 + Phase 2 已完成 ✅**，下一步进入 Phase 3（笔记、搜索补全、主题切换）。

---

## 📄 许可证

详见 [LICENSE](./LICENSE) 文件。

## 🤝 致谢

- [readmdict](https://github.com/liusheng/readmdict) — MDX/MDD 解析库
- PySide6 / Qt 团队 — 优秀的跨平台 UI 框架
