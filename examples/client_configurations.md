# 第三方客户端配置示例

本文档提供了主流AI聊天客户端的详细配置步骤。

## 🍒 Cherry Studio 配置

### 方法1：OpenAI兼容配置（推荐）

#### 步骤1：添加自定义API
1. 打开Cherry Studio
2. 点击左下角的"设置"图标
3. 选择"模型"选项卡
4. 点击"添加自定义API"

#### 步骤2：配置API设置
```
API名称: LLM Security Firewall
API类型: OpenAI Compatible
Base URL: http://localhost:8082/v1
API Key: cherry-studio-key
```

#### 步骤3：选择模型
- 在模型列表中选择可用的模型（如：tinyllama:latest）
- 点击"测试连接"验证配置

### 方法2：Ollama兼容配置

#### 配置选项A：
```
API名称: LLM Security Firewall (Ollama)
API类型: Ollama
Base URL: http://localhost:8082/api/v1/ollama
API Key: cherry-studio-key
```

#### 配置选项B：
```
API名称: LLM Security Firewall (Ollama v1)
API类型: Ollama
Base URL: http://localhost:8082/api/v1/ollama/v1
API Key: cherry-studio-key
```

### 故障排除

#### 问题1：无法获取模型列表
**解决方案：**
1. 确保API密钥正确：`cherry-studio-key`
2. 尝试不同的Base URL：
   - `http://localhost:8082/v1`
   - `http://localhost:8082/api/v1/ollama`
   - `http://localhost:8082`

#### 问题2：连接被拒绝
**解决方案：**
1. 确认防火墙程序正在运行：
   ```bash
   curl http://localhost:8082/health
   ```
2. 检查端口8082是否被占用
3. 确认API密钥格式正确

#### 问题3：模型无响应
**解决方案：**
1. 检查Ollama服务是否运行
2. 确认模型已下载：`ollama list`
3. 查看防火墙日志获取详细错误信息

### 步骤4：开始聊天
- 创建新对话
- 选择配置的模型
- 开始安全的AI对话

## 📦 ChatBox 配置

### 步骤1：打开设置
1. 启动ChatBox应用
2. 点击右上角的设置图标
3. 选择"API设置"

### 步骤2：配置OpenAI API
```
API Provider: OpenAI API
API Host: http://localhost:8082/v1
API Key: cherry-studio-key
Model: tinyllama:latest
```

### 步骤3：测试连接
- 点击"测试API"按钮
- 确认连接成功
- 保存设置

## 🌐 Open WebUI 配置

### 步骤1：管理员设置
1. 访问 Open WebUI 管理界面
2. 登录管理员账户
3. 进入"设置" -> "连接"

### 步骤2：添加OpenAI API
```
API类型: OpenAI API
API URL: http://localhost:8082/v1
API密钥: cherry-studio-key
```

### 步骤3：验证模型
- 点击"获取模型"
- 确认模型列表加载成功
- 选择默认模型

## 💬 LibreChat 配置

### 步骤1：环境配置
在`.env`文件中添加：
```env
OPENAI_API_KEY=cherry-studio-key
OPENAI_REVERSE_PROXY=http://localhost:8082/v1
```

### 步骤2：模型配置
在`librechat.yaml`中配置：
```yaml
version: 1.0.5
cache: true
endpoints:
  custom:
    - name: "LLM Security Firewall"
      apiKey: "cherry-studio-key"
      baseURL: "http://localhost:8082/v1"
      models:
        default: ["tinyllama:latest"]
```

## 🔧 通用cURL测试

### 测试模型列表
```bash
curl -H "Authorization: Bearer cherry-studio-key" \
     http://localhost:8082/v1/models | jq .
```

### 测试聊天接口
```bash
curl -X POST http://localhost:8082/v1/chat/completions \
  -H "Authorization: Bearer cherry-studio-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tinyllama:latest",
    "messages": [
      {
        "role": "user",
        "content": "Hello, please introduce yourself"
      }
    ],
    "stream": false,
    "max_tokens": 100
  }' | jq .
```

### 测试流式聊天
```bash
curl -X POST http://localhost:8082/v1/chat/completions \
  -H "Authorization: Bearer cherry-studio-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tinyllama:latest",
    "messages": [
      {
        "role": "user",
        "content": "Count from 1 to 10"
      }
    ],
    "stream": true,
    "max_tokens": 50
  }'
```

## 🐍 Python客户端示例

### 使用OpenAI库
```python
import openai

# 配置客户端
client = openai.OpenAI(
    api_key="cherry-studio-key",
    base_url="http://localhost:8082/v1"
)

# 获取模型列表
models = client.models.list()
print("可用模型:", [model.id for model in models.data])

# 发送聊天请求
response = client.chat.completions.create(
    model="tinyllama:latest",
    messages=[
        {"role": "user", "content": "Hello, how are you?"}
    ],
    max_tokens=100
)

print("AI回复:", response.choices[0].message.content)
```

### 使用requests库
```python
import requests
import json

BASE_URL = "http://localhost:8082"
API_KEY = "cherry-studio-key"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 获取模型列表
models_response = requests.get(f"{BASE_URL}/v1/models", headers=HEADERS)
models = models_response.json()
print("可用模型:", [model["name"] for model in models["models"]])

# 发送聊天请求
chat_data = {
    "model": "tinyllama:latest",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": False,
    "max_tokens": 50
}

chat_response = requests.post(
    f"{BASE_URL}/v1/chat/completions",
    headers=HEADERS,
    json=chat_data
)

if chat_response.status_code == 200:
    result = chat_response.json()
    print("AI回复:", result["choices"][0]["message"]["content"])
else:
    print("请求失败:", chat_response.status_code, chat_response.text)
```

## 🔍 故障排除

### 常见错误及解决方案

#### 1. 连接被拒绝
```
错误: Connection refused
解决: 确保防火墙服务正在运行 (python3 -m src.main)
```

#### 2. API密钥无效
```
错误: 403 Forbidden - API密钥验证失败
解决: 检查API密钥是否正确，格式是否为 "Bearer <key>"
```

#### 3. 模型不可用
```
错误: Model not found
解决: 确保Ollama服务运行并安装了所需模型
```

#### 4. 请求被安全拦截
```
错误: 403 Forbidden - 安全检测失败
解决: 检查请求内容，避免使用可能触发安全规则的词汇
```

### 调试技巧

1. **查看服务器日志**：
   ```bash
   # 启动时查看详细日志
   WEB_PORT=8082 python3 -m src.main
   ```

2. **测试API连通性**：
   ```bash
   curl -I http://localhost:8082/v1/models
   ```

3. **验证API密钥**：
   ```bash
   curl -H "Authorization: Bearer cherry-studio-key" \
        http://localhost:8082/v1/models
   ```

4. **检查安全事件**：
   ```bash
   cat data/security/security_events.json | jq .
   ```

## 📋 配置检查清单

在配置客户端之前，请确认：

- [ ] LLM安全防火墙服务正在运行
- [ ] Ollama服务正在运行
- [ ] 至少安装了一个Ollama模型
- [ ] API密钥配置正确
- [ ] 网络连接正常
- [ ] 防火墙端口8082已开放

## 🎯 性能优化建议

1. **调整超时设置**：根据模型大小调整客户端超时时间
2. **使用流式响应**：对于长文本生成，使用stream=true
3. **限制token数量**：设置合适的max_tokens避免过长响应
4. **监控资源使用**：定期检查CPU和内存使用情况
5. **批量请求**：避免频繁的单次请求，考虑批量处理
