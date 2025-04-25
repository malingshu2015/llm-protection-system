#!/bin/bash
# GitHub发布脚本

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
    echo -e "${RED}错误: VERSION文件不存在${NC}"
    exit 1
fi

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}本地大模型防护系统 GitHub 发布工具 v${VERSION}${NC}"
echo -e "${GREEN}=========================================${NC}"

# 检查gh命令是否已安装
if ! command -v gh &> /dev/null; then
    echo -e "${RED}错误: GitHub CLI (gh) 未安装${NC}"
    echo -e "${YELLOW}请安装GitHub CLI: https://github.com/cli/cli#installation${NC}"
    exit 1
fi

# 检查GitHub登录状态
echo -e "${YELLOW}检查GitHub登录状态...${NC}"
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}未登录GitHub，请先登录...${NC}"
    gh auth login
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}登录GitHub失败${NC}"
        exit 1
    fi
fi

# 创建GitHub仓库
echo -e "${YELLOW}是否创建新的GitHub仓库? (y/n)${NC}"
read -p "" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}请输入仓库名称 (默认: llm-protection-system):${NC}"
    read REPO_NAME
    REPO_NAME=${REPO_NAME:-llm-protection-system}
    
    echo -e "${YELLOW}请输入仓库描述:${NC}"
    read REPO_DESC
    REPO_DESC=${REPO_DESC:-"本地大模型防护系统 - 为本地部署的大型语言模型提供安全防护"}
    
    echo -e "${YELLOW}是否将仓库设为私有? (y/n)${NC}"
    read -p "" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        VISIBILITY="--private"
    else
        VISIBILITY="--public"
    fi
    
    echo -e "${YELLOW}创建GitHub仓库...${NC}"
    gh repo create $REPO_NAME --description "$REPO_DESC" $VISIBILITY --source=. --remote=origin --push
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}创建GitHub仓库失败${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}GitHub仓库创建成功!${NC}"
else
    # 检查是否已设置远程仓库
    if ! git remote | grep -q "origin"; then
        echo -e "${YELLOW}未设置远程仓库，请输入远程仓库URL:${NC}"
        read REMOTE_URL
        
        if [ -z "$REMOTE_URL" ]; then
            echo -e "${RED}错误: 远程仓库URL不能为空${NC}"
            exit 1
        fi
        
        echo -e "${YELLOW}设置远程仓库...${NC}"
        git remote add origin "$REMOTE_URL"
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}设置远程仓库失败${NC}"
            exit 1
        fi
    fi
    
    # 推送代码到远程仓库
    echo -e "${YELLOW}推送代码到远程仓库...${NC}"
    git push -u origin main
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}推送代码到远程仓库失败${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}代码推送成功!${NC}"
fi

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

# 创建GitHub Release
echo -e "${YELLOW}是否创建GitHub Release? (y/n)${NC}"
read -p "" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 准备Release Notes
    RELEASE_NOTES_FILE="${PROJECT_ROOT}/docs/release_notes_v${VERSION}.md"
    if [ ! -f "$RELEASE_NOTES_FILE" ]; then
        echo -e "${RED}错误: Release Notes文件不存在: ${RELEASE_NOTES_FILE}${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}是否创建草稿版本? (y/n)${NC}"
    read -p "" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        DRAFT_FLAG="--draft"
    else
        DRAFT_FLAG=""
    fi
    
    echo -e "${YELLOW}创建GitHub Release...${NC}"
    gh release create "v${VERSION}" \
        $DRAFT_FLAG \
        --title "本地大模型防护系统 v${VERSION}" \
        --notes-file "$RELEASE_NOTES_FILE"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}创建GitHub Release失败${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}GitHub Release创建成功!${NC}"
    
    # 上传资产文件
    echo -e "${YELLOW}是否上传资产文件? (y/n)${NC}"
    read -p "" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 检查资产文件
        echo -e "${YELLOW}上传Python包...${NC}"
        if [ -d "${PROJECT_ROOT}/dist" ] && [ ! -z "$(ls -A ${PROJECT_ROOT}/dist)" ]; then
            for asset in "${PROJECT_ROOT}/dist"/*; do
                echo -e "${YELLOW}上传: $(basename "$asset")${NC}"
                gh release upload "v${VERSION}" "$asset" --clobber
                
                if [ $? -ne 0 ]; then
                    echo -e "${RED}上传资产文件失败: $(basename "$asset")${NC}"
                    exit 1
                fi
            done
        else
            echo -e "${YELLOW}未找到Python包，跳过上传${NC}"
        fi
        
        echo -e "${YELLOW}上传macOS DMG文件...${NC}"
        DMG_FILE="${PROJECT_ROOT}/本地大模型防护系统-${VERSION}.dmg"
        if [ -f "$DMG_FILE" ]; then
            echo -e "${YELLOW}上传: $(basename "$DMG_FILE")${NC}"
            gh release upload "v${VERSION}" "$DMG_FILE" --clobber
            
            if [ $? -ne 0 ]; then
                echo -e "${RED}上传DMG文件失败${NC}"
                exit 1
            fi
        else
            echo -e "${YELLOW}未找到DMG文件，跳过上传${NC}"
        fi
        
        echo -e "${GREEN}资产文件上传成功!${NC}"
    fi
fi

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}GitHub发布完成!${NC}"
echo -e "${GREEN}=========================================${NC}"

# 打开GitHub Release页面
echo -e "${YELLOW}是否打开GitHub Release页面? (y/n)${NC}"
read -p "" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 获取仓库URL
    REPO_URL=$(git config --get remote.origin.url)
    REPO_URL=${REPO_URL%.git}
    
    if [[ "$REPO_URL" == *"github.com"* ]]; then
        RELEASE_URL="${REPO_URL}/releases"
        
        if command -v open &> /dev/null; then
            # macOS
            open "$RELEASE_URL"
        elif command -v xdg-open &> /dev/null; then
            # Linux
            xdg-open "$RELEASE_URL"
        elif command -v start &> /dev/null; then
            # Windows
            start "$RELEASE_URL"
        else
            echo -e "${YELLOW}无法自动打开浏览器，请手动访问: ${RELEASE_URL}${NC}"
        fi
    else
        echo -e "${YELLOW}无法确定GitHub仓库URL，请手动访问GitHub仓库页面${NC}"
    fi
fi
