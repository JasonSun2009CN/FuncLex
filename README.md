# FuncLex

基于 Python + PySide6 的**本地桌面词典应用**，支持 MDX 格式词典（牛津、朗文、柯林斯、韦氏等），完全离线运行，保留原始 HTML 排版与音标。

---

## ✨ 功能特性

- 📚 **MDX 格式支持**: 直接读取主流 MDX 词典文件
- 🔍 **快速查询**: 内存索引 + 大小写不敏感查找
- 📖 **丰富排版**: 保留原始 HTML/CSS 格式（音标、词性、释义、例句）
- 🎯 **多词典切换**: 自动扫描目录下所有 MDX，按词条数排序默认
- 🎨 **现代 UI**: macOS 风格（浅灰背景、蓝色主色、圆角搜索框）
- 🔒 **完全本地**: 词典文件和数据全部存储在本地，不上传任何数据

---

## 🚀 快速开始

### 环境要求

- Python 3.9 或更高版本
- macOS / Windows / Linux

### 安装步骤

```bash
# 1. 克隆 / 进入项目
cd FuncLex

# 2. (推荐) 创建虚拟环境
python3 -m venv venv
source venv/bin/activate          # macOS/Linux
# venv\Scripts\activate           # Windows

# 3. 安装依赖
pip install -r requirements.txt
pip install python-lzo           # readmdict 运行时依赖，部分环境需手动

# Windows 用户若 python-lzo 安装失败：
#   conda install python-lzo
#   或安装 Visual C++ Build Tools 后再 pip install
```

### 运行

```bash
python app.py
```

应用启动后会**自动扫描**以下目录的所有 `.mdx` 文件并加载到内存：
- 当前工作目录（项目根目录）
- `./dictionaries/`（可选）

启动时默认选中词条数最多的词典（通常是牛津第10版）。

---

## 📁 项目结构

```
FuncLex/
├── app.py                       # 应用入口
├── requirements.txt             # Python 依赖
├── README.md                    # 用户文档
├── ROADMAP.md                   # 4 阶段开发路线图
├── HANDOFF.md                   # 开发者交接文档（接手必读）
├── .gitignore
├── funlex/
│   ├── __init__.py              # version 0.1.0
│   ├── core/                    # 核心逻辑层（纯 Python，无 UI 依赖）
│   │   ├── models.py            # 数据模型
│   │   ├── mdx_parser.py        # MDX 文件解析
│   │   └── dictionary.py        # 词典管理 / 查询
│   └── ui/                      # UI 层（PySide6）
│       ├── styles.py            # QSS 主题 + EntryView 默认 CSS
│       ├── search_bar.py        # 搜索框组件
│       ├── entry_view.py        # 词条显示区
│       └── main_window.py       # 主窗口
├── data/                        # 本地数据（Phase 2 SQLite 索引）
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
| `✕` 按钮 | 清除搜索内容 |

---

## 🧪 已验证（Phase 1 MVP 验收）

实测环境（macOS / Python 3.11）：
- 6 本 MDX 自动加载：**635,525 词条**，启动 ~11 秒
- 词典排序（entry_count 倒序）：
  1. 牛津高阶英汉双解词典 第10版（310,088 词条）
  2. 牛津高阶 英汉双解词典 第9版（205,027 词条）
  3. 牛津高阶英汉双解词典 第7版（42,481 词条）
  4. Collins COBUILD (CN)（34,414 词条）
  5. Collins Cobuild Audio（33,796 词条）
  6. 韦氏同义词辞典（24,148 词条）
- 查询测试: `take` / `happy` / `love` / `a` 全部命中，HTML 长度 14k–151k 字节
- `xyz123` 不存在词返回友好提示
- 窗口默认 1100×750，最小 900×600，内容区自适应

完整接口约定与已知坑见 `HANDOFF.md`，4 阶段路线图见 `ROADMAP.md`。

---

## 🛠️ 开发计划

详细开发计划请参考 [ROADMAP.md](./ROADMAP.md)。

当前状态：**Phase 1 (MVP) 已完成 ✅**，下一步进入 Phase 2（SQLite 索引 + Settings + 历史记录）。

---

## 📄 许可证

详见 [LICENSE](./LICENSE) 文件。

## 🤝 致谢

- [readmdict](https://github.com/liusheng/readmdict) — MDX/MDD 解析库
- PySide6 / Qt 团队 — 优秀的跨平台 UI 框架
