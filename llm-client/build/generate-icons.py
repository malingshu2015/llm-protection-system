#!/usr/bin/env python3
"""
图标生成脚本 (Python 版本)
使用 Pillow 和 cairosvg 从 SVG 生成各平台图标
"""

import os
import sys
from pathlib import Path

try:
    from PIL import Image
    import cairosvg
except ImportError:
    print("❌ 缺少依赖库")
    print("请安装: pip install Pillow cairosvg")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
ICON_SVG = SCRIPT_DIR / "icon.svg"
TEMP_DIR = SCRIPT_DIR / "temp"

print("🎨 开始生成应用图标...")

# 创建临时目录
TEMP_DIR.mkdir(exist_ok=True)

print("📦 生成 PNG 图标...")

# 生成各种尺寸的 PNG
sizes = [16, 32, 48, 64, 128, 256, 512, 1024]

png_files = {}
for size in sizes:
    png_path = TEMP_DIR / f"icon_{size}.png"
    print(f"  ├─ {size}x{size}.png")

    # 使用 cairosvg 将 SVG 转换为 PNG
    cairosvg.svg2png(
        url=str(ICON_SVG),
        write_to=str(png_path),
        output_width=size,
        output_height=size
    )

    png_files[size] = png_path

print()
print("🍎 生成 macOS .icns 文件...")

# macOS .icns 需要使用 iconutil (仅在 macOS 上可用)
if sys.platform == "darwin":
    import subprocess

    iconset_dir = TEMP_DIR / "icon.iconset"
    iconset_dir.mkdir(exist_ok=True)

    # 复制和重命名文件到 iconset
    mappings = {
        16: ["icon_16x16.png"],
        32: ["icon_16x16@2x.png", "icon_32x32.png"],
        64: ["icon_32x32@2x.png"],
        128: ["icon_128x128.png"],
        256: ["icon_128x128@2x.png", "icon_256x256.png"],
        512: ["icon_256x256@2x.png", "icon_512x512.png"],
        1024: ["icon_512x512@2x.png"]
    }

    for size, names in mappings.items():
        src = png_files[size]
        for name in names:
            dst = iconset_dir / name
            Image.open(src).save(dst)

    # 生成 .icns
    icns_path = SCRIPT_DIR / "icon.icns"
    result = subprocess.run(
        ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print(f"  ✅ icon.icns 已生成")
    else:
        print(f"  ❌ iconutil 失败: {result.stderr}")
else:
    print("  ⚠️  iconutil 不可用(仅在 macOS 上可用),跳过 .icns 生成")

print()
print("🪟 生成 Windows .ico 文件...")

# 生成 .ico (包含多个尺寸)
ico_sizes = [16, 32, 48, 64, 128, 256]
ico_images = [Image.open(png_files[s]) for s in ico_sizes]

ico_path = SCRIPT_DIR / "icon.ico"
ico_images[0].save(
    ico_path,
    format='ICO',
    sizes=[(s, s) for s in ico_sizes],
    append_images=ico_images[1:]
)
print("  ✅ icon.ico 已生成")

print()
print("🐧 生成 Linux .png 文件...")

png_512_path = SCRIPT_DIR / "icon.png"
Image.open(png_files[512]).save(png_512_path)
print("  ✅ icon.png 已生成 (512x512)")

print()
print("✨ 所有图标生成完成!")
print()
print("生成的文件:")

for ext in ['.icns', '.ico', '.png', '.svg']:
    file_path = SCRIPT_DIR / f"icon{ext}"
    if file_path.exists():
        size = file_path.stat().st_size
        print(f"  {file_path.name:15} {size:>10,} bytes")

print()
print("📝 提示:")
print("  - icon.icns: macOS 应用图标")
print("  - icon.ico:  Windows 应用图标")
print("  - icon.png:  Linux 应用图标 (512x512)")
print("  - icon.svg:  源 SVG 文件")

# 清理临时文件
import shutil
shutil.rmtree(TEMP_DIR)
print()
print("🧹 临时文件已清理")
