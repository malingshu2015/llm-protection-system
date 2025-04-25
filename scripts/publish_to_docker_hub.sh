#!/bin/bash
# Docker Hub发布脚本

# 设置颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查参数
if [ $# -lt 1 ]; then
    echo -e "${RED}错误: 缺少Docker Hub用户名参数${NC}"
    echo -e "用法: $0 <Docker Hub用户名> [镜像名称]"
    exit 1
fi

DOCKER_HUB_USERNAME="$1"
IMAGE_NAME="${2:-llm-protection-system}"

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
echo -e "${GREEN}本地大模型防护系统 Docker Hub 发布工具 v${VERSION}${NC}"
echo -e "${GREEN}=========================================${NC}"

# 检查Docker是否已安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}错误: Docker未安装${NC}"
    exit 1
fi

# 检查Docker守护进程是否运行
if ! docker info &> /dev/null; then
    echo -e "${RED}错误: Docker守护进程未运行${NC}"
    exit 1
fi

# 检查Docker Hub登录状态
echo -e "${YELLOW}检查Docker Hub登录状态...${NC}"
if ! docker info | grep -q "Username: $DOCKER_HUB_USERNAME"; then
    echo -e "${YELLOW}未登录Docker Hub，请登录...${NC}"
    docker login
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}登录Docker Hub失败${NC}"
        exit 1
    fi
fi

# 构建Docker镜像
echo -e "${YELLOW}构建Docker镜像...${NC}"
docker build -t $IMAGE_NAME:$VERSION .

if [ $? -ne 0 ]; then
    echo -e "${RED}构建Docker镜像失败${NC}"
    exit 1
fi

# 测试Docker镜像
echo -e "${YELLOW}测试Docker镜像...${NC}"
echo -e "${YELLOW}启动测试容器...${NC}"
CONTAINER_ID=$(docker run -d -p 8080:8080 --name llm-protection-test $IMAGE_NAME:$VERSION)

if [ $? -ne 0 ]; then
    echo -e "${RED}启动测试容器失败${NC}"
    exit 1
fi

echo -e "${YELLOW}等待容器启动...${NC}"
sleep 5

echo -e "${YELLOW}检查容器状态...${NC}"
CONTAINER_STATUS=$(docker inspect -f '{{.State.Status}}' llm-protection-test)

if [ "$CONTAINER_STATUS" != "running" ]; then
    echo -e "${RED}容器未正常运行，状态: $CONTAINER_STATUS${NC}"
    echo -e "${YELLOW}容器日志:${NC}"
    docker logs llm-protection-test
    docker rm -f llm-protection-test
    exit 1
fi

echo -e "${GREEN}容器运行正常!${NC}"
echo -e "${YELLOW}停止并删除测试容器...${NC}"
docker stop llm-protection-test
docker rm llm-protection-test

# 标记Docker镜像
echo -e "${YELLOW}标记Docker镜像...${NC}"
docker tag $IMAGE_NAME:$VERSION $DOCKER_HUB_USERNAME/$IMAGE_NAME:$VERSION
docker tag $IMAGE_NAME:$VERSION $DOCKER_HUB_USERNAME/$IMAGE_NAME:latest

# 询问是否推送到Docker Hub
echo -e "${YELLOW}是否推送到Docker Hub? (y/n)${NC}"
read -p "" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}已取消推送到Docker Hub${NC}"
    exit 0
fi

# 推送到Docker Hub
echo -e "${YELLOW}推送到Docker Hub...${NC}"
docker push $DOCKER_HUB_USERNAME/$IMAGE_NAME:$VERSION
docker push $DOCKER_HUB_USERNAME/$IMAGE_NAME:latest

if [ $? -ne 0 ]; then
    echo -e "${RED}推送到Docker Hub失败${NC}"
    exit 1
fi

echo -e "${GREEN}推送到Docker Hub成功!${NC}"
echo -e "${YELLOW}验证拉取:${NC}"
echo -e "docker pull $DOCKER_HUB_USERNAME/$IMAGE_NAME:$VERSION"

# 询问是否构建多架构镜像
echo -e "${YELLOW}是否构建并推送多架构镜像? (y/n)${NC}"
read -p "" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}创建并使用buildx构建器...${NC}"
    docker buildx create --name mybuilder --use
    
    echo -e "${YELLOW}构建并推送多架构镜像...${NC}"
    docker buildx build --platform linux/amd64,linux/arm64 \
        -t $DOCKER_HUB_USERNAME/$IMAGE_NAME:$VERSION \
        -t $DOCKER_HUB_USERNAME/$IMAGE_NAME:latest \
        --push .
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}构建并推送多架构镜像失败${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}构建并推送多架构镜像成功!${NC}"
fi

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}Docker Hub发布完成!${NC}"
echo -e "${GREEN}=========================================${NC}"

# 发布后检查清单
echo -e "${YELLOW}发布后检查清单:${NC}"
echo -e "- [ ] 确认镜像可以通过docker pull拉取"
echo -e "- [ ] 确认镜像的标签正确"
echo -e "- [ ] 确认镜像的大小合理"
echo -e "- [ ] 确认Docker Hub页面上的描述和README正确显示"
echo -e "- [ ] 确认镜像可以正常运行"
