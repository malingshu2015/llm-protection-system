# ChatWise 客户端配置指南

## 📋 概述

本指南将帮助您配置ChatWise客户端连接到本地大模型防火墙系统，确保安全、稳定的AI对话体验。

## 🔑 可用API密钥

系统已为ChatWise客户端预配置了以下API密钥：

### 主推荐密钥
```
chatwise-key
```
- **用途**: ChatWise客户端专用
- **权限**: chat, models
- **速率限制**: 100次/分钟
- **最大客户端数**: 50个
- **描述**: 推荐用于ChatWise客户端的官方密钥

### 兼容性密钥
```
api_key_123456
```
- **用途**: 为了兼容您当前使用的密钥格式
- **权限**: chat, models  
- **速率限制**: 100次/分钟
- **最大客户端数**: 50个
- **描述**: 兼容api_key_开头格式的密钥

### 其他可用密钥
```
cherry-studio-key     # 通用客户端密钥
chatbox-key          # ChatBox兼容密钥
demo-key-12345       # 演示和测试密钥
```

## ⚙️ ChatWise 配置步骤

### 1. 基本连接配置

在ChatWise客户端中设置以下参数：

**API基础地址:**
```
http://localhost:8082/v1
```

**注意**: 如果您之前配置的是8081端口，请更新为8082端口。

**API密钥 (选择其一):**
```
chatwise-key
```
或
```
api_key_123456
```

**模型名称 (可选择):**
- `qwen3:latest` (推荐 - 中文优化)
- `phi3:latest` (轻量级)
- `llama3.2:latest` (英文优化)
- `tinyllama:latest` (超轻量级测试)
- `gemma3:latest` (Google模型)
- `deepseek-r1:14b` (推理专用)

### 2. 请求头配置

确保ChatWise客户端发送以下HTTP头：

```http
Authorization: Bearer chatwise-key
Content-Type: application/json
```

### 3. 请求格式示例

```json
{
  "model": "qwen3:latest",
  "messages": [
    {
      "role": "user", 
      "content": "你好，这是测试消息"
    }
  ],
  "stream": false
}
```

## 🧪 连接测试

### 使用curl测试连接

```bash
# 测试chatwise-key
curl -X POST "http://localhost:8082/v1/chat/completions" \
  -H "Authorization: Bearer chatwise-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:latest",
    "messages": [{"role": "user", "content": "Hello from ChatWise"}],
    "stream": false
  }'

# 测试api_key_123456  
curl -X POST "http://localhost:8082/v1/chat/completions" \
  -H "Authorization: Bearer api_key_123456" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:latest", 
    "messages": [{"role": "user", "content": "测试连接"}],
    "stream": false
  }'
```

### 验证模型列表

```bash
curl -H "Authorization: Bearer chatwise-key" \
  http://localhost:8082/v1/models
```

## 🚀 性能优化建议

### 1. 模型选择
- **日常对话**: `qwen3:latest` (中文优化，响应质量高)
- **快速响应**: `tinyllama:latest` (响应速度快，资源占用少)
- **英文对话**: `llama3.2:latest` (英文表现出色)

### 2. 请求优化
- 使用非流式响应 (`"stream": false`) 可获得更稳定的连接
- 控制消息长度，避免过长的上下文
- 建议单次对话控制在2000字符以内

### 3. 并发限制
- 每个API密钥最多支持50个并发客户端
- 速率限制为100次/分钟
- 建议实现请求重试机制

## 🔧 故障排除

### 常见错误及解决方案

#### 1. "无效的API密钥" (403 Forbidden)
**原因**: API密钥不正确或不存在
**解决方案**: 
- 确认使用的是 `chatwise-key` 或 `api_key_123456`
- 检查Authorization头格式: `Bearer <api_key>`

#### 2. 连接超时
**原因**: 防火墙系统未启动或端口被占用
**解决方案**:
- 确认防火墙系统在 http://localhost:8082 正常运行
- 检查端口8082是否被其他程序占用

#### 3. 模型不可用
**原因**: 请求的模型未安装或服务异常
**解决方案**:
- 使用 `/v1/models` 接口查看可用模型列表
- 选择状态为available的模型

#### 4. 速率限制 (429 Too Many Requests)
**原因**: 超出API调用频率限制
**解决方案**:
- 降低请求频率到100次/分钟以下
- 实现指数退避重试机制

## 📊 监控和日志

### 1. 系统监控
访问管理界面查看实时状态:
```
http://localhost:8082/static/admin/index.html
```

### 2. API状态检查
```bash
curl http://localhost:8082/health
```

### 3. 实时监控
```
http://localhost:8082/static/admin/monitor.html
```

## 🔒 安全注意事项

1. **API密钥安全**
   - 不要在公共代码仓库中硬编码API密钥
   - 使用环境变量或配置文件存储密钥
   - 定期轮换API密钥

2. **网络安全**
   - 确保防火墙系统在安全的网络环境中运行
   - 考虑使用HTTPS(需要配置SSL证书)
   - 限制访问来源IP(如需要)

3. **数据保护**
   - 敏感对话内容将被系统安全检测
   - 系统会记录请求日志用于监控和故障排除
   - 不会永久存储对话内容

## 📞 技术支持

如果遇到问题，请按以下步骤操作：

1. **检查系统状态**: 访问 http://localhost:8082/health
2. **查看错误日志**: 检查系统终端输出或 server.log 文件
3. **测试API连接**: 使用curl命令验证基本连接
4. **查看监控数据**: 访问管理界面检查实时状态

## 📝 更新日志

- **2025-08-27**: 添加ChatWise专用API密钥支持
- **2025-08-27**: 增强第三方客户端兼容性
- **2025-08-27**: 修复API密钥验证问题

---

**🎯 快速开始**: 使用 `chatwise-key` 密钥和 `qwen3:latest` 模型可以获得最佳的中文对话体验！