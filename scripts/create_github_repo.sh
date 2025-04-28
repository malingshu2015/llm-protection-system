#!/bin/bash
# 创建GitHub仓库并推送代码的简化脚本

# 设置颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 获取项目根目录
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$PROJECT_ROOT"

# 获取版本号
if [ -f "VERSION" ]; then
    VERSION=$(cat VERSION)
else
    VERSION="1.0.0"
fi

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}本地大模型防护系统 GitHub 仓库创建工具 v${VERSION}${NC}"
echo -e "${GREEN}=========================================${NC}"

# 询问仓库信息
echo -e "${YELLOW}请输入GitHub用户名:${NC}"
read GITHUB_USERNAME

if [ -z "$GITHUB_USERNAME" ]; then
    echo -e "${RED}错误: GitHub用户名不能为空${NC}"
    exit 1
fi

echo -e "${YELLOW}请输入仓库名称 (默认: llm-protection-system):${NC}"
read REPO_NAME
REPO_NAME=${REPO_NAME:-"llm-protection-system"}

echo -e "${YELLOW}请输入仓库描述:${NC}"
read REPO_DESC
REPO_DESC=${REPO_DESC:-"本地大模型防护系统 - 为本地部署的大型语言模型提供安全防护"}

echo -e "${YELLOW}是否将仓库设为私有? (y/n)${NC}"
read -p "" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    PRIVATE="--private"
else
    PRIVATE="--public"
fi

# 创建远程仓库
echo -e "${YELLOW}创建GitHub仓库...${NC}"
echo -e "${YELLOW}请在浏览器中手动创建GitHub仓库:${NC}"
echo -e "${YELLOW}1. 访问 https://github.com/new${NC}"
echo -e "${YELLOW}2. 仓库名称: ${REPO_NAME}${NC}"
echo -e "${YELLOW}3. 仓库描述: ${REPO_DESC}${NC}"
echo -e "${YELLOW}4. 选择${PRIVATE}${NC}"
echo -e "${YELLOW}5. 点击'创建仓库'按钮${NC}"
echo -e "${YELLOW}6. 复制仓库URL${NC}"

echo -e "${YELLOW}请输入仓库URL:${NC}"
read REPO_URL

if [ -z "$REPO_URL" ]; then
    echo -e "${RED}错误: 仓库URL不能为空${NC}"
    exit 1
fi

# 设置远程仓库
echo -e "${YELLOW}设置远程仓库...${NC}"
if git remote | grep -q "origin"; then
    git remote remove origin
fi

git remote add origin "$REPO_URL"

if [ $? -ne 0 ]; then
    echo -e "${RED}设置远程仓库失败${NC}"
    exit 1
fi

# 推送代码
echo -e "${YELLOW}推送代码到远程仓库...${NC}"
git push -u origin main

if [ $? -ne 0 ]; then
    echo -e "${RED}推送代码失败${NC}"
    echo -e "${YELLOW}尝试使用强制推送...${NC}"
    git push -u origin main --force
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}强制推送也失败了${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}代码推送成功!${NC}"

# 创建版本标签
echo -e "${YELLOW}是否创建版本标签 v${VERSION}? (y/n)${NC}"
read -p "" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}创建版本标签...${NC}"
    git tag -a "v${VERSION}" -m "Release v${VERSION}"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}创建版本标签失败${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}推送版本标签...${NC}"
    git push origin "v${VERSION}"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}推送版本标签失败${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}版本标签创建并推送成功!${NC}"
fi

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}GitHub仓库创建完成!${NC}"
echo -e "${GREEN}仓库URL: ${REPO_URL}${NC}"
echo -e "${GREEN}=========================================${NC}"

# 打开仓库页面
echo -e "${YELLOW}是否打开仓库页面? (y/n)${NC}"
read -p "" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if command -v open &> /dev/null; then
        # macOS
        open "$REPO_URL"
    elif command -v xdg-open &> /dev/null; then
        # Linux
        xdg-open "$REPO_URL"
    elif command -v start &> /dev/null; then
        # Windows
        start "$REPO_URL"
    else
        echo -e "${YELLOW}无法自动打开浏览器，请手动访问: ${REPO_URL}${NC}"
    fi
fi
