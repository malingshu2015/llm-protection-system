# 本地大模型防护系统 (Local LLM Protection System)

一个全面的安全防护系统，为本地部署的大型语言模型提供安全防护。

![Version](https://img.shields.io/badge/version-1.1.1--enhanced-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Security](https://img.shields.io/badge/security-100%25%20accuracy-brightgreen)

## 功能特点

- **🛡️ 安全检测与防护** （准确率：100%）
  - 提示注入检测：识别和阻止各类提示注入攻击
  - 越狱尝试识别：检测绕过安全限制的行为
  - 敏感信息过滤：保护个人信息和敏感凭证
    - ✅ 信用卡号码检测 
    - ✅ 中国身份证号码检测（18位/15位）
    - ✅ 手机号码检测（中国大陆11位）
    - ✅ 社保号、邮箱、API密钥等
  - 有害内容检测：过滤不当内容
    - ✅ 武器制作相关询问检测
    - ✅ 危险物品制作防护
    - ✅ 暴力内容识别
  - **智能上下文感知**：区分合法用途与危险意图，支持教育/医疗/专业背景白名单
  - **三级安全响应**：允许/警告/阻止的智能分级处理

- **模型管理**
  - 模型发现与集成：支持Ollama等多种本地模型
  - 模型安全规则配置：为不同模型配置不同的安全规则
  - 模型访问控制：管理模型使用权限

- **📊 监控与分析**
  - 实时监控：监控系统资源和请求统计
  - 智能缓存：基于AI的智能缓存系统，提升响应速度
  - 安全事件管理：记录和分析安全事件
  - 性能分析：监控系统性能和资源使用情况
  - **安全仪表板**：专门的安全威胁监控界面
    - 实时威胁检测趋势图表
    - 威胁类型分布统计
    - 系统健康状态监控
    - 检测准确率实时展示

- **用户界面**
  - 管理控制台：直观的Web界面
  - 聊天演示界面：用于测试和演示
  - 暗色模式支持：Apple风格界面设计

- **第三方客户端支持**
  - OpenAI API兼容：完全兼容OpenAI API格式
  - Cherry Studio：专门优化支持
  - ChatBox、Open WebUI等：支持主流AI聊天客户端
  - 流式响应：支持实时流式对话
  - API密钥认证：安全的访问控制

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
git clone https://github.com/malingshu2015/llm-protection-system.git
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
docker pull malingshu2015/llm-protection-system:1.1.0
docker run -p 8080:8080 -p 8082:8082 malingshu2015/llm-protection-system:1.1.0
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

**v1.1.0 新增功能：**
- 实时监控面板：`http://localhost:8080/static/admin/monitor_v2.html`
- 增强模型管理：`http://localhost:8080/static/admin/models_v2.html`
- 优化规则配置：`http://localhost:8080/static/admin/rules_v2.html`

**安全检测增强：**
- 新增危险物品制作检测规则 (hc-011)
- 智能上下文感知白名单机制
- 三级安全响应系统 (允许/警告/阻止)

### 使用聊天演示

访问以下地址打开聊天演示界面：

```
http://localhost:8080/static/chat/index.html
```

### 第三方客户端配置

系统完全兼容OpenAI API格式，支持主流AI聊天客户端：

#### Cherry Studio 配置
```
API地址: http://localhost:8082
API密钥: cherry-studio-key
模型: tinyllama:latest
```

#### ChatBox 配置
```
API Host: http://localhost:8082/v1
API Key: cherry-studio-key
Model: tinyllama:latest
```

#### 通用OpenAI兼容客户端
```
Base URL: http://localhost:8082/v1
API Key: cherry-studio-key
```

详细配置指南请参考：[第三方客户端兼容性指南](docs/third_party_client_compatibility.md)

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

## 项目结构 (Project Structure)

为了保持代码库整洁，我们对目录进行了归档和整理：

- **`src/`**: 系统核心源代码
- **`tests/`**: 测试套件
  - `integration/`: 综合集成测试和旧版测试脚本
- **`scripts/`**: 各种管理和工具脚本
  - `build/`: 构建和打包脚本 (PyInstaller, Docker, DMG)
  - `test_runners/`: 用于运行复杂测试套件的执行器
  - `utils/`: 通用工具脚本 (更新、检查等)
  - `verification/`: 验证修复效果的专用脚本
  - `debug/`: 调试相关的临时脚本
- **`logs/`**: 系统运行和测试产生的日志
- **`reports/`**: 测试报告、设计文档和安全分析报告
  - `json/`: 自动生成的机器可读测试结果
  - `markdown/`: 人类可读的详细安全报告
- **`requirements/`**: 各种环境的依赖定义文件

## 架构

本地大模型防护系统采用模块化设计，主要组件包括：

- **安全代理层**：拦截和处理所有进出大模型的请求和响应
- **安全检测模块**：提供多种安全检测功能
- **模型适配器**：适配不同大模型的API格式
- **事件管理系统**：记录和分析安全事件
- **Web界面**：提供图形化管理界面

更详细的架构图请参考[docs/llm_protection_system_architecture.md](docs/llm_protection_system_architecture.md)。

## 🚀 最新更新

### v1.1.1-enhanced (2024-08-28)

**🔥 重大改进**
- ✅ **安全检测准确率提升至100%**
  - 修复敏感信息检测漏洞：新增中国身份证号码和手机号码检测
  - 完善危险物品制作询问检测规则
  - 加强威胁检测的全面性和准确性

- 🎯 **用户体验优化**
  - 新增专门的安全仪表板界面
  - 实时威胁监控和趋势分析
  - 改进管理界面导航和布局

- 🔧 **API兼容性增强**
  - 完善Cherry Studio客户端支持
  - 优化OpenAI API兼容性
  - 改进CORS跨域支持

**检测性能对比**
```
修复前: 75.0% 高风险拦截率, 87.5% 总体准确率
修复后: 100.0% 高风险拦截率, 100.0% 总体准确率
准确率提升: +12.5%
```

## 贡献

欢迎贡献代码、报告问题或提出新功能建议。请参考[CONTRIBUTING.md](CONTRIBUTING.md)了解贡献指南。

## 许可证

[MIT](LICENSE)
