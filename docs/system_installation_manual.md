# 🛠️ 大模型防火墙系统安装指南 v1.1.0

## 📋 系统要求

### 最低要求
- **操作系统**: Linux (Ubuntu 18.04+), macOS 10.14+, Windows 10+
- **Python版本**: Python 3.8+ 
- **内存**: 512MB RAM (建议1GB+)
- **存储空间**: 500MB 可用磁盘空间
- **网络**: 用于下载依赖包的网络连接

### 推荐配置
- **操作系统**: Ubuntu 20.04 LTS / macOS 12+ / Windows 11
- **Python版本**: Python 3.10+
- **内存**: 2GB+ RAM
- **存储空间**: 2GB+ 可用磁盘空间
- **处理器**: 双核 CPU

## 🚀 快速安装

### 方式一: GitHub 直接下载 (推荐)

```bash
# 1. 克隆仓库
git clone https://github.com/your-username/llm-protection-system.git
cd llm-protection-system

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 Windows:
# venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 启动系统
python -m src.main
```

### 方式二: Release 包下载

```bash
# 1. 下载最新Release包
wget https://github.com/your-username/llm-protection-system/archive/refs/tags/v1.1.0.tar.gz

# 2. 解压
tar -xzf v1.1.0.tar.gz
cd llm-protection-system-1.1.0

# 3. 安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. 启动系统
python -m src.main
```

## 📦 详细安装步骤

### Step 1: 环境准备

#### Linux/Ubuntu
```bash
# 更新系统包
sudo apt update

# 安装Python和必要工具
sudo apt install python3 python3-pip python3-venv git

# 验证安装
python3 --version
pip3 --version
```

#### macOS
```bash
# 安装Homebrew (如未安装)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装Python
brew install python3 git

# 验证安装
python3 --version
pip3 --version
```

#### Windows
1. 下载并安装 [Python 3.10+](https://www.python.org/downloads/)
2. 安装过程中选择"Add Python to PATH"
3. 安装 [Git for Windows](https://git-scm.com/download/win)
4. 验证安装：
```cmd
python --version
pip --version
git --version
```

### Step 2: 获取源码

```bash
# 方式1: Git克隆
git clone https://github.com/your-username/llm-protection-system.git

# 方式2: 下载ZIP包
# 访问 https://github.com/your-username/llm-protection-system/releases
# 下载最新版本的Source code (zip)
```

### Step 3: 创建隔离环境

```bash
cd llm-protection-system

# 创建Python虚拟环境
python3 -m venv llm-protection-env

# 激活虚拟环境
# Linux/macOS:
source llm-protection-env/bin/activate

# Windows:
llm-protection-env\Scripts\activate

# 验证环境
which python  # 应显示虚拟环境路径
```

### Step 4: 安装依赖

```bash
# 升级pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 验证关键组件安装
python -c "import fastapi, uvicorn, aiohttp; print('依赖安装成功!')"
```

### Step 5: 配置系统

```bash
# 复制环境配置文件
cp .env.example .env

# 编辑配置文件 (可选)
nano .env  # 或使用其他编辑器
```

**.env 配置说明:**
```env
# 服务配置
SERVER_HOST=127.0.0.1
SERVER_PORT=8081

# Ollama配置
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT=30

# API密钥配置
API_KEY=cherry-studio-key

# 安全配置
DEVELOPMENT_MODE=true
BYPASS_DETECTION_FOR_DEV=false
CONFIDENCE_THRESHOLD=0.6

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/system.log
```

### Step 6: 启动系统

```bash
# 启动大模型防火墙
python -m src.main

# 或使用开发模式 (自动重载)
python -m src.main --reload
```

**启动成功标志:**
```
🚀 大模型防护系统已启动
📊 监控中心: http://127.0.0.1:8081/static/admin/
🔗 API 文档: http://127.0.0.1:8081/docs
```

## 🔧 配置指南

### 1. Ollama集成配置

```bash
# 安装Ollama (如未安装)
curl -fsSL https://ollama.com/install.sh | sh

# 启动Ollama服务
ollama serve

# 拉取测试模型
ollama pull llama3.2:1b
```

### 2. 第三方客户端配置

#### Cherry Studio 配置
```json
{
  "server_url": "http://127.0.0.1:8081/v1",
  "api_key": "cherry-studio-key",
  "model": "llama3.2:1b"
}
```

#### Open WebUI 配置
```env
OPENAI_API_BASE_URL=http://127.0.0.1:8081/v1
OPENAI_API_KEY=cherry-studio-key
```

### 3. 安全规则配置

访问管理界面配置安全规则:
- **规则管理**: `http://127.0.0.1:8081/static/admin/rules.html`
- **模型配置**: `http://127.0.0.1:8081/static/admin/model_rules.html`
- **实时监控**: `http://127.0.0.1:8081/static/admin/realtime_monitor.html`

## 🐛 常见问题

### 问题1: 端口被占用
```bash
# 检查端口占用
netstat -tulpn | grep :8081

# 杀死占用进程
kill -9 <进程ID>

# 或修改端口
export SERVER_PORT=8082
```

### 问题2: 依赖安装失败
```bash
# 清理pip缓存
pip cache purge

# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

### 问题3: Ollama连接失败
```bash
# 检查Ollama状态
curl http://localhost:11434/api/tags

# 重启Ollama
sudo systemctl restart ollama
```

### 问题4: 权限错误
```bash
# Linux/macOS权限修复
chmod +x scripts/*.sh
sudo chown -R $USER:$USER logs/

# Windows权限修复
# 以管理员身份运行命令提示符
```

## 🔄 更新升级

### 版本检查
```bash
# 查看当前版本
python -c "from src.config import APP_VERSION; print(APP_VERSION)"

# 检查远程版本
git fetch --tags
git tag -l | sort -V | tail -5
```

### 升级到最新版本
```bash
# 备份配置
cp .env .env.backup
cp -r data/ data_backup/

# 获取最新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt --upgrade

# 重启服务
python -m src.main
```

## 🏗️ 生产部署

### Docker部署 (推荐)
```bash
# 构建镜像
docker build -t llm-protection-system .

# 运行容器
docker run -d \
  --name llm-firewall \
  -p 8081:8081 \
  -v ./data:/app/data \
  -v ./logs:/app/logs \
  llm-protection-system
```

### Systemd服务 (Linux)
```bash
# 创建服务文件
sudo tee /etc/systemd/system/llm-protection.service > /dev/null <<EOF
[Unit]
Description=LLM Protection System
After=network.target

[Service]
Type=simple
User=llm-user
WorkingDirectory=/opt/llm-protection-system
Environment=PATH=/opt/llm-protection-system/venv/bin
ExecStart=/opt/llm-protection-system/venv/bin/python -m src.main
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 启用服务
sudo systemctl enable llm-protection.service
sudo systemctl start llm-protection.service
```

## 📊 验证安装

### 健康检查
```bash
# 检查服务状态
curl http://127.0.0.1:8081/health

# 检查API接口
curl -H "Authorization: Bearer cherry-studio-key" \
     http://127.0.0.1:8081/v1/models

# 测试安全检测
curl -X POST "http://127.0.0.1:8081/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer cherry-studio-key" \
  -d '{
    "model": "llama3.2:1b",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

### 访问管理界面
- **主页**: http://127.0.0.1:8081/static/admin/
- **监控中心**: http://127.0.0.1:8081/static/admin/monitor.html
- **实时监控**: http://127.0.0.1:8081/static/admin/realtime_monitor.html
- **规则管理**: http://127.0.0.1:8081/static/admin/rules.html
- **API文档**: http://127.0.0.1:8081/docs

## 📞 技术支持

- **GitHub Issues**: [项目问题反馈](https://github.com/your-username/llm-protection-system/issues)
- **文档**: [在线文档](https://github.com/your-username/llm-protection-system/wiki)
- **更新日志**: [CHANGELOG.md](../CHANGELOG.md)

---

*安装过程中如有问题，请查看日志文件 `logs/system.log` 获取详细错误信息。*