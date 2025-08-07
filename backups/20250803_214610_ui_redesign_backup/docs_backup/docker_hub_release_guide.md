# Docker Hub发布指南

本文档提供了将本地大模型防护系统发布到Docker Hub的详细步骤。

## 前提条件

1. 已安装Docker
2. 拥有Docker Hub账号
3. 已在本地登录Docker Hub：`docker login`

## 发布步骤

### 1. 准备Docker镜像

在项目根目录下构建Docker镜像：

```bash
docker build -t llm-protection-system:1.0.0 .
```

### 2. 测试Docker镜像

在本地测试Docker镜像是否正常工作：

```bash
docker run -d -p 8080:8080 --name llm-protection-test llm-protection-system:1.0.0
```

访问`http://localhost:8080`验证系统是否正常运行。

测试完成后停止并删除容器：

```bash
docker stop llm-protection-test
docker rm llm-protection-test
```

### 3. 标记Docker镜像

使用您的Docker Hub用户名标记镜像：

```bash
docker tag llm-protection-system:1.0.0 yourusername/llm-protection-system:1.0.0
docker tag llm-protection-system:1.0.0 yourusername/llm-protection-system:latest
```

### 4. 推送到Docker Hub

将镜像推送到Docker Hub：

```bash
docker push yourusername/llm-protection-system:1.0.0
docker push yourusername/llm-protection-system:latest
```

### 5. 验证发布

验证镜像是否已成功发布并可拉取：

```bash
docker pull yourusername/llm-protection-system:1.0.0
```

## 自动化发布脚本

为了简化发布过程，我们提供了一个自动化发布脚本：

```bash
./scripts/publish_to_docker_hub.sh yourusername
```

该脚本会自动执行上述所有步骤，包括构建、测试和推送。

## Docker Hub仓库设置

在Docker Hub上，建议为您的仓库配置以下内容：

1. **详细描述**：提供系统的简要描述和主要功能
2. **README**：链接到GitHub仓库的README或提供使用说明
3. **标签说明**：说明不同标签的用途（如latest、1.0.0等）
4. **构建设置**：配置自动构建（可选）

## 多架构支持

要支持多种CPU架构（如amd64、arm64等），可以使用Docker的buildx功能：

```bash
docker buildx create --name mybuilder --use
docker buildx build --platform linux/amd64,linux/arm64 -t yourusername/llm-protection-system:1.0.0 --push .
```

## 发布后检查清单

- [ ] 确认镜像可以通过`docker pull`拉取
- [ ] 确认镜像的标签正确
- [ ] 确认镜像的大小合理
- [ ] 确认Docker Hub页面上的描述和README正确显示
- [ ] 确认镜像可以正常运行

## 故障排除

### 常见问题

1. **推送失败**：确保您已登录Docker Hub并有权限推送到指定仓库
2. **构建错误**：检查Dockerfile是否正确配置
3. **运行错误**：检查容器日志以获取详细错误信息：`docker logs container_id`

### 有用的命令

- 查看本地镜像：`docker images`
- 删除本地镜像：`docker rmi image_id`
- 查看容器日志：`docker logs container_id`
- 进入运行中的容器：`docker exec -it container_id bash`

## 参考资源

- [Docker Hub官方文档](https://docs.docker.com/docker-hub/)
- [Docker Buildx文档](https://docs.docker.com/buildx/working-with-buildx/)
- [Docker多架构镜像指南](https://docs.docker.com/desktop/multi-arch/)
