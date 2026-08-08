# FuncLex

一个基于 Python + PySide6 的本地桌面词典应用，支持 MDX 格式词典文件，完全离线运行，保护数据隐私。

## ✨ 功能特性

- 📚 **MDX 格式支持**: 直接读取主流 MDX 词典文件 (牛津、朗文、柯林斯、韦氏等)
- 🔍 **快速搜索**: 支持单词查询，SQLite 本地索引加速大型词典
- 📖 **丰富排版**: 保留原始 HTML/CSS 格式，显示音标、词性、释义、例句
- 🎯 **短语 & 习语**: 识别 Phrasal Verb 和 Idiom，支持关联搜索
- 📝 **个人笔记**: 每个单词支持添加用户笔记
- 🕒 **查询历史**: 自动记录查询历史，快速回看
- 🎨 **双视图模式**:
  - 默认视图: 单栏完整显示
  - 等分视图: 多词性按区域等分显示
- 🔒 **完全本地**: 词典文件和数据全部存储在本地，不上传任何数据

## 🚀 快速开始

### 环境要求

- Python 3.9 或更高版本
- macOS / Windows / Linux

### 安装步骤

1. **克隆或下载项目**
   ```bash
   cd FuncLex
   ```

2. **(推荐) 创建虚拟环境**
   ```bash
   python3 -m venv venv
   # macOS / Linux
   source venv/bin/activate
   # Windows
   venv\Scripts\activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **添加词典文件**

   项目根目录已预置部分 MDX 词典文件，你也可以：
   - 将自己的 `.mdx` 文件放入项目根目录或任意文件夹
   - 在应用设置中配置词典路径

5. **运行应用**
   ```bash
   python app.py
   ```

## 📁 项目结构

```
FuncLex/
├── app.py                    # 应用入口
├── requirements.txt          # Python 依赖
├── config.json               # 用户配置 (自动生成)
├── ROADMAP.md                # 开发路线图
├── funlex/
│   ├── core/                 # 核心逻辑层 (纯 Python，无 UI 依赖)
│   │   ├── models.py         # 数据模型
│   │   ├── mdx_parser.py     # MDX 解析
│   │   ├── dictionary.py     # 词典管理
│   │   ├── indexer.py        # SQLite 索引
│   │   ├── history.py        # 查询历史
│   │   └── notes.py          # 笔记管理
│   └── ui/                   # UI 层 (PySide6)
│       ├── main_window.py    # 主窗口
│       ├── search_bar.py     # 搜索框
│       ├── entry_view.py     # 默认词条视图
│       ├── entry_view_split.py  # 等分词条视图
│       ├── history_panel.py  # 历史面板
│       ├── notes_editor.py   # 笔记编辑器
│       ├── settings_dialog.py # 设置对话框
│       └── styles.py         # QSS 样式
├── data/                     # 本地数据 (自动生成)
└── dictionaries/             # 词典目录 (可选，可自定义)
```

## ⚙️ 配置说明

首次运行会自动生成 `config.json`，可手动修改或通过设置对话框调整：

```json
{
  "dictionary_paths": ["dictionaries/", "/absolute/path/to/your.mdx"],
  "default_dictionary": "牛津高阶英汉双解词典 第10版.mdx",
  "view_mode": "default",
  "theme": "light",
  "history_limit": 100
}
```

| 配置项 | 说明 | 可选值 |
|--------|------|--------|
| `dictionary_paths` | MDX 文件或目录路径列表 | 任意有效路径 |
| `default_dictionary` | 默认使用的词典文件名 | 已加载的词典名 |
| `view_mode` | 词条显示视图 | `default` / `split` |
| `theme` | UI 主题 | `light` / `dark` |
| `history_limit` | 历史记录最大条数 | 正整数 |

## 🛠️ 开发说明

详细开发计划请参考 [ROADMAP.md](./ROADMAP.md)。

### 核心分层原则

- **Core 层**: 纯 Python 实现，不依赖 PySide6。可独立测试、可替换 UI。
- **UI 层**: 仅调用 Core 层 API，通过信号槽异步通信。

### 运行测试 (开发中)

```bash
# 单元测试
python -m pytest tests/

# 代码检查
python -m flake8 funlex/
```

## 📄 许可证

详见 [LICENSE](./LICENSE) 文件。

## 🤝 致谢

- [readmdict](https://github.com/liusheng/readmdict) - MDX/MDD 解析库
- PySide6 / Qt 团队 - 优秀的跨平台 UI 框架
