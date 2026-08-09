"""生成占位图标（正式 icon 设计好后，直接替换 assets/icon.png 即可）"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

SIZE = 1024
OUT = os.path.join(os.path.dirname(__file__), "assets", "icon.png")

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# 圆角矩形底板（macOS squircle 风格近似）
def rounded(radius=230):
    m = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(m).rounded_rectangle([0, 0, SIZE, SIZE], radius=radius, fill=(0, 122, 255, 255))
    return m

base = rounded()
# 顶部亮渐变叠加
grad = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
gd = ImageDraw.Draw(grad)
for y in range(SIZE):
    a = int(90 * (1 - y / SIZE))
    gd.line([(0, y), (SIZE, y)], fill=(255, 255, 255, a))
img = Image.alpha_composite(base, grad)

# 白色 "F" 字母
d = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 560)
except Exception:
    font = ImageFont.load_default()
bbox = d.textbbox((0, 0), "F", font=font)
tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
d.text(((SIZE - tw) / 2 - bbox[0], (SIZE - th) / 2 - bbox[1]), "F",
       font=font, fill=(255, 255, 255, 255))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
img.save(OUT, format="PNG")
print(f"placeholder icon -> {OUT} ({img.size[0]}x{img.size[1]})")
