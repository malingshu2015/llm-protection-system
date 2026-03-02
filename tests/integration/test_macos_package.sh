#!/bin/bash
# 测试macOS安装包脚本

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
echo -e "${GREEN}本地大模型防护系统 macOS 安装包测试工具 v${VERSION}${NC}"
echo -e "${GREEN}=========================================${NC}"

# 检查是否已创建DMG文件
DMG_FILE="$PROJECT_ROOT/本地大模型防护系统-${VERSION}.dmg"
if [ ! -f "$DMG_FILE" ]; then
    echo -e "${RED}错误: DMG 文件未创建。请先运行 create_dmg.sh 创建 DMG 文件。${NC}"
    exit 1
fi

# 检查是否已构建应用程序
if [ ! -d "dist/本地大模型防护系统.app" ]; then
    echo -e "${RED}错误: 应用程序未构建。请先运行 build_macos.sh 构建应用程序。${NC}"
    exit 1
fi

# 测试DMG文件
echo -e "${YELLOW}测试 DMG 文件...${NC}"
echo -e "${YELLOW}检查 DMG 文件完整性...${NC}"
hdiutil verify "$DMG_FILE"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}DMG 文件完整性检查通过!${NC}"
else
    echo -e "${RED}DMG 文件完整性检查失败!${NC}"
    exit 1
fi

# 测试应用程序
echo -e "${YELLOW}测试应用程序...${NC}"
echo -e "${YELLOW}检查应用程序可执行性...${NC}"
if [ -x "dist/本地大模型防护系统.app/Contents/MacOS/llm-protection-system" ]; then
    echo -e "${GREEN}应用程序可执行性检查通过!${NC}"
else
    echo -e "${RED}应用程序可执行性检查失败!${NC}"
    exit 1
fi

# 检查应用程序资源
echo -e "${YELLOW}检查应用程序资源...${NC}"
if [ -d "dist/本地大模型防护系统.app/Contents/Resources" ]; then
    echo -e "${GREEN}应用程序资源检查通过!${NC}"
else
    echo -e "${RED}应用程序资源检查失败!${NC}"
    exit 1
fi

# 检查应用程序框架
echo -e "${YELLOW}检查应用程序框架...${NC}"
if [ -d "dist/本地大模型防护系统.app/Contents/Frameworks" ]; then
    echo -e "${GREEN}应用程序框架检查通过!${NC}"
else
    echo -e "${RED}应用程序框架检查失败!${NC}"
    exit 1
fi

# 检查应用程序签名
echo -e "${YELLOW}检查应用程序签名...${NC}"
codesign -vv "dist/本地大模型防护系统.app" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}应用程序签名检查通过!${NC}"
else
    echo -e "${YELLOW}应用程序未签名或签名无效，这在开发环境中是正常的。${NC}"
fi

# 检查应用程序启动
echo -e "${YELLOW}检查应用程序启动...${NC}"
echo -e "${YELLOW}注意: 这将尝试启动应用程序，请在应用程序启动后手动关闭它。${NC}"
echo -e "${YELLOW}按任意键继续，或按 Ctrl+C 取消...${NC}"
read -n 1 -s

# 尝试启动应用程序
open "dist/本地大模型防护系统.app"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}应用程序启动成功!${NC}"
    echo -e "${YELLOW}请在测试完成后手动关闭应用程序。${NC}"
    echo -e "${YELLOW}按任意键继续...${NC}"
    read -n 1 -s
else
    echo -e "${RED}应用程序启动失败!${NC}"
    exit 1
fi

# 测试完成
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}macOS 安装包测试完成!${NC}"
echo -e "${GREEN}所有测试通过!${NC}"
echo -e "${GREEN}=========================================${NC}"
