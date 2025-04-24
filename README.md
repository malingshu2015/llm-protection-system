# 本地大模型防护系统 (Local LLM Protection System)

一个全面的安全防护系统，为本地部署的大型语言模型提供安全防护。

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)

## 功能特点

- **安全检测与防护**
  - 提示注入检测：识别和阻止各类提示注入攻击
  - 越狱尝试识别：检测绕过安全限制的行为
  - 敏感信息过滤：保护个人信息和敏感凭证
  - 有害内容检测：过滤不当内容

- **模型管理**
  - 模型发现与集成：支持Ollama等多种本地模型
  - 模型安全规则配置：为不同模型配置不同的安全规则
  - 模型访问控制：管理模型使用权限

- **监控与分析**
  - 实时监控：监控系统资源和请求统计
  - 安全事件管理：记录和分析安全事件
  - 性能分析：监控系统性能

- **用户界面**
  - 管理控制台：直观的Web界面
  - 聊天演示界面：用于测试和演示
  - 暗色模式支持：Apple风格界面设计

## 安装

### 使用pip安装

```bash
# 使用pip安装
# 注意：这将在未来发布到PyPI后可用
pip install llm-protection-system
```

### 从源代码安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/llm-protection-system.git
cd llm-protection-system

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate    # Windows

# 安装依赖
pip install -r requirements.txt

# 开发模式安装
pip install -e .
```

### 使用Docker

```bash
# 使用Docker运行
docker pull yourusername/llm-protection-system:1.0.0
docker run -p 8080:8080 yourusername/llm-protection-system:1.0.0
```

## 使用

### 启动服务

```bash
# 使用默认配置启动服务
llm-protection  # 如果使用pip安装

# 或者
python -m src.main  # 如果从源代码安装

# 指定端口和日志级别
python -m src.main --port 8080 --log-level debug
```

### 配置

可以通过环境变量或者`.env`文件进行配置：

```
# .env 文件示例
WEB_PORT=8080
WEB_HOST=0.0.0.0
LOG_LEVEL=INFO
DEBUG=false
```

### 访问管理界面

启动服务后，访问以下地址打开管理界面：

```
http://localhost:8080/static/admin/index.html
```

### 使用聊天演示

访问以下地址打开聊天演示界面：

```
http://localhost:8080/static/chat/index.html
```

## 开发

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_security/

# 带覆盖率报告
pytest --cov=src tests/
```

### 代码格式化

```bash
# 使用black格式化代码
black .

# 使用isort排序导入
isort .
```

### 代码检查

```bash
# 使用flake8检查代码风格
flake8

# 使用mypy进行类型检查
mypy .
```

### 构建包

```bash
# 构建源码分发包
python setup.py sdist

# 构建轮子分发包
python setup.py bdist_wheel
```

## 架构

本地大模型防护系统采用模块化设计，主要组件包括：

- **安全代理层**：拦截和处理所有进出大模型的请求和响应
- **安全检测模块**：提供多种安全检测功能
- **模型适配器**：适配不同大模型的API格式
- **事件管理系统**：记录和分析安全事件
- **Web界面**：提供图形化管理界面

更详细的架构图请参考[docs/llm_protection_system_architecture.md](docs/llm_protection_system_architecture.md)。

## 贡献

欢迎贡献代码、报告问题或提出新功能建议。请参考[CONTRIBUTING.md](CONTRIBUTING.md)了解贡献指南。

## 许可证

[MIT](LICENSE)
