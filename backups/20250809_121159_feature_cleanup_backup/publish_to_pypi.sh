#!/bin/bash
# PyPI发布脚本

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
echo -e "${GREEN}本地大模型防护系统 PyPI 发布工具 v${VERSION}${NC}"
echo -e "${GREEN}=========================================${NC}"

# 检查虚拟环境
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}警告: 未检测到虚拟环境，建议在虚拟环境中运行此脚本${NC}"
    read -p "是否继续? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}已取消${NC}"
        exit 1
    fi
fi

# 检查必要的工具
echo -e "${YELLOW}检查必要的工具...${NC}"
if ! command -v twine &> /dev/null; then
    echo -e "${YELLOW}未找到twine，正在安装...${NC}"
    pip install twine
fi

if ! command -v build &> /dev/null; then
    echo -e "${YELLOW}未找到build，正在安装...${NC}"
    pip install build
fi

# 清理旧的构建文件
echo -e "${YELLOW}清理旧的构建文件...${NC}"
rm -rf build/ dist/ *.egg-info/

# 构建分发包
echo -e "${YELLOW}构建分发包...${NC}"
python -m build

# 检查分发包
echo -e "${YELLOW}检查分发包...${NC}"
twine check dist/*

if [ $? -ne 0 ]; then
    echo -e "${RED}分发包检查失败，请修复问题后重试${NC}"
    exit 1
fi

# 询问是否上传到TestPyPI
echo -e "${YELLOW}是否上传到TestPyPI进行测试? (y/n)${NC}"
read -p "" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}上传到TestPyPI...${NC}"
    twine upload --repository-url https://test.pypi.org/legacy/ dist/*
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}上传到TestPyPI失败${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}上传到TestPyPI成功!${NC}"
    echo -e "${YELLOW}测试安装:${NC}"
    echo -e "pip install --index-url https://test.pypi.org/simple/ llm-protection-system==${VERSION}"
    
    echo -e "${YELLOW}是否继续上传到正式PyPI? (y/n)${NC}"
    read -p "" -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}已取消上传到正式PyPI${NC}"
        exit 0
    fi
fi

# 上传到正式PyPI
echo -e "${YELLOW}上传到正式PyPI...${NC}"
echo -e "${YELLOW}请确认您已登录PyPI或已配置API令牌${NC}"
read -p "是否继续? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}已取消上传到正式PyPI${NC}"
    exit 0
fi

twine upload dist/*

if [ $? -ne 0 ]; then
    echo -e "${RED}上传到正式PyPI失败${NC}"
    exit 1
fi

echo -e "${GREEN}上传到正式PyPI成功!${NC}"
echo -e "${YELLOW}验证安装:${NC}"
echo -e "pip install llm-protection-system==${VERSION}"

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}PyPI发布完成!${NC}"
echo -e "${GREEN}=========================================${NC}"

# 发布后检查清单
echo -e "${YELLOW}发布后检查清单:${NC}"
echo -e "- [ ] 确认包可以通过pip安装"
echo -e "- [ ] 确认包的版本号正确"
echo -e "- [ ] 确认包的元数据（描述、作者、许可证等）正确"
echo -e "- [ ] 确认包的依赖项正确"
echo -e "- [ ] 确认包的文档链接有效"
echo -e "- [ ] 确认PyPI页面上的README正确显示"
