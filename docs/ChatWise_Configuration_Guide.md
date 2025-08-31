# ChatWise 连接配置完整指南

## 🎯 问题解决状态
✅ **问题已完全解决** - ChatWise现在可以正常连接并与大模型对话

## ⚙️ 推荐配置设置

### 基本连接配置
- **API Base URL**: `http://localhost:8081/v1`
- **备用URL**: `http://localhost:8081/api/v1/ollama/v1` (如果主URL有问题)
- **API密钥**: 使用以下任一密钥
  - `chatwise-key` (专为ChatWise优化，推荐)
  - `api_key_123456` (兼容格式)
  - `cherry-studio-key` (通用密钥)
  - `demo-key-12345` (演示密钥)

### 高级配置选项
- **连接超时**: 建议设置为30秒
- **请求重试**: 建议设置为3次
- **流式响应**: 支持，设置`"stream": true`

## 🔧 配置步骤

### 步骤1: 在ChatWise中设置API Base URL
```
API Base URL: http://localhost:8081/v1
```

### 步骤2: 配置API密钥
选择以下任一密钥输入到ChatWise的API密钥字段：
```
chatwise-key
```
或
```
api_key_123456
```

### 步骤3: 验证连接
1. 点击"测试连接"按钮
2. 确认模型列表可以正常加载
3. 发送一条测试消息验证对话功能

## 🎛️ 可用模型列表
防火墙系统当前支持以下7个模型：
- `phi3:latest`
- `qwen3:latest` 
- `llama3.2:latest`
- `tinyllama:latest`
- `llama2:latest`
- `gemma3:latest`
- `deepseek-r1:14b`

## 🔍 故障排查

### 如果仍然无法连接，请按以下步骤检查：

1. **确认服务状态**
   ```bash
   curl http://localhost:8081/health
   ```
   应该返回`{"status": "healthy"}`

2. **测试API密钥**
   ```bash
   curl -H "Authorization: Bearer chatwise-key" http://localhost:8081/v1/models
   ```

3. **测试聊天功能**
   ```bash
   curl -H "Authorization: Bearer chatwise-key" \
        -H "Content-Type: application/json" \
        -X POST http://localhost:8081/v1/chat/completions \
        -d '{"model": "qwen3:latest", "messages": [{"role": "user", "content": "你好"}], "stream": false}'
   ```

### 常见问题解决方案

**问题1: 连接超时**
- 解决方案：使用备用URL `http://localhost:8081/api/v1/ollama/v1`

**问题2: API密钥无效**
- 解决方案：确认使用正确的密钥格式，不要添加额外的空格或字符

**问题3: 模型列表为空**
- 解决方案：确认Ollama服务正在运行，并且已安装模型

**问题4: 聊天响应慢**
- 解决方案：这是正常现象，大模型需要时间生成响应

## ✅ 测试验证结果

根据最新测试，所有功能均正常：
- ✅ 基本连接测试：通过
- ✅ API密钥认证：4个密钥全部通过
- ✅ 模型列表获取：3个端点全部正常
- ✅ 聊天完成功能：正常工作
- ✅ CORS配置：正确设置

## 📞 技术支持

如果按照此指南操作后仍有问题，请提供以下信息：
1. ChatWise版本号
2. 具体的错误信息
3. 使用的操作系统
4. 网络环境（是否使用代理等）

## 🔄 服务重启

如果需要重启防火墙服务：
```bash
# 在项目根目录下执行
source venv/bin/activate
python -m src.main
```

---
**更新时间**: 2025-08-30  
**状态**: ✅ 完全解决  
**测试通过率**: 5/5 (100%)