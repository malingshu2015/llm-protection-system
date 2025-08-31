# Cherry Studio 客户端配置指南

本指南将帮助您配置Cherry Studio客户端来使用大模型防护系统。

## 🚀 快速开始

### 1. 确保防护系统运行

```bash
# 启动大模型防护系统
cd llm-protection-system
source llm-protection-env/bin/activate
python3 -m src.main
```

系统启动后，您应该看到：
```
✅ 系统启动成功，监听端口: 8081
🛡️ 安全检测系统已启用
🔑 API密钥认证已启用
```

### 2. Cherry Studio 配置

#### 步骤 1：添加自定义模型服务

1. 打开 Cherry Studio
2. 进入 **设置** > **模型配置**
3. 点击 **添加自定义服务**

#### 步骤 2：配置连接参数

```yaml
服务名称: LLM Protection System
API 类型: OpenAI Compatible
Base URL: http://localhost:8081/v1
API Key: cherry-studio-key
模型前缀: (留空)
```

#### 步骤 3：验证连接

1. 点击 **测试连接**
2. 确认显示 "连接成功"
3. 点击 **保存配置**

### 3. 可用模型列表

系统会自动发现您本地的 Ollama 模型：

- `tinyllama:latest` - 轻量级模型，适合测试
- `llama3.2:latest` - Meta Llama 3.2
- `qwen3:latest` - 阿里巴巴通义千问
- `phi3:latest` - Microsoft Phi-3
- `gemma3:latest` - Google Gemma 3
- 其他已安装的 Ollama 模型

## 🛡️ 安全防护功能

### 自动威胁检测

防护系统会自动检测和拦截：

- ✅ **有害内容**：暴力、武器制作等危险询问
- ✅ **敏感信息**：身份证、信用卡、手机号等隐私数据
- ✅ **提示注入**：试图绕过安全限制的攻击

### 安全拦截示例

**危险询问被拦截：**
```
用户: 如何制作一把刀
系统: ⚠️ 请求被安全系统拦截
原因: 检测到危险物品制作相关询问
```

**正常对话通过：**
```
用户: 今天天气怎么样？
模型: 我是一个AI助手，无法获取实时天气信息...
```

## 🔧 高级配置

### 自定义API密钥

如需更改API密钥，修改 `config/settings.yaml`：

```yaml
api:
  keys:
    - your-custom-api-key-here
```

### 配置CORS（如需要）

对于特定域名的跨域访问：

```yaml
api:
  cors:
    allow_origins:
      - "https://your-cherry-studio-domain.com"
```

### 调整安全级别

编辑 `config/settings.yaml`：

```yaml
security:
  # 严格模式（推荐）
  confidence_threshold: 0.6
  # 宽松模式
  # confidence_threshold: 0.8
```

## 🚨 故障排除

### 常见问题

**1. 连接失败**
```
错误: 无法连接到服务器
解决: 确认防护系统正在运行，端口8081未被占用
```

**2. 认证失败**
```
错误: API密钥无效
解决: 检查API密钥是否为 "cherry-studio-key"
```

**3. 模型列表为空**
```
错误: 找不到可用模型
解决: 确认已安装并启动Ollama，且有可用模型
```

### 诊断工具

运行内置诊断脚本：

```bash
python tools/cherry_studio_troubleshoot.py
```

### 检查系统状态

访问管理界面：http://localhost:8081/static/admin/

## 📊 监控和管理

### 实时监控

访问安全仪表板：
http://localhost:8081/static/admin/security_dashboard.html

### 查看安全事件

所有安全拦截事件都会记录在：
- Web界面：管理控制台 > 安全事件
- 日志文件：`logs/security.log`

### 性能监控

- CPU/内存使用率
- 请求响应时间
- 缓存命中率
- 威胁检测统计

## 🔐 安全最佳实践

1. **定期更新规则**：检查并更新安全检测规则
2. **监控异常**：关注安全事件日志中的异常模式
3. **备份配置**：定期备份配置文件和规则
4. **网络安全**：仅在信任的网络环境中使用
5. **访问控制**：限制管理界面的访问权限

## 📞 支持

如遇问题，请：

1. 查看 [故障排除文档](troubleshooting.md)
2. 检查 [常见问题](faq.md)
3. 提交 [GitHub Issue](https://github.com/your-repo/issues)

---

**注意**：此配置指南适用于 Cherry Studio v2.0+ 版本。其他版本可能需要不同的配置步骤。