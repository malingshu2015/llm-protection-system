#!/bin/bash
# macOS 平台构建脚本

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
echo -e "${GREEN}本地大模型防护系统 macOS 构建工具 v${VERSION}${NC}"
echo -e "${GREEN}=========================================${NC}"

# 检查 Python 版本
echo -e "${YELLOW}检查 Python 版本...${NC}"
PYTHON_VERSION=$(python3 --version)
echo "当前 Python 版本: $PYTHON_VERSION"

# 检查虚拟环境
if [ -d "venv_py39" ]; then
    echo -e "${YELLOW}使用现有的虚拟环境 venv_py39...${NC}"
    source venv_py39/bin/activate
else
    echo -e "${YELLOW}创建新的虚拟环境 venv_py39...${NC}"
    python3 -m venv venv_py39
    source venv_py39/bin/activate
fi

# 安装依赖项
echo -e "${YELLOW}安装依赖项...${NC}"
pip install -r requirements.txt
pip install pyinstaller

# 清理构建目录
echo -e "${YELLOW}清理构建目录...${NC}"
rm -rf build dist

# 构建应用程序
echo -e "${YELLOW}开始构建 macOS 应用程序...${NC}"
pyinstaller macos.spec --clean

# 检查构建结果
if [ -d "dist/本地大模型防护系统.app" ]; then
    echo -e "${GREEN}应用程序构建成功!${NC}"

    # 创建分发包
    echo -e "${YELLOW}创建分发包...${NC}"
    TIMESTAMP=$(date +"%Y%m%d")
    DIST_NAME="llm-protection-system-${VERSION}-macos-$(uname -m)-${TIMESTAMP}"
    DIST_DIR="${PROJECT_ROOT}/${DIST_NAME}"

    # 创建分发目录
    mkdir -p "${DIST_DIR}"

    # 复制应用程序
    cp -R "dist/本地大模型防护系统.app" "${DIST_DIR}/"

    # 创建启动脚本
    cat > "${DIST_DIR}/start.sh" << EOF
#!/bin/bash
open "本地大模型防护系统.app"
EOF
    chmod +x "${DIST_DIR}/start.sh"

    # 复制文档
    cp README.md "${DIST_DIR}/"
    if [ -f "LICENSE" ]; then
        cp LICENSE "${DIST_DIR}/"
    fi

    # 创建文档目录
    mkdir -p "${DIST_DIR}/docs"

    # 复制文档文件
    for doc_file in docs/*.md; do
        if [ -f "$doc_file" ]; then
            cp "$doc_file" "${DIST_DIR}/docs/"
        fi
    done

    # 创建压缩包
    tar -czf "${DIST_NAME}.tar.gz" -C "${PROJECT_ROOT}" "${DIST_NAME}"

    # 删除临时目录
    rm -rf "${DIST_DIR}"

    echo -e "${GREEN}分发包已创建: ${DIST_NAME}.tar.gz${NC}"
else
    echo -e "${RED}构建失败!${NC}"
    exit 1
fi

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}构建完成!${NC}"
echo -e "${GREEN}=========================================${NC}"
