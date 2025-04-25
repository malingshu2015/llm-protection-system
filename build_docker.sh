#!/bin/bash
# Docker 构建脚本

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
echo -e "${GREEN}本地大模型防护系统 Docker 构建工具 v${VERSION}${NC}"
echo -e "${GREEN}=========================================${NC}"

# 检查 Docker 是否已安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker 未安装。请先安装 Docker。${NC}"
    exit 1
fi

# 检查 Docker 守护进程是否运行
if ! docker info &> /dev/null; then
    echo -e "${RED}错误: Docker 守护进程未运行。请先启动 Docker。${NC}"
    exit 1
fi

# 构建 Docker 镜像
echo -e "${YELLOW}开始构建 Docker 镜像...${NC}"
docker build -t llm-protection-system:${VERSION} .

# 检查构建结果
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Docker 镜像构建成功!${NC}"
    
    # 标记最新版本
    echo -e "${YELLOW}标记最新版本...${NC}"
    docker tag llm-protection-system:${VERSION} llm-protection-system:latest
    
    # 显示镜像信息
    echo -e "${YELLOW}Docker 镜像信息:${NC}"
    docker images | grep llm-protection-system
    
    # 创建运行脚本
    echo -e "${YELLOW}创建运行脚本...${NC}"
    cat > run_docker.sh << EOF
#!/bin/bash
# 运行 Docker 容器

# 创建数据目录
mkdir -p data logs rules

# 运行容器
docker run -d \\
    --name llm-protection-system \\
    -p 8080:8080 \\
    -v \$(pwd)/data:/app/data \\
    -v \$(pwd)/logs:/app/logs \\
    -v \$(pwd)/rules:/app/rules \\
    -e LOG_LEVEL=INFO \\
    -e DEBUG=false \\
    -e WEB_PORT=8080 \\
    -e WEB_HOST=0.0.0.0 \\
    llm-protection-system:${VERSION}

echo "容器已启动，访问 http://localhost:8080 查看应用"
EOF
    chmod +x run_docker.sh
    
    echo -e "${GREEN}运行脚本已创建: run_docker.sh${NC}"
    echo -e "${YELLOW}使用以下命令运行容器:${NC}"
    echo -e "  ./run_docker.sh"
    
    # 创建 Docker Compose 文件
    echo -e "${YELLOW}创建 Docker Compose 文件...${NC}"
    cat > docker-compose.yml << EOF
version: '3'

services:
  llm-protection:
    image: llm-protection-system:${VERSION}
    container_name: llm-protection-system
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./rules:/app/rules
    environment:
      - LOG_LEVEL=INFO
      - DEBUG=false
      - WEB_PORT=8080
      - WEB_HOST=0.0.0.0
    restart: unless-stopped
    networks:
      - llm-network

networks:
  llm-network:
    driver: bridge
EOF
    
    echo -e "${GREEN}Docker Compose 文件已创建: docker-compose.yml${NC}"
    echo -e "${YELLOW}使用以下命令运行容器:${NC}"
    echo -e "  docker-compose up -d"
    
    # 创建推送脚本
    echo -e "${YELLOW}创建推送脚本...${NC}"
    cat > push_docker.sh << EOF
#!/bin/bash
# 推送 Docker 镜像到 Docker Hub

# 设置 Docker Hub 用户名
DOCKER_HUB_USERNAME="\$1"

if [ -z "\$DOCKER_HUB_USERNAME" ]; then
    echo "错误: 请提供 Docker Hub 用户名"
    echo "用法: ./push_docker.sh <Docker Hub 用户名>"
    exit 1
fi

# 登录 Docker Hub
echo "登录 Docker Hub..."
docker login

# 标记镜像
echo "标记镜像..."
docker tag llm-protection-system:${VERSION} \$DOCKER_HUB_USERNAME/llm-protection-system:${VERSION}
docker tag llm-protection-system:${VERSION} \$DOCKER_HUB_USERNAME/llm-protection-system:latest

# 推送镜像
echo "推送镜像..."
docker push \$DOCKER_HUB_USERNAME/llm-protection-system:${VERSION}
docker push \$DOCKER_HUB_USERNAME/llm-protection-system:latest

echo "镜像已推送到 Docker Hub"
EOF
    chmod +x push_docker.sh
    
    echo -e "${GREEN}推送脚本已创建: push_docker.sh${NC}"
    echo -e "${YELLOW}使用以下命令推送镜像到 Docker Hub:${NC}"
    echo -e "  ./push_docker.sh <Docker Hub 用户名>"
    
    echo -e "${GREEN}=========================================${NC}"
    echo -e "${GREEN}Docker 构建完成!${NC}"
    echo -e "${GREEN}=========================================${NC}"
else
    echo -e "${RED}Docker 镜像构建失败!${NC}"
    exit 1
fi
