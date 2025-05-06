# API安全功能测试计划

## 测试目标

本测试计划旨在验证本地大模型防护系统的API安全功能，包括API密钥认证、请求速率限制和内容脱敏功能。测试将确保这些功能能够有效防止通过API接口调用大模型的攻击，并保护输出内容的安全性。

## 测试环境

- **操作系统**：Windows 10/11、macOS 12+、Ubuntu 20.04/22.04
- **Python版本**：Python 3.9+
- **依赖库**：按照requirements.txt安装
- **测试工具**：pytest、curl、Postman、JMeter

## 测试范围

1. **API密钥认证测试**
2. **请求速率限制测试**
3. **内容脱敏测试**
4. **安全中间件集成测试**
5. **性能和负载测试**

## 测试计划

### 1. API密钥认证测试

#### 1.1 API密钥生成和管理测试

| 测试ID | 测试描述 | 预期结果 | 优先级 |
|-------|---------|---------|-------|
| AUTH-001 | 创建新的API密钥 | 成功创建API密钥并返回密钥值 | 高 |
| AUTH-002 | 创建具有特定权限的API密钥 | 成功创建API密钥并正确设置权限 | 高 |
| AUTH-003 | 创建具有特定模型访问权限的API密钥 | 成功创建API密钥并正确设置模型访问权限 | 高 |
| AUTH-004 | 创建具有速率限制的API密钥 | 成功创建API密钥并正确设置速率限制 | 高 |
| AUTH-005 | 删除API密钥 | 成功删除API密钥 | 中 |
| AUTH-006 | 获取API密钥信息 | 成功获取API密钥信息 | 中 |
| AUTH-007 | 加载API密钥文件 | 成功加载API密钥文件 | 高 |
| AUTH-008 | 保存API密钥文件 | 成功保存API密钥文件 | 高 |

#### 1.2 API密钥验证测试

| 测试ID | 测试描述 | 预期结果 | 优先级 |
|-------|---------|---------|-------|
| AUTH-101 | 使用有效API密钥访问API | 请求成功，返回200状态码 | 高 |
| AUTH-102 | 使用无效API密钥访问API | 请求失败，返回403状态码 | 高 |
| AUTH-103 | 不提供API密钥访问API | 请求失败，返回403状态码 | 高 |
| AUTH-104 | 使用过期API密钥访问API | 请求失败，返回403状态码 | 中 |
| AUTH-105 | 从请求头提取API密钥 | 成功从请求头提取API密钥 | 高 |
| AUTH-106 | 从查询参数提取API密钥 | 成功从查询参数提取API密钥 | 中 |
| AUTH-107 | 从Cookie提取API密钥 | 成功从Cookie提取API密钥 | 中 |

#### 1.3 权限控制测试

| 测试ID | 测试描述 | 预期结果 | 优先级 |
|-------|---------|---------|-------|
| AUTH-201 | 使用具有所需权限的API密钥访问API | 请求成功，返回200状态码 | 高 |
| AUTH-202 | 使用缺少所需权限的API密钥访问API | 请求失败，返回403状态码 | 高 |
| AUTH-203 | 使用通配符权限的API密钥访问API | 请求成功，返回200状态码 | 中 |
| AUTH-204 | 检查API密钥是否有特定权限 | 正确返回权限检查结果 | 高 |

#### 1.4 模型访问控制测试

| 测试ID | 测试描述 | 预期结果 | 优先级 |
|-------|---------|---------|-------|
| AUTH-301 | 使用具有所需模型访问权限的API密钥访问模型 | 请求成功，返回200状态码 | 高 |
| AUTH-302 | 使用缺少所需模型访问权限的API密钥访问模型 | 请求失败，返回403状态码 | 高 |
| AUTH-303 | 使用通配符模型访问权限的API密钥访问模型 | 请求成功，返回200状态码 | 中 |
| AUTH-304 | 检查API密钥是否有特定模型访问权限 | 正确返回模型访问权限检查结果 | 高 |

### 2. 请求速率限制测试

#### 2.1 基本速率限制测试

| 测试ID | 测试描述 | 预期结果 | 优先级 |
|-------|---------|---------|-------|
| RATE-001 | 在速率限制内发送请求 | 请求成功，返回200状态码 | 高 |
| RATE-002 | 超过速率限制发送请求 | 请求失败，返回429状态码 | 高 |
| RATE-003 | 验证速率限制响应头 | 响应头包含正确的速率限制信息 | 高 |
| RATE-004 | 验证Retry-After响应头 | 响应头包含正确的Retry-After值 | 中 |
| RATE-005 | 等待速率限制重置后发送请求 | 请求成功，返回200状态码 | 中 |

#### 2.2 基于API密钥的速率限制测试

| 测试ID | 测试描述 | 预期结果 | 优先级 |
|-------|---------|---------|-------|
| RATE-101 | 使用不同速率限制的API密钥发送请求 | 根据API密钥的速率限制正确处理请求 | 高 |
| RATE-102 | 使用同一API密钥从不同IP地址发送请求 | 请求计数合并，根据API密钥的速率限制正确处理请求 | 中 |
| RATE-103 | 获取API密钥的速率限制 | 正确返回API密钥的速率限制 | 中 |

#### 2.3 基于IP地址的速率限制测试

| 测试ID | 测试描述 | 预期结果 | 优先级 |
|-------|---------|---------|-------|
| RATE-201 | 不使用API密钥从同一IP地址发送请求 | 根据IP地址的速率限制正确处理请求 | 高 |
| RATE-202 | 使用不同API密钥从同一IP地址发送请求 | 根据API密钥的速率限制分别处理请求 | 中 |
| RATE-203 | 从代理后的IP地址发送请求 | 正确识别客户端IP地址并应用速率限制 | 中 |

#### 2.4 速率限制持久化测试

| 测试ID | 测试描述 | 预期结果 | 优先级 |
|-------|---------|---------|-------|
| RATE-301 | 保存请求计数到文件 | 成功保存请求计数到文件 | 中 |
| RATE-302 | 从文件加载请求计数 | 成功从文件加载请求计数 | 中 |
| RATE-303 | 重启服务后保持速率限制状态 | 重启服务后速率限制状态保持不变 | 中 |
| RATE-304 | 过期的请求计数自动清理 | 过期的请求计数被自动清理 | 低 |

### 3. 内容脱敏测试

#### 3.1 敏感信息检测测试

| 测试ID | 测试描述 | 预期结果 | 优先级 |
|-------|---------|---------|-------|
| MASK-001 | 检测电话号码 | 成功检测电话号码 | 高 |
| MASK-002 | 检测邮箱地址 | 成功检测邮箱地址 | 高 |
| MASK-003 | 检测身份证号 | 成功检测身份证号 | 高 |
| MASK-004 | 检测信用卡号 | 成功检测信用卡号 | 高 |
| MASK-005 | 检测多种敏感信息混合的文本 | 成功检测所有敏感信息 | 高 |
| MASK-006 | 检测边界情况（部分匹配、格式变化等） | 正确处理边界情况 | 中 |

#### 3.2 敏感信息脱敏测试

| 测试ID | 测试描述 | 预期结果 | 优先级 |
|-------|---------|---------|-------|
| MASK-101 | 脱敏电话号码 | 电话号码被正确脱敏（如：138****5678） | 高 |
| MASK-102 | 脱敏邮箱地址 | 邮箱地址被正确脱敏（如：u***@example.com） | 高 |
| MASK-103 | 脱敏身份证号 | 身份证号被正确脱敏（如：110***********1234） | 高 |
| MASK-104 | 脱敏信用卡号 | 信用卡号被正确脱敏（如：************3456） | 高 |
| MASK-105 | 脱敏多种敏感信息混合的文本 | 所有敏感信息被正确脱敏 | 高 |
| MASK-106 | 脱敏边界情况 | 正确处理边界情况 | 中 |

#### 3.3 响应处理测试

| 测试ID | 测试描述 | 预期结果 | 优先级 |
|-------|---------|---------|-------|
| MASK-201 | 从OpenAI响应中提取文本 | 成功从OpenAI响应中提取文本 | 高 |
| MASK-202 | 从Anthropic响应中提取文本 | 成功从Anthropic响应中提取文本 | 高 |
| MASK-203 | 从Ollama响应中提取文本 | 成功从Ollama响应中提取文本 | 高 |
| MASK-204 | 更新OpenAI响应中的文本 | 成功更新OpenAI响应中的文本 | 高 |
| MASK-205 | 更新Anthropic响应中的文本 | 成功更新Anthropic响应中的文本 | 高 |
| MASK-206 | 更新Ollama响应中的文本 | 成功更新Ollama响应中的文本 | 高 |
| MASK-207 | 处理流式响应 | 成功处理流式响应中的敏感信息 | 中 |

### 4. 安全中间件集成测试

#### 4.1 中间件功能测试

| 测试ID | 测试描述 | 预期结果 | 优先级 |
|-------|---------|---------|-------|
| MID-001 | 中间件处理正常请求 | 请求成功，返回200状态码 | 高 |
| MID-002 | 中间件处理无API密钥的请求 | 请求失败，返回403状态码 | 高 |
| MID-003 | 中间件处理超过速率限制的请求 | 请求失败，返回429状态码 | 高 |
| MID-004 | 中间件处理包含敏感信息的响应 | 响应中的敏感信息被脱敏 | 高 |
| MID-005 | 中间件处理OPTIONS请求 | OPTIONS请求被正确处理 | 中 |
| MID-006 | 中间件处理公开路径的请求 | 公开路径的请求被正确处理，不需要API密钥 | 中 |

#### 4.2 中间件集成测试

| 测试ID | 测试描述 | 预期结果 | 优先级 |
|-------|---------|---------|-------|
| MID-101 | 中间件与FastAPI集成 | 中间件成功集成到FastAPI应用中 | 高 |
| MID-102 | 中间件与API路由集成 | 中间件成功保护API路由 | 高 |
| MID-103 | 中间件与其他中间件的顺序 | 中间件按正确顺序执行 | 中 |
| MID-104 | 中间件错误处理 | 中间件错误被正确处理 | 中 |

### 5. 性能和负载测试

#### 5.1 性能测试

| 测试ID | 测试描述 | 预期结果 | 优先级 |
|-------|---------|---------|-------|
| PERF-001 | API密钥验证性能 | API密钥验证的平均响应时间<10ms | 中 |
| PERF-002 | 速率限制检查性能 | 速率限制检查的平均响应时间<10ms | 中 |
| PERF-003 | 内容脱敏性能 | 内容脱敏的平均处理时间<50ms（对于1KB文本） | 中 |
| PERF-004 | 中间件整体性能 | 中间件整体处理的平均响应时间增加<100ms | 中 |

#### 5.2 负载测试

| 测试ID | 测试描述 | 预期结果 | 优先级 |
|-------|---------|---------|-------|
| LOAD-001 | 并发请求处理 | 系统能够处理100个并发请求，响应时间增加<200% | 中 |
| LOAD-002 | 高频率API密钥验证 | 系统能够处理每秒1000次API密钥验证 | 中 |
| LOAD-003 | 高频率速率限制检查 | 系统能够处理每秒1000次速率限制检查 | 中 |
| LOAD-004 | 大量API密钥管理 | 系统能够管理10000个API密钥，性能下降<50% | 低 |
| LOAD-005 | 大量速率限制记录 | 系统能够管理10000个客户端的速率限制记录，性能下降<50% | 低 |

## 测试数据

### API密钥测试数据

```json
{
  "valid_key": {
    "name": "测试API密钥",
    "permissions": ["chat", "completion"],
    "created_at": 1620000000,
    "rate_limit": 100,
    "models": ["gpt-3.5-turbo", "gpt-4"]
  },
  "invalid_key": "invalid_api_key",
  "expired_key": {
    "name": "过期API密钥",
    "permissions": ["chat"],
    "created_at": 1600000000,
    "rate_limit": 100,
    "models": ["gpt-3.5-turbo"],
    "expires_at": 1610000000
  }
}
```

### 敏感信息测试数据

```json
{
  "phone_numbers": [
    "13812345678",
    "+86 138 1234 5678",
    "138-1234-5678"
  ],
  "emails": [
    "user@example.com",
    "test.user@company.co.uk",
    "john.doe123@sub.domain.org"
  ],
  "id_cards": [
    "110101199001011234",
    "11010119900101123X",
    "110101 19900101 1234"
  ],
  "credit_cards": [
    "1234567890123456",
    "1234 5678 9012 3456",
    "1234-5678-9012-3456"
  ],
  "mixed_text": "我的手机号是13812345678，邮箱是user@example.com，身份证号是110101199001011234，信用卡号是1234567890123456。"
}
```

## 测试脚本

### API密钥认证测试脚本

```python
import pytest
import requests

BASE_URL = "http://localhost:8080"
VALID_API_KEY = "your_valid_api_key"
INVALID_API_KEY = "invalid_api_key"

def test_valid_api_key():
    response = requests.get(
        f"{BASE_URL}/api/v1/health",
        headers={"X-API-Key": VALID_API_KEY}
    )
    assert response.status_code == 200

def test_invalid_api_key():
    response = requests.get(
        f"{BASE_URL}/api/v1/health",
        headers={"X-API-Key": INVALID_API_KEY}
    )
    assert response.status_code == 403

def test_no_api_key():
    response = requests.get(f"{BASE_URL}/api/v1/health")
    assert response.status_code == 403

def test_api_key_from_query_param():
    response = requests.get(f"{BASE_URL}/api/v1/health?api_key={VALID_API_KEY}")
    assert response.status_code == 200
```

### 速率限制测试脚本

```python
import pytest
import requests
import time

BASE_URL = "http://localhost:8080"
VALID_API_KEY = "your_valid_api_key"
RATE_LIMIT = 10  # 假设速率限制为每分钟10个请求

def test_rate_limit():
    # 发送速率限制内的请求
    for i in range(RATE_LIMIT):
        response = requests.get(
            f"{BASE_URL}/api/v1/health",
            headers={"X-API-Key": VALID_API_KEY}
        )
        assert response.status_code == 200
        assert "X-RateLimit-Remaining" in response.headers
        remaining = int(response.headers["X-RateLimit-Remaining"])
        assert remaining == RATE_LIMIT - i - 1

    # 发送超过速率限制的请求
    response = requests.get(
        f"{BASE_URL}/api/v1/health",
        headers={"X-API-Key": VALID_API_KEY}
    )
    assert response.status_code == 429
    assert "X-RateLimit-Remaining" in response.headers
    assert int(response.headers["X-RateLimit-Remaining"]) == 0
    assert "Retry-After" in response.headers

    # 等待速率限制重置
    reset_time = int(response.headers["X-RateLimit-Reset"])
    wait_time = reset_time - int(time.time()) + 1
    if wait_time > 0:
        time.sleep(wait_time)

    # 发送重置后的请求
    response = requests.get(
        f"{BASE_URL}/api/v1/health",
        headers={"X-API-Key": VALID_API_KEY}
    )
    assert response.status_code == 200
    assert "X-RateLimit-Remaining" in response.headers
    assert int(response.headers["X-RateLimit-Remaining"]) == RATE_LIMIT - 1
```

### 内容脱敏测试脚本

```python
import pytest
from src.security.content_masker import content_masker

def test_phone_number_masking():
    text = "我的手机号是13812345678"
    masked_text, mask_info = content_masker.mask_sensitive_info(text)
    assert "138****5678" in masked_text
    assert len(mask_info) == 1
    assert mask_info[0]["type"] == "phone_number"

def test_email_masking():
    text = "我的邮箱是user@example.com"
    masked_text, mask_info = content_masker.mask_sensitive_info(text)
    assert "u***@example.com" in masked_text
    assert len(mask_info) == 1
    assert mask_info[0]["type"] == "email"

def test_id_card_masking():
    text = "我的身份证号是110101199001011234"
    masked_text, mask_info = content_masker.mask_sensitive_info(text)
    assert "110***********1234" in masked_text
    assert len(mask_info) == 1
    assert mask_info[0]["type"] == "id_card"

def test_credit_card_masking():
    text = "我的信用卡号是1234567890123456"
    masked_text, mask_info = content_masker.mask_sensitive_info(text)
    assert "************3456" in masked_text
    assert len(mask_info) == 1
    assert mask_info[0]["type"] == "credit_card"

def test_mixed_text_masking():
    text = "我的手机号是13812345678，邮箱是user@example.com，身份证号是110101199001011234，信用卡号是1234567890123456。"
    masked_text, mask_info = content_masker.mask_sensitive_info(text)
    assert "138****5678" in masked_text
    assert "u***@example.com" in masked_text
    assert "110***********1234" in masked_text
    assert "************3456" in masked_text
    assert len(mask_info) == 4
```

## 测试执行计划

1. **单元测试**：使用pytest执行单元测试，验证各个组件的功能
2. **集成测试**：验证组件之间的交互和集成
3. **API测试**：使用curl或Postman测试API端点
4. **性能测试**：使用JMeter进行性能和负载测试
5. **手动测试**：验证边界情况和复杂场景

## 测试报告模板

```
# API安全功能测试报告

## 测试摘要

- **测试日期**：[日期]
- **测试环境**：[环境]
- **测试版本**：[版本]
- **测试执行人**：[姓名]

## 测试结果摘要

- **总测试用例数**：[数量]
- **通过**：[数量]
- **失败**：[数量]
- **跳过**：[数量]
- **通过率**：[百分比]

## 详细测试结果

### API密钥认证测试

| 测试ID | 测试描述 | 结果 | 备注 |
|-------|---------|------|------|
| AUTH-001 | 创建新的API密钥 | 通过/失败 | [备注] |
| ... | ... | ... | ... |

### 请求速率限制测试

| 测试ID | 测试描述 | 结果 | 备注 |
|-------|---------|------|------|
| RATE-001 | 在速率限制内发送请求 | 通过/失败 | [备注] |
| ... | ... | ... | ... |

### 内容脱敏测试

| 测试ID | 测试描述 | 结果 | 备注 |
|-------|---------|------|------|
| MASK-001 | 检测电话号码 | 通过/失败 | [备注] |
| ... | ... | ... | ... |

### 安全中间件集成测试

| 测试ID | 测试描述 | 结果 | 备注 |
|-------|---------|------|------|
| MID-001 | 中间件处理正常请求 | 通过/失败 | [备注] |
| ... | ... | ... | ... |

### 性能和负载测试

| 测试ID | 测试描述 | 结果 | 备注 |
|-------|---------|------|------|
| PERF-001 | API密钥验证性能 | 通过/失败 | [备注] |
| ... | ... | ... | ... |

## 发现的问题

| 问题ID | 问题描述 | 严重程度 | 状态 |
|-------|---------|---------|------|
| ISSUE-001 | [问题描述] | 高/中/低 | 开放/已修复/已验证 |
| ... | ... | ... | ... |

## 结论和建议

[结论和建议]

## 附件

- [测试日志]
- [性能测试报告]
- [其他附件]
```

## 测试责任人

- **单元测试**：[姓名]
- **集成测试**：[姓名]
- **API测试**：[姓名]
- **性能测试**：[姓名]
- **测试报告**：[姓名]

## 测试时间表

| 阶段 | 开始日期 | 结束日期 | 负责人 |
|-----|---------|---------|-------|
| 测试计划编写 | 2025-05-03 | 2025-05-03 | [姓名] |
| 单元测试 | 2025-05-04 | 2025-05-05 | [姓名] |
| 集成测试 | 2025-05-06 | 2025-05-07 | [姓名] |
| API测试 | 2025-05-08 | 2025-05-09 | [姓名] |
| 性能测试 | 2025-05-10 | 2025-05-11 | [姓名] |
| 测试报告编写 | 2025-05-12 | 2025-05-12 | [姓名] |

## 风险和缓解策略

| 风险 | 可能性 | 影响 | 缓解策略 |
|-----|-------|------|---------|
| 测试环境不稳定 | 中 | 高 | 准备备用测试环境，使用容器化测试环境 |
| 测试数据不足 | 中 | 中 | 提前准备充分的测试数据，包括边界情况 |
| 性能测试资源不足 | 低 | 高 | 使用云服务进行性能测试，分时段执行 |
| 测试时间不足 | 中 | 高 | 优先测试关键功能，自动化测试提高效率 |

---

**注意**：此测试计划为动态文档，将根据项目进展不断更新。请定期检查最新版本。
