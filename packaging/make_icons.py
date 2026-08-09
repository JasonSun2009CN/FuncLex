"""从源图生成三平台应用图标：icon.icns(mac) / icon.ico(win) / icon.png(linux)

用法:
    python packaging/make_icons.py <源图.png|.svg> [输出目录，默认 packaging/assets]

- 源图建议 ≥1024×1024 的 PNG（带透明）；若给 SVG 且装了 cairosvg 也会栅格化
- 输出到 outdir:
    icon.icns       macOS（本机走 iconutil，最可靠；无则 Pillow 兜底）
    icon.ico        Windows（16~256 多尺寸）
    icon-linux.png  Linux（256×256 桌面图标）
- 依赖: pip install pillow

设计好正式 icon 后，把源图替换到 packaging/assets/icon.png 重跑本脚本即可
（源图保持 1024 不被覆盖，Linux 图标单独输出 icon-linux.png）。
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ICONSET_SIZES = [
    ("icon_16x16.png", 16, 1),
    ("icon_16x16@2x.png", 16, 2),
    ("icon_32x32.png", 32, 1),
    ("icon_32x32@2x.png", 32, 2),
    ("icon_128x128.png", 128, 1),
    ("icon_128x128@2x.png", 128, 2),
    ("icon_256x256.png", 256, 1),
    ("icon_256x256@2x.png", 256, 2),
    ("icon_512x512.png", 512, 1),
    ("icon_512x512@2x.png", 512, 2),
]


def load_source(src: Path) -> Image.Image:
    if src.suffix.lower() == ".svg":
        try:
            import cairosvg
            import io

            png = cairosvg.svg2png(
                url=str(src), output_width=1024, output_height=1024
            )
            img = Image.open(io.BytesIO(png))
        except ImportError:
            sys.exit("SVG 源图需要 cairosvg（pip install cairosvg）；或直接提供 PNG。")
    else:
        img = Image.open(src)
    if img.mode != "RGBA":
        img = img.convert("RGBA")
    return img


def make_icns(img: Image.Image, out: Path) -> None:
    if sys.platform == "darwin" and shutil.which("iconutil"):
        with tempfile.TemporaryDirectory() as td:
            iconset = Path(td) / "icon.iconset"
            iconset.mkdir()
            for name, size, scale in ICONSET_SIZES:
                s = img.resize((size * scale, size * scale), Image.LANCZOS)
                s.save(iconset / name)
            subprocess.run(
                ["iconutil", "-c", "icns", str(iconset), "-o", str(out)],
                check=True,
            )
        print(f"  生成 {out.name}（iconutil）")
    else:
        # Pillow 兜底（写单尺寸 ICNS，部分系统兼容）
        img.save(out, format="ICNS")
        print(f"  生成 {out.name}（Pillow）")


def make_ico(img: Image.Image, out: Path) -> None:
    img.save(out, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"  生成 {out.name}")


def make_png(img: Image.Image, out: Path) -> None:
    img.resize((256, 256), Image.LANCZOS).save(out, format="PNG")
    print(f"  生成 {out.name}")


def main() -> None:
    # Windows 控制台默认 cp1252 无法编码中文 print，强制 UTF-8（CI 与本地双保险）
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="生成三平台应用图标")
    ap.add_argument("source", type=Path, help="源图 PNG/SVG（≥1024×1024）")
    ap.add_argument("outdir", type=Path, nargs="?", default=Path("packaging/assets"))
    args = ap.parse_args()

    if not args.source.is_file():
        sys.exit(f"源图不存在: {args.source}")
    # 防呆：Linux 输出名与源图分离，绝不覆盖源图
    if args.outdir.resolve() / "icon-linux.png" == args.source.resolve():
        sys.exit("输出 icon-linux.png 与源图同名，会覆盖；请更换源图文件名或使用独立 outdir。")
    args.outdir.mkdir(parents=True, exist_ok=True)
    img = load_source(args.source)
    print(f"源图: {args.source}（{img.size[0]}×{img.size[1]}）")

    make_icns(img, args.outdir / "icon.icns")
    make_ico(img, args.outdir / "icon.ico")
    make_png(img, args.outdir / "icon-linux.png")
    print("完成。")


if __name__ == "__main__":
    main()
