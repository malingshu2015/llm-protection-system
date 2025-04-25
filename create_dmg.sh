#!/bin/bash
# 创建macOS DMG文件脚本

# 设置颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 获取项目根目录
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_ROOT"

# 获取版本号
if [ -f "VERSION" ]; then
    VERSION=$(cat VERSION)
else
    VERSION="1.0.0"
fi

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}本地大模型防护系统 DMG 创建工具 v${VERSION}${NC}"
echo -e "${GREEN}=========================================${NC}"

# 检查是否已构建应用程序
if [ ! -d "dist/本地大模型防护系统.app" ]; then
    echo -e "${RED}错误: 应用程序未构建。请先运行 build_macos.sh 构建应用程序。${NC}"
    exit 1
fi

# 检查是否安装了 create-dmg 工具
if ! command -v create-dmg &> /dev/null; then
    echo -e "${YELLOW}未找到 create-dmg 工具，尝试使用 hdiutil 创建 DMG 文件...${NC}"
    
    # 创建临时目录
    echo -e "${YELLOW}创建临时目录...${NC}"
    TMP_DIR="$PROJECT_ROOT/tmp_dmg"
    rm -rf "$TMP_DIR"
    mkdir -p "$TMP_DIR"
    
    # 复制应用程序到临时目录
    echo -e "${YELLOW}复制应用程序到临时目录...${NC}"
    cp -R "dist/本地大模型防护系统.app" "$TMP_DIR/"
    
    # 创建 Applications 链接
    echo -e "${YELLOW}创建 Applications 链接...${NC}"
    ln -s /Applications "$TMP_DIR/Applications"
    
    # 复制文档
    echo -e "${YELLOW}复制文档...${NC}"
    mkdir -p "$TMP_DIR/文档"
    cp README.md "$TMP_DIR/文档/"
    if [ -f "LICENSE" ]; then
        cp LICENSE "$TMP_DIR/文档/"
    fi
    
    # 复制文档文件
    for doc_file in docs/*.md; do
        if [ -f "$doc_file" ]; then
            cp "$doc_file" "$TMP_DIR/文档/"
        fi
    done
    
    # 创建 DMG 文件
    echo -e "${YELLOW}创建 DMG 文件...${NC}"
    DMG_FILE="$PROJECT_ROOT/本地大模型防护系统-${VERSION}.dmg"
    hdiutil create -volname "本地大模型防护系统" -srcfolder "$TMP_DIR" -ov -format UDZO "$DMG_FILE"
    
    # 清理临时目录
    echo -e "${YELLOW}清理临时目录...${NC}"
    rm -rf "$TMP_DIR"
else
    # 使用 create-dmg 工具创建 DMG 文件
    echo -e "${YELLOW}使用 create-dmg 工具创建 DMG 文件...${NC}"
    DMG_FILE="$PROJECT_ROOT/本地大模型防护系统-${VERSION}.dmg"
    create-dmg \
        --volname "本地大模型防护系统" \
        --volicon "static/favicon.ico" \
        --window-pos 200 120 \
        --window-size 800 400 \
        --icon-size 100 \
        --icon "本地大模型防护系统.app" 200 190 \
        --hide-extension "本地大模型防护系统.app" \
        --app-drop-link 600 185 \
        --no-internet-enable \
        "$DMG_FILE" \
        "dist/本地大模型防护系统.app"
fi

# 检查 DMG 文件是否创建成功
if [ -f "$DMG_FILE" ]; then
    echo -e "${GREEN}DMG 文件创建成功: ${DMG_FILE}${NC}"
    
    # 显示 DMG 文件信息
    echo -e "${YELLOW}DMG 文件信息:${NC}"
    ls -lh "$DMG_FILE"
    
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}DMG 创建完成!${NC}"
    echo -e "${GREEN}=========================================${NC}"
else
    echo -e "${RED}DMG 文件创建失败!${NC}"
    exit 1
fi
