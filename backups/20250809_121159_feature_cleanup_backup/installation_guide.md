# 本地大模型防护系统安装指南

**版本**: 1.0.0  
**更新日期**: 2025-04-25

## 目录

1. [系统要求](#系统要求)
2. [安装方式概述](#安装方式概述)
3. [Python包安装](#python包安装)
4. [Docker容器安装](#docker容器安装)
5. [Windows安装](#windows安装)
6. [macOS安装](#macos安装)
7. [Linux安装](#linux安装)
8. [配置说明](#配置说明)
9. [验证安装](#验证安装)
10. [常见问题](#常见问题)
11. [获取帮助](#获取帮助)

## 系统要求

### 最低硬件要求

- **CPU**: 双核处理器，2.0GHz或更高
- **内存**: 4GB RAM（推荐8GB或更高）
- **存储空间**: 500MB可用空间
- **网络**: 互联网连接（用于初始安装和模型下载）

### 软件要求

- **操作系统**:
  - Windows 10/11 (64位)
  - macOS 11.0或更高版本
  - Ubuntu 20.04/22.04 LTS, CentOS 8, Debian 11或其他主流Linux发行版
- **依赖软件**:
  - Python 3.9或更高版本（Python包安装方式）
  - Docker 20.10或更高版本（Docker安装方式）

## 安装方式概述

本地大模型防护系统提供多种安装方式，您可以根据自己的需求和环境选择最适合的方式：

1. **Python包安装**: 通过pip安装Python包，适合开发人员和熟悉Python的用户
2. **Docker容器安装**: 通过Docker运行容器化应用，适合需要隔离环境或快速部署的用户
3. **可执行文件安装**: 提供Windows、macOS和Linux平台的可执行文件，适合普通用户

## Python包安装

### 使用pip安装

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装本地大模型防护系统
pip install local-llm-protection-system
```

### 从源代码安装

```bash
# 克隆代码仓库
git clone https://github.com/yourusername/local-llm-protection-system.git
cd local-llm-protection-system

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装包
pip install -e .
```

## Docker容器安装

### 使用预构建镜像

```bash
# 拉取最新镜像
docker pull yourusername/local-llm-protection-system:latest

# 运行容器
docker run -d -p 8080:8080 --name llm-protection yourusername/local-llm-protection-system:latest
```

### 使用Docker Compose

1. 创建`docker-compose.yml`文件：

```yaml
version: '3'
services:
  llm-protection:
    image: yourusername/local-llm-protection-system:latest
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
    environment:
      - ENVIRONMENT=production
```

2. 启动服务：

```bash
docker-compose up -d
```

## Windows安装

1. 从[官方网站](https://example.com/download)或[GitHub Releases](https://github.com/yourusername/local-llm-protection-system/releases)下载最新的Windows安装程序(`.exe`)
2. 双击安装程序并按照向导指引完成安装
3. 安装完成后，可以从开始菜单启动应用程序

## macOS安装

1. 从[官方网站](https://example.com/download)或[GitHub Releases](https://github.com/yourusername/local-llm-protection-system/releases)下载最新的macOS安装包(`.dmg`)
2. 打开DMG文件，将应用程序拖到Applications文件夹
3. 首次运行时，可能需要在"系统偏好设置 > 安全性与隐私"中允许运行

## Linux安装

### Debian/Ubuntu

```bash
# 下载DEB包
wget https://example.com/download/local-llm-protection-system_1.0.0_amd64.deb

# 安装
sudo dpkg -i local-llm-protection-system_1.0.0_amd64.deb
sudo apt-get install -f  # 安装依赖
```

### RHEL/CentOS/Fedora

```bash
# 下载RPM包
wget https://example.com/download/local-llm-protection-system-1.0.0.x86_64.rpm

# 安装
sudo rpm -i local-llm-protection-system-1.0.0.x86_64.rpm
```

## 配置说明

安装完成后，您需要进行一些基本配置才能开始使用本地大模型防护系统。

### 配置文件位置

- **Python包安装**: `~/.config/local-llm-protection-system/config.yaml`
- **Docker容器**: `/app/config/config.yaml`（可通过卷挂载修改）
- **Windows安装**: `C:\Program Files\Local LLM Protection System\config\config.yaml`
- **macOS安装**: `/Applications/Local LLM Protection System.app/Contents/Resources/config/config.yaml`
- **Linux安装**: `/etc/local-llm-protection-system/config.yaml`

### 基本配置示例

```yaml
# 基本设置
server:
  host: 0.0.0.0
  port: 8080
  debug: false

# 数据存储
data:
  dir: ./data
  log_level: info

# 安全规则
security:
  default_rules: true
  custom_rules_dir: ./rules

# Ollama集成
ollama:
  host: localhost
  port: 11434
  timeout: 30
```

## 验证安装

安装完成后，您可以通过以下步骤验证系统是否正常工作：

1. 启动本地大模型防护系统：
   - **Python包**: 运行`llm-protection-system start`
   - **Docker**: 容器已自动启动
   - **桌面应用**: 从应用程序菜单启动

2. 打开Web浏览器，访问`http://localhost:8080`

3. 您应该能看到系统的登录页面或仪表盘

4. 使用默认凭据登录（首次登录后请修改密码）：
   - 用户名: `admin`
   - 密码: `admin`

## 常见问题

### 安装后无法启动服务

**问题**: 安装完成后，服务无法正常启动。

**解决方案**:
- 检查日志文件（位于数据目录下的`logs`文件夹）
- 确认系统满足最低要求
- 检查配置文件是否正确
- 确认端口8080未被其他应用占用

### 无法连接到Ollama

**问题**: 系统报错无法连接到Ollama服务。

**解决方案**:
- 确认Ollama已安装并正在运行
- 检查Ollama服务地址和端口配置
- 确认网络连接正常
- 检查防火墙设置

### 权限问题

**问题**: 在Linux或macOS上遇到权限错误。

**解决方案**:
- 确保应用程序有权访问配置和数据目录
- 检查日志目录的写入权限
- 可能需要使用`sudo`运行或调整目录权限

## 获取帮助

如果您在安装过程中遇到问题，可以通过以下渠道获取帮助：

- **文档**: 查阅[完整文档](https://example.com/docs)
- **GitHub Issues**: 在[GitHub仓库](https://github.com/yourusername/local-llm-protection-system/issues)提交问题
- **社区论坛**: 访问[用户社区](https://example.com/community)
- **电子邮件**: 联系支持团队 support@example.com

---

本文档最后更新于2025年4月25日。请访问[官方文档](https://example.com/docs/installation)获取最新版本。
