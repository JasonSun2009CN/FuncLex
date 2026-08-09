# 打包指南

FuncLex 用 **PyInstaller（onedir 模式）** 打包，5 个版本（CI 矩阵一键并行出齐）：

| 版本 | 目标 | 构建环境 | 产物 |
|------|------|----------|------|
| `mac-arm` | Apple Silicon Mac | macOS arm64（`macos-15`） | `FuncLex-macOS-AppleSilicon-arm64.zip`（.app） |
| `mac-intel` | Intel Mac | macOS x86_64（`macos-15-intel`） | `FuncLex-macOS-Intel-x86_64.zip`（.app） |
| `windows` | Windows 10/11 x64 | Windows（`windows-latest`） | `FuncLex-Windows-x64.zip`（便携目录） |
| `linux-x64` | Linux x86_64 | Ubuntu 22.04（glibc 2.35） | `FuncLex-Linux-x86_64.tar.gz` |
| `linux-arm64` | Linux aarch64 | Ubuntu 22.04-arm | `FuncLex-Linux-aarch64.tar.gz` |

> PyInstaller **不能交叉编译**：哪个平台就在哪个平台打。CI 用 GitHub Actions 矩阵一行一个平台、同步编译。
> 完整 CI/CD 方案（触发规则、Release/Packages/Deployment 取舍、本地操作、三大坑点）见 [docs/ci-cd.md](../docs/ci-cd.md)。

## 数据目录（打包后）

打包后的应用不依赖启动目录，数据落在平台用户目录（首次运行自动创建）：

- macOS: `~/Library/Application Support/FuncLex/`
  - 词典 `.mdx` / 发音 `.mdd` → 放 `…/FuncLex/dictionaries/`
  - `data/`（index.db 等）、`config.json` → 在 `…/FuncLex/`
- Windows: `%APPDATA%\FuncLex\`
- Linux: `~/.local/share/FuncLex/`

也可在应用"设置 → 词典路径"里手动指定。

## 图标

设计好正式图标后：

1. 把源图（≥1024×1024 PNG，带透明）放 `packaging/assets/icon.png`
2. 跑一次 `python packaging/make_icons.py packaging/assets/icon.png packaging/assets`
   → 生成 `icon.icns` / `icon.ico` / `icon.png`
3. 重新构建即可。当前 `assets/` 是占位图标。

> 也可给 SVG（需 `pip install cairosvg`）。

## 本地构建

### macOS（在 Mac 上）

```bash
# Apple Silicon
./packaging/build_mac.sh arm
# Intel（需 x86_64 Python，如 Rosetta 下或 python.org x86_64 安装包）
PYTHON_BIN=/path/to/x86_64-python3 ./packaging/build_mac.sh intel
```

产物 `dist/FuncLex.app`。未签名 → 首次打开需右键→打开（或自行 codesign+notarize）。

### Windows（在 Windows 上）

```cmd
build_windows.bat
```

`python-lzo` 若 pip 装不上：`conda install python-lzo` 或装 Visual C++ Build Tools。

### Linux（在 Linux 上）

```bash
./packaging/build_linux.sh
```

- `python-lzo`：Ubuntu 先 `apt install liblzo2-dev`
- `.mdd` 发音依赖 GStreamer：`apt install gstreamer1.0-plugins-base gstreamer1.0-plugins-good`

## CI 一键构建 5 版

推到 GitHub 后自动触发（无需手动）：

- **push 到 `main`**：5 个矩阵任务并行打包成安装包，存临时 **Artifact**（Actions 页面下载预览，7 天自动清理）
- **push 版本 tag `v*`**：打包完成后自动聚合全部安装包，创建正式 **GitHub Release**（无需手动操作）
- 手动触发：Actions → **Build & Release FuncLex** → Run workflow（任意分支自测）

> 本地打标签 → 推送 → 自动发版的具体步骤见 [docs/ci-cd.md](../docs/ci-cd.md) 第 3 节。

## 注意 / 常见问题

- **内置词库 `dictionaries/` 随包打入**（`--add-data`），离线开箱即用；`data/`（索引/历史/笔记）运行时生成在用户数据目录，不打进包。内置词典更新需重新发版。
- **排除 QtWebEngine 以减小体积**（应用未用到）；若某平台构建异常，去掉 `--exclude-module PySide6.QtWebEngine*` 重试。
- **mac 架构**：PyInstaller 打出的版本跟随所用 Python 的架构。
  - 本开发机是 **Intel（x86_64）**，本地 `build_mac.sh arm` 打出的仍是 x86_64；
    要 **Apple Silicon 版**需 arm64 的 Python（如 python.org arm64 安装包）或 CI 的 `macos-15` runner。
  - 快捷路径：直接推 GitHub 用 Actions 矩阵，`macos-15-intel`(Intel) + `macos-15`(arm) 各出一个。
- **mac 签名（较新 macOS 的 com.apple.provenance 坑）**：
  macOS 会给打包文件打 `com.apple.provenance` 系统托管属性，用户态 `xattr -d` 删不掉，
  codesign 因此报 `resource fork, Finder information, or similar detritus not allowed`，**ad-hoc 签名做不了**。
  脚本会尽力签名、失败则移除签名——**未签名 app 可正常运行**（首次打开需右键→打开）。
  正式分发建议在无此限制的环境用 Apple Developer 证书签名+公证，可免 Gatekeeper 弹窗。
- **python-lzo**：mac/Linux 直接 pip；Windows 装不上时 `conda install python-lzo` 或装 Visual C++ Build Tools。
