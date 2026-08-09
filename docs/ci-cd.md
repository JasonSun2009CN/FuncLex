# FuncLex CI/CD 流水线方案

> Python + PySide6 桌面词典 GUI，PyInstaller 打包，GitHub Actions 一键出 **5 平台安装包**。

- 流水线文件：`.github/workflows/build.yml`（本方案唯一事实源）
- 产物：Windows 便携 zip · macOS 双架构 zip（.app）· Linux x86_64 / aarch64 压缩包
- 资源：内置 `dictionaries/` 词库（.mdx/.mdd）**随包打入**，离线开箱即用

---

## 0. 分支策略：只保留 `main`，禁止分平台分支

本方案**只用 `main` 一个分支**。Windows / macOS / Linux 的差异不靠分支承载，而收敛在 CI 的 **matrix 一维**里（一行一个平台）。

**为什么不建 `windows` / `macos` / `linux` 分平台分支？**

| 问题 | 分平台分支的弊端 |
|------|------------------|
| 构建逻辑割裂 | 每个分支各自维护一份打包脚本，改一处图标/依赖要同步 3 个分支，极易漏改、分叉漂移 |
| 跨平台改动无法原子落地 | 一次需要"在多个分支各提 PR"，评审 3 遍、CI 跑 3 遍，合并时序问题多 |
| 触发/发布混乱 | 打 tag 时选哪个分支？Release 从哪出？分支漂移导致"main 已改、发布分支还是旧代码" |
| 反模式 | 平台差异是**构建环境**差异，不是**源代码**差异；代码库只有一个，环境差异交给"运行环境 + 构建参数"表达 |

**正解**：唯一 `main` + GitHub Actions `strategy.matrix`。`runs-on: ${{ matrix.os }}` 一台云端虚拟机对应一个系统架构，五个任务**并行同步编译**；所有平台共享同一份构建参数，改动一处全平台生效。

---

## 1. GitHub 的三个"发布"概念：Release / Packages / Deployment

三者名字相近，用途完全不同：

### ① GitHub Release —— 给"人"下载的发布物
- **是什么**：绑定某个 tag 的**发布点**，可附任意二进制资产（zip/dmg/exe）、写发布说明、@提及、生成 changelog。每个 Release 是一个可下载、可收藏的里程碑。
- **适用场景**：**桌面应用安装包**、游戏、工具二进制、任何"终端用户要下载文件"的分发。
- **适合本项目**：✓ **唯一正确选择**。FuncLex 的交付物就是 5 个安装包，用户打开 Releases 页面挑对应平台下载。Assets 直接可点可下，版本历史一目了然，还能接 `latest` 跳转。

### ② GitHub Packages —— 给"程序"消费的制品仓库
- **是什么**：软件包注册表，托管容器镜像（`ghcr.io`）、npm、Maven、NuGet、RubyGems 等，供 `docker pull` / `npm install` / `pip install` **按依赖拉取**。
- **适用场景**：库 / SDK / 服务镜像 / 命令行工具——"被别的程序安装引用"的制品。
- **适合本项目**：✗ **不用**。GUI 桌面应用不是被依赖消费的包，用户不会 `pip install funlex`；把 zip 塞进容器注册表没有意义。

### ③ Deployments —— 给"环境"的部署状态
- **是什么**：一套**部署跟踪机制**，把 CI 产物"发布到哪里（生产/预发/某台服务器）"的状态、提交、环境 URL 关联起来，可与 `environment` 保护规则联动（人工审批门禁）。
- **适用场景**：**Web 服务 / 后端**——有明确的"运行环境"（VPS、K8s、云函数）需要部署。
- **适合本项目**：✗ **不用**。桌面离线应用**没有远程运行环境可部署**，用户下载安装就是"部署"，与 Deployment 的"推送服务上线"语义无关。

### 取舍结论（一句话）

> **Release 管"给人下载"，Packages 管"给程序拉取"，Deployments 管"给环境上线"。桌面离线 GUI 只有'人下载'这个需求 → 只上 GitHub Release。** 其余两者是为容器化/在线服务设计的，本项目一律不启用，避免概念污染。

---

## 2. 完整流水线：`.github/workflows/build.yml`

完整代码见 `build.yml`。这里讲结构与关键决策：

### 2.1 触发规则（三合一）

```yaml
on:
  push:
    branches: [main]      # ① 推 main → 打包存临时 Artifact（测试预览）
    tags: ["v*"]          # ② 推版本 tag → 打包后自动聚合 → 正式 Release
  workflow_dispatch:      # ③ 手动：任意分支自测
```

- **`push` main** 与 **`push` tag v\*** 是同一套矩阵打包逻辑，跑完分支去向不同：
  - main 推 → 5 个安装包上传 **Artifact**（仅 Actions 页面可见，`retention-days: 7`，供开发预览，**不对外分发**）；
  - tag 推 → 额外多跑一个 `release` 任务，下载全部安装包 → `gh release create` 建**正式 Release** 对外分发。
- tag 推时不重复打 main 的包：`branches: [main]` 不匹配 tag 的 ref，一个 push 只触发一次。

### 2.2 矩阵：一机一架构，同步编译

| matrix.os | 架构 | 产物 | 选它的理由 |
|-----------|------|------|-----------|
| `macos-15` | arm64 | `FuncLex-macOS-AppleSilicon-arm64.zip` | Apple Silicon 标准 runner |
| `macos-15-intel` | x86_64 | `FuncLex-macOS-Intel-x86_64.zip` | 现役 Intel runner（**`macos-13` 已退役**，`macos-14` 2026-11 停服，勿用） |
| `windows-latest` | x86_64 | `FuncLex-Windows-x64.zip` | Windows x64 |
| `ubuntu-22.04` | x86_64 | `FuncLex-Linux-x86_64.tar.gz` | glibc 2.35，**压低兼容地板**（见坑点④） |
| `ubuntu-22.04-arm` | aarch64 | `FuncLex-Linux-aarch64.tar.gz` | GitHub 官方 arm64 标签 |

`fail-fast: false`：单平台失败不拖垮其余平台。

### 2.3 各平台差异化打包命令

- **图标**：源图 `packaging/assets/icon.png`（入库）→ `python packaging/make_icons.py` 生成 `icon.icns`(mac) / `icon.ico`(win) / `icon-linux.png`(linux)。`icon.icns/ico` 不入库（`.gitignore`），CI 每次从源图现生成。
- **PyInstaller 一行通用**，差异用变量表达：

```bash
SEP=":"; [ "$RUNNER_OS" = "Windows" ] && SEP=";"   # add-data 分隔符随平台
ICON=""; [ -n "${{ matrix.icon }}" ] && ICON="--icon ${{ matrix.icon }}"
EXTRA=""; [ "$RUNNER_OS" = "macOS" ] && EXTRA="--osx-bundle-identifier com.funlex.app"

python -m PyInstaller --noconfirm --clean --onedir --windowed \
  --name FuncLex --paths . --hidden-import lzo \
  --add-data "funlex/ui/assets${SEP}funlex/ui/assets" \
  --add-data "dictionaries${SEP}dictionaries" \      # ← 内置词库随包打入
  --exclude-module PySide6.QtWebEngineCore \
  --exclude-module PySide6.QtWebEngineWidgets \
  $ICON $EXTRA app.py
```

- **资源嵌入**：`dictionaries/`（词库）+ `funlex/ui/assets/`（UI 资源）双 `--add-data`。onedir 模式下打入 `_internal/dictionaries`，运行期用 `sys._MEIPASS` 定位（见坑点⑥）。
- **压缩逻辑**（各平台用最可靠的命令）：
  - macOS → `ditto -c -k --keepParent dist/FuncLex.app`（保 .app 内**符号链接与权限**，`zip` 命令会丢）
  - Windows → Python `shutil.make_archive(..., root_dir='dist', base_dir='FuncLex')`（zip 内带 `FuncLex/` 目录包裹，避免 `Compress-Archive` 层级不可控）
  - Linux → `tar -C dist -czf ... FuncLex`（保可执行权限，天然便携）

### 2.4 聚合发布

```yaml
release:
  if: startsWith(github.ref, 'refs/tags/v')
  needs: build          # 等 5 个矩阵任务全部成功
  ...
  - run: gh release create "$TAG" release-assets/*.zip release-assets/*.tar.gz --generate-notes
```

用**独立 release 任务**（而非矩阵内各自创建）避免并发竞态：下载全部 artifact → 展平 → 一次性 `gh release create`。`permissions.contents: write` 赋予建 Release 权限。

---

## 3. 本地操作步骤

### 3.1 日常预览（push main）

```bash
git add -A && git commit -m "feat: xxx"
git push origin main
```

→ Actions 自动跑 5 平台打包，`Actions → Build & Release FuncLex → build` 任务组里下载 **Artifact**（zip/tar.gz），本地解压自测。7 天后自动清理。

### 3.2 正式发布（打版本 tag）

```bash
# 1) 确认版本号（funlex/__init__.py 的 __version__）
grep __version__ funlex/__init__.py

# 2) 打 tag（v 开头 + 语义化版本；建议先自测过 main 的 artifact 再发）
git tag v0.4.0

# 3) 推送 tag —— 触发打包 + 自动建 Release
git push origin v0.4.0

# 4) 等 Actions 完成（约 10-20 分钟，5 平台并行）
#    → 打开 https://github.com/<owner>/FuncLex/releases/tag/v0.4.0
#    → 5 个安装包已全部附上，Release 已自动发布（--generate-notes 自动生成说明）
#    → 若想先审阅再公开：在 build.yml 的 gh release create 加 --draft
```

**常用维护命令**

```bash
git tag                        # 看本地 tag
git ls-remote --tags origin    # 看远端 tag
git tag -d v0.4.0 && git push origin :v0.4.0   # 删本地+远端 tag（重打 tag 前先删）
```

> 注意：tag 推上去、Release 建好后，**同名 tag 不能原地重推**（非 fast-forward 会被拒）。要修版本：删 tag → 重新 `git tag` → 再 push。

### 3.3 手动自测（不污染 main/tag）

Actions → **Build & Release FuncLex** → Run workflow → 可临时改 `__version__` 在分支上验证，或直接跑 main。产物同样落 Artifact。

### 3.4 本地兜底打包（不开 CI 也能验）

```bash
./packaging/build_mac.sh arm          # macOS 本机
./packaging/build_linux.sh            # Linux 本机
build_windows.bat                     # Windows 本机（cmd）
```

---

## 4. 三大常见坑点与解决方案

### 坑点 ① mac 安全拦截（Gatekeeper / 未签名警告）

**现象**：用户双击下载的 `.app` → "无法打开，因为来自身份不明的开发者" / "已损坏，无法打开"。

**原因**：CI 里没有 Apple Developer 证书，产物**未公证（notarize）**。macOS 对**所有从网络下载**的文件打 `com.apple.quarantine` 属性，Gatekeeper 据此拦截未签名/未公证应用。**注意**：`macos-13` 已退役、`macos-14` 2026-11 停服，Intel 构建必须用 `macos-15-intel`。

**解决**（逐级递进）：

1. **ad-hoc 签名兜底**（CI 已做）：`codesign --force --deep -s - dist/FuncLex.app`，失败则移除签名，**不阻塞构建**。减少本地"资源分叉"报错，但跨机器下载仍会有 quarantine。
2. **用户侧放行**（对每个下载的 app）：
   ```bash
   xattr -dr com.apple.quarantine /path/to/FuncLex.app   # 或：右键 → 打开
   ```
3. **正式分发**：申请 Apple Developer 账号（$99/年），把证书+公证凭据配成 workflow secrets：
   - `APPLE_CERT_BASE64` / `APPLE_CERT_PASSWORD` / `APPLE_NOTARIZATION_APPLE_ID` / `APPLE_NOTARIZATION_TEAM_ID` / `APPLE_NOTARIZATION_PASSWORD`（App-specific password）
   - CI 里 `import-certificate` → 签名 → `notarytool submit` → `stapler staple`，用户即可**正常双击打开**。
4. **macOS 15 特有坑**：系统会给部分文件打 `com.apple.provenance`（用户态无法 `xattr -d` 剥离），导致 ad-hoc 签名报 `resource fork ... not allowed`。CI 已做"签名失败→移除签名"兜底——未签名 app 仍可右键打开运行。

### 坑点 ② Linux glibc 兼容

**现象**：在 `ubuntu-latest`（24.04，glibc 2.39）打出的包，拿到老发行版（Ubuntu 20.04、Debian 11、CentOS）上 `Segmentation fault` 或 `version GLIBC_2.34 not found`。

**原因**：Linux 二进制链接的是**构建机 glibc** 的符号版本。构建机 glibc 越新，跑得起的发行版越少——**glibc 兼容地板 = 构建机 glibc 版本**。

**解决**：

1. **用尽量老的镜像构建**：本流水线 x64/aarch64 都用 `ubuntu-22.04`（glibc 2.35），而不是 `latest`。这已经把地板压到 glibc 2.35 附近。
2. **真正的地板由依赖 wheel 决定**：
   - PySide6 x64 wheel = `manylinux_2_28`（glibc 2.28）；**aarch64 新版 wheel 是 `manylinux_2_39`（glibc 2.39）**——在 22.04 上 pip 自动回退装 **PySide6 6.8.0**（`manylinux_2_31`，glibc 2.31 地板），对老系统反而更友好。
   - 结论：**x64 产物要求 glibc ≥ 2.28（≈ Ubuntu 20.04+），aarch64 ≥ 2.31**。在"支持到哪"的 Release 说明里写明。
3. **追求更低地板（可选）**：改用 `manylinux` 容器（`quay.io/pypa/manylinux_2_28_*`）或 [PyApp](https://github.com/ofek/pyapp) 静态链接方案，能把地板降到 glibc 2.28 甚至 2.17。对纯桌面工具通常不值得。
4. **别在容器里跑 GUI**：如用 Docker 打包，`apt install` 的系统库（GStreamer 等）也要装，且产物需带对应 `.so`——本方案直接在全功能 runner 上构建，规避此问题。

### 坑点 ③ Python 资源路径（PyInstaller 下找不到文件）

**现象**：源码运行正常，打包后启动报 `FileNotFoundError` / 词典加载失败 / 找不到内置词库。

**原因**：PyInstaller 打包后，`__file__`、`os.getcwd()` 都**不可信**：
- 资源被塞进 `_internal/`（onedir）或解压到临时目录，`__file__` 指向的是**运行目录/临时目录**；
- `os.getcwd()` 随用户从哪个目录启动而变化（双击桌面图标 vs 终端启动结果不同）。

**解决**（本仓库已内置到 `funlex/core/paths.py`）：

1. **打包资源用 `sys._MEIPASS` 定位**（PyInstaller 提供的、指向资源根的正规 API）：
   ```python
   def bundled_dictionary_dir():
       if is_frozen():
           base = getattr(sys, "_MEIPASS", None)
           if base and (d := Path(base) / "dictionaries").is_dir():
               return d
       return Path()
   ```
   本方案据此让打包版同时扫描：内置 `_internal/dictionaries` → 用户数据目录 `dictionaries/`（扩充）。用户自己加的词典放数据目录，更新内置词库才需重发版。
2. **写数据永不写安装目录**：索引/历史/笔记/配置落到平台用户数据目录——macOS `~/Library/Application Support/FuncLex/`、Windows `%APPDATA%\FuncLex\`、Linux `~/.local/share/FuncLex/`（`paths.py` 已实现 `is_frozen()` 分支）。
3. **判定规则**：`bool(getattr(sys, "frozen", False))` 区分开发/打包；`sys._MEIPASS` 只在 frozen 时存在，**不要硬编码路径**，也不要 `Path(__file__).parent / ".."` 拼接。

---

## 5. 变更清单（本次已落地）

| 文件 | 改动 |
|------|------|
| `.github/workflows/build.yml` | 重写：5 平台矩阵 + 内置词库 + push/tag 双触发 + 自动 Release |
| `dictionaries/` | 5 本 `.mdx` 从仓库根移入（内置词库，随包打入） |
| `funlex/core/paths.py` | frozen 模式新增扫描内置 `_internal/dictionaries` |
| `packaging/build_*.sh / build_windows.bat` | 本地打包同步 `--add-data dictionaries` |
| `FuncLex.spec` | datas 增加 `dictionaries` |
| `packaging/README.md` | 产物表 5 版、CI 触发规则、内置词库说明 |
| `README.md` | 词典扫描目录说明更新 |
| `docs/ci-cd.md` | 本方案 |
