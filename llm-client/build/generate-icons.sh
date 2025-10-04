#!/bin/bash
# 图标生成脚本
# 需要安装 ImageMagick 和 librsvg

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="$SCRIPT_DIR"
ICON_SVG="$BUILD_DIR/icon.svg"

echo "🎨 开始生成应用图标..."

# 检查依赖
if ! command -v convert &> /dev/null; then
    echo "❌ ImageMagick 未安装"
    echo "请安装: brew install imagemagick (macOS) 或 apt install imagemagick (Linux)"
    exit 1
fi

if ! command -v rsvg-convert &> /dev/null; then
    echo "⚠️  rsvg-convert 未安装,将使用 ImageMagick 转换 SVG"
    echo "推荐安装: brew install librsvg (macOS) 或 apt install librsvg2-bin (Linux)"
fi

# 创建临时目录
TMP_DIR=$(mktemp -d)
trap "rm -rf $TMP_DIR" EXIT

echo "📦 生成 PNG 图标..."

# 生成各种尺寸的 PNG
sizes=(16 32 48 64 128 256 512 1024)

for size in "${sizes[@]}"; do
    echo "  ├─ ${size}x${size}.png"
    if command -v rsvg-convert &> /dev/null; then
        rsvg-convert -w $size -h $size "$ICON_SVG" -o "$TMP_DIR/icon_${size}.png"
    else
        convert -background none -resize ${size}x${size} "$ICON_SVG" "$TMP_DIR/icon_${size}.png"
    fi
done

echo ""
echo "🍎 生成 macOS .icns 文件..."

# 创建 iconset 目录
ICONSET_DIR="$TMP_DIR/icon.iconset"
mkdir -p "$ICONSET_DIR"

# 复制和重命名文件到 iconset
cp "$TMP_DIR/icon_16.png" "$ICONSET_DIR/icon_16x16.png"
cp "$TMP_DIR/icon_32.png" "$ICONSET_DIR/icon_16x16@2x.png"
cp "$TMP_DIR/icon_32.png" "$ICONSET_DIR/icon_32x32.png"
cp "$TMP_DIR/icon_64.png" "$ICONSET_DIR/icon_32x32@2x.png"
cp "$TMP_DIR/icon_128.png" "$ICONSET_DIR/icon_128x128.png"
cp "$TMP_DIR/icon_256.png" "$ICONSET_DIR/icon_128x128@2x.png"
cp "$TMP_DIR/icon_256.png" "$ICONSET_DIR/icon_256x256.png"
cp "$TMP_DIR/icon_512.png" "$ICONSET_DIR/icon_256x256@2x.png"
cp "$TMP_DIR/icon_512.png" "$ICONSET_DIR/icon_512x512.png"
cp "$TMP_DIR/icon_1024.png" "$ICONSET_DIR/icon_512x512@2x.png"

# 生成 .icns
if command -v iconutil &> /dev/null; then
    iconutil -c icns "$ICONSET_DIR" -o "$BUILD_DIR/icon.icns"
    echo "  ✅ icon.icns 已生成"
else
    echo "  ⚠️  iconutil 不可用(仅在 macOS 上可用),跳过 .icns 生成"
fi

echo ""
echo "🪟 生成 Windows .ico 文件..."

# 生成 .ico (包含多个尺寸)
convert "$TMP_DIR/icon_16.png" \
        "$TMP_DIR/icon_32.png" \
        "$TMP_DIR/icon_48.png" \
        "$TMP_DIR/icon_64.png" \
        "$TMP_DIR/icon_128.png" \
        "$TMP_DIR/icon_256.png" \
        "$BUILD_DIR/icon.ico"

echo "  ✅ icon.ico 已生成"

echo ""
echo "🐧 生成 Linux .png 文件..."

cp "$TMP_DIR/icon_512.png" "$BUILD_DIR/icon.png"
echo "  ✅ icon.png 已生成 (512x512)"

echo ""
echo "✨ 所有图标生成完成!"
echo ""
echo "生成的文件:"
ls -lh "$BUILD_DIR"/icon.*

echo ""
echo "📝 提示:"
echo "  - icon.icns: macOS 应用图标"
echo "  - icon.ico:  Windows 应用图标"
echo "  - icon.png:  Linux 应用图标 (512x512)"
echo "  - icon.svg:  源 SVG 文件"
