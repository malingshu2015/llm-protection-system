# API安全实现文档

## 已实现功能

### 1. API密钥认证机制

API密钥认证机制提供了一种安全的方式来验证API调用者的身份，并控制其访问权限。

**主要特性**：
- API密钥生成和管理
- 基于API密钥的权限控制
- 基于API密钥的模型访问控制
- 支持从请求头、查询参数和Cookie中提取API密钥

**实现文件**：
- `src/security/api_auth.py`：API密钥管理和认证逻辑
- `src/middleware/security_middleware.py`：集成API密钥认证的中间件

**配置选项**：
- `settings.security.api_keys_path`：API密钥存储路径
- `settings.security.enable_api_auth`：是否启用API密钥认证

### 2. 请求速率限制

请求速率限制功能可以防止API被滥用，保护系统资源，防止DoS攻击。

**主要特性**：
- 基于API密钥的速率限制
- 基于IP地址的速率限制
- 可配置的时间窗口和请求限制
- 标准的速率限制响应头

**实现文件**：
- `src/security/rate_limiter.py`：速率限制逻辑
- `src/middleware/security_middleware.py`：集成速率限制的中间件

**配置选项**：
- `settings.security.rate_limit_path`：速率限制数据存储路径
- `settings.security.enable_rate_limiting`：是否启用速率限制

### 3. 内容脱敏

内容脱敏功能可以保护敏感信息，防止数据泄露。

**主要特性**：
- 支持多种敏感信息类型的脱敏（电话号码、邮箱、身份证号、信用卡号等）
- 不同类型敏感信息的不同脱敏策略
- 可配置的脱敏规则

**实现文件**：
- `src/security/content_masker.py`：内容脱敏逻辑
- `src/middleware/security_middleware.py`：集成内容脱敏的中间件

**配置选项**：
- `settings.security.sensitive_info_patterns_path`：敏感信息模式存储路径
- `settings.security.enable_content_masking`：是否启用内容脱敏

## 待实现功能

### 1. 上下文感知的检测

**计划功能**：
- 跟踪对话历史，检测多阶段攻击
- 基于上下文的安全检测
- 对话级别的安全策略

### 2. 基于机器学习的检测

**计划功能**：
- 使用机器学习模型检测复杂攻击模式
- 自动学习和适应新的攻击模式
- 异常检测和行为分析

### 3. 模型特定防护

**计划功能**：
- 针对特定模型的漏洞防护
- 模型特定的提示注入检测
- 模型特定的输出过滤

## 使用指南

### API密钥管理

#### 创建API密钥

```python
from src.security.api_auth import api_key_manager

# 创建一个新的API密钥
api_key = api_key_manager.create_api_key(
    name="测试API密钥",
    permissions=["chat", "completion"],
    rate_limit=100,
    models=["gpt-3.5-turbo", "gpt-4"]
)
print(f"新创建的API密钥: {api_key}")
```

#### 验证API密钥

```python
from src.security.api_auth import api_key_manager

# 验证API密钥
is_valid = api_key_manager.validate_api_key("your-api-key")
print(f"API密钥是否有效: {is_valid}")

# 检查权限
has_permission = api_key_manager.check_permission("your-api-key", "chat")
print(f"是否有chat权限: {has_permission}")

# 检查模型访问权限
can_access_model = api_key_manager.check_model_access("your-api-key", "gpt-4")
print(f"是否可以访问GPT-4模型: {can_access_model}")
```

### 速率限制

在API请求中，系统会自动检查速率限制。如果请求超过限制，将返回429状态码和以下响应：

```json
{
  "error": "请求频率超过限制",
  "type": "rate_limit_error",
  "code": 429,
  "rate_limit": {
    "limit": 60,
    "remaining": 0,
    "reset": 1620000000,
    "used": 61
  }
}
```

响应头中也会包含速率限制信息：

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1620000000
X-RateLimit-Used: 61
Retry-After: 30
```

### 内容脱敏

内容脱敏功能会自动处理响应中的敏感信息。例如：

- 电话号码：`13812345678` -> `138****5678`
- 邮箱：`user@example.com` -> `u***@example.com`
- 身份证号：`110101199001011234` -> `110***********1234`
- 信用卡号：`1234567890123456` -> `************3456`

## 安全最佳实践

1. **始终使用API密钥**：所有API请求都应该包含API密钥。
2. **限制API密钥权限**：为API密钥分配最小必要权限。
3. **定期轮换API密钥**：定期更换API密钥，减少泄露风险。
4. **监控API使用情况**：定期检查API使用日志，发现异常情况。
5. **设置合理的速率限制**：根据实际需求设置合理的速率限制，防止滥用。
6. **启用内容脱敏**：对于可能包含敏感信息的响应，启用内容脱敏功能。
7. **使用HTTPS**：所有API请求都应该使用HTTPS加密传输。
8. **实施IP白名单**：如果可能，限制API只能从特定IP地址访问。
