#!/bin/bash
# GitHub Release创建脚本

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
echo -e "${GREEN}本地大模型防护系统 GitHub Release 创建工具 v${VERSION}${NC}"
echo -e "${GREEN}=========================================${NC}"

# 检查gh命令是否已安装
if ! command -v gh &> /dev/null; then
    echo -e "${YELLOW}GitHub CLI (gh) 未安装，尝试安装...${NC}"
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        brew install gh
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt &> /dev/null; then
            # Debian/Ubuntu
            sudo apt update
            sudo apt install gh
        elif command -v dnf &> /dev/null; then
            # Fedora
            sudo dnf install gh
        elif command -v yum &> /dev/null; then
            # RHEL/CentOS
            sudo yum install gh
        else
            echo -e "${RED}无法自动安装GitHub CLI，请手动安装: https://github.com/cli/cli#installation${NC}"
            exit 1
        fi
    else
        echo -e "${RED}无法自动安装GitHub CLI，请手动安装: https://github.com/cli/cli#installation${NC}"
        exit 1
    fi
fi

# 检查GitHub登录状态
echo -e "${YELLOW}检查GitHub登录状态...${NC}"
if ! gh auth status &> /dev/null; then
    echo -e "${YELLOW}未登录GitHub，请登录...${NC}"
    gh auth login
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}登录GitHub失败${NC}"
        exit 1
    fi
fi

# 检查当前分支
echo -e "${YELLOW}检查当前分支...${NC}"
CURRENT_BRANCH=$(git branch --show-current)
echo -e "当前分支: ${CURRENT_BRANCH}"

# 检查工作目录是否干净
echo -e "${YELLOW}检查工作目录状态...${NC}"
if ! git diff --quiet; then
    echo -e "${RED}工作目录不干净，请先提交或暂存更改${NC}"
    exit 1
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
fi

# 准备Release Notes
RELEASE_NOTES_FILE="${PROJECT_ROOT}/docs/release_notes_v${VERSION}.md"
if [ ! -f "$RELEASE_NOTES_FILE" ]; then
    echo -e "${RED}错误: Release Notes文件不存在: ${RELEASE_NOTES_FILE}${NC}"
    exit 1
fi

# 创建GitHub Release草稿
echo -e "${YELLOW}创建GitHub Release草稿...${NC}"
gh release create "v${VERSION}" \
    --draft \
    --title "本地大模型防护系统 v${VERSION}" \
    --notes-file "$RELEASE_NOTES_FILE"

if [ $? -ne 0 ]; then
    echo -e "${RED}创建GitHub Release草稿失败${NC}"
    exit 1
fi

echo -e "${GREEN}GitHub Release草稿创建成功!${NC}"

# 上传资产文件
echo -e "${YELLOW}是否上传资产文件? (y/n)${NC}"
read -p "" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 检查资产文件
    ASSETS_DIR="${PROJECT_ROOT}/dist"
    if [ ! -d "$ASSETS_DIR" ] || [ -z "$(ls -A $ASSETS_DIR)" ]; then
        echo -e "${RED}错误: 资产目录不存在或为空: ${ASSETS_DIR}${NC}"
        exit 1
    fi
    
    echo -e "${YELLOW}上传资产文件...${NC}"
    for asset in "$ASSETS_DIR"/*; do
        echo -e "${YELLOW}上传: $(basename "$asset")${NC}"
        gh release upload "v${VERSION}" "$asset" --clobber
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}上传资产文件失败: $(basename "$asset")${NC}"
            exit 1
        fi
    done
    
    echo -e "${GREEN}资产文件上传成功!${NC}"
fi

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}GitHub Release草稿创建完成!${NC}"
echo -e "${GREEN}请访问GitHub仓库页面查看并编辑Release草稿${NC}"
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
