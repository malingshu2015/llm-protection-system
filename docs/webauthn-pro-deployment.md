# WebAuthn 专业库集成部署指南

## 概述

本系统已集成专业的 WebAuthn 库 (`webauthn>=2.0.0`) 实现完整的 FIDO2 认证协议,提供企业级的无密码登录功能。

## 主要改进

### 1. 完整的密码学验证
- ✅ **完整的签名验证**: 使用 `verify_registration_response()` 和 `verify_authentication_response()`
- ✅ **Attestation 验证**: 验证认证器的合法性
- ✅ **Origin 和 RP ID 验证**: 防止钓鱼攻击
- ✅ **Sign Count 验证**: 检测克隆的认证器
- ✅ **User Verification**: 支持生物识别验证

### 2. 安全特性
- **防克隆检测**: 通过签名计数器检测克隆的安全密钥
- **备份状态跟踪**: 检测凭证是否可备份和已备份
- **传输方式记录**: 记录认证器支持的传输方式 (USB, NFC, BLE 等)
- **AAGUID 记录**: 记录认证器的唯一标识符

## 安装步骤

### 1. 安装依赖

```bash
# 安装认证相关依赖
pip install -r requirements-auth.txt
```

requirements-auth.txt 包含:
```txt
# WebAuthn/FIDO2 支持
webauthn>=2.0.0,<3.0.0
cryptography>=41.0.0,<44.0.0

# 双因素认证 (2FA)
pyotp>=2.9.0,<3.0.0
qrcode[pil]>=7.4.2,<8.0.0
pillow>=10.0.0,<11.0.0

# OAuth2
httpx>=0.24.0,<0.29.0

# JWT
pyjwt>=2.8.0,<3.0.0
```

### 2. 配置参数

在 `src/auth/services/webauthn_service_pro.py` 中配置:

```python
webauthn_service = WebAuthnService(
    rp_id="localhost",              # 生产环境改为实际域名
    rp_name="LLM防护系统",
    rp_origin="http://localhost:8000",  # 生产环境改为 https://yourdomain.com
    storage_dir="data/webauthn"
)
```

### 3. 生产环境配置

**重要**: 生产环境必须使用 HTTPS:

```python
# 生产环境配置示例
webauthn_service = WebAuthnService(
    rp_id="yourdomain.com",
    rp_name="LLM防护系统",
    rp_origin="https://yourdomain.com",
    storage_dir="/var/lib/llm-protection/webauthn"
)
```

## 技术实现

### 注册流程

1. **创建挑战** (专业库)
```python
options = generate_registration_options(
    rp_id=self.rp_id,
    rp_name=self.rp_name,
    user_id=user_id.encode('utf-8'),
    user_name=username,
    exclude_credentials=existing_credentials,
    authenticator_selection={
        "authenticator_attachment": AuthenticatorAttachment.CROSS_PLATFORM,
        "user_verification": UserVerificationRequirement.PREFERRED,
    },
    attestation=AttestationConveyancePreference.NONE,
    timeout=60000,
)
```

2. **验证并保存** (完整签名验证)
```python
verification = verify_registration_response(
    credential=credential,
    expected_challenge=base64url_to_bytes(expected_challenge),
    expected_origin=self.rp_origin,
    expected_rp_id=self.rp_id,
)
```

### 认证流程

1. **创建挑战**
```python
options = generate_authentication_options(
    rp_id=self.rp_id,
    allow_credentials=allow_credentials,
    user_verification=UserVerificationRequirement.PREFERRED,
    timeout=60000,
)
```

2. **验证认证** (签名和计数器验证)
```python
verification = verify_authentication_response(
    credential=credential,
    expected_challenge=base64url_to_bytes(expected_challenge),
    expected_origin=self.rp_origin,
    expected_rp_id=self.rp_id,
    credential_public_key=base64url_to_bytes(stored_credential.public_key),
    credential_current_sign_count=stored_credential.sign_count,
)

# 更新签名计数器
stored_credential.sign_count = verification.new_sign_count
```

## API 端点

### 1. 注册流程

**创建注册挑战**
```http
POST /api/v1/webauthn/register/challenge
Authorization: Bearer <token>

Response:
{
  "challenge": "base64url_encoded_challenge",
  "rp": {
    "id": "localhost",
    "name": "LLM防护系统"
  },
  "user": {
    "id": "base64url_encoded_user_id",
    "name": "username",
    "displayName": "username"
  },
  "pubKeyCredParams": [...],
  "timeout": 60000,
  "excludeCredentials": [...],
  "authenticatorSelection": {...}
}
```

**验证并保存凭证**
```http
POST /api/v1/webauthn/register/verify
Authorization: Bearer <token>
Content-Type: application/json

{
  "credential_id": "base64url_encoded_id",
  "public_key": "base64url_encoded_key",
  "attestation_object": "base64url_encoded_attestation",
  "client_data_json": "base64url_encoded_client_data",
  "transports": ["usb", "nfc"],
  "device_name": "YubiKey 5C"
}
```

### 2. 认证流程

**创建认证挑战**
```http
POST /api/v1/webauthn/authenticate/challenge
Content-Type: application/json

{
  "username": "optional_username"
}

Response:
{
  "challenge": "base64url_encoded_challenge",
  "rpId": "localhost",
  "timeout": 60000,
  "allowCredentials": [...]
}
```

**验证认证并登录**
```http
POST /api/v1/webauthn/authenticate/verify
Content-Type: application/json

{
  "credential_id": "base64url_encoded_id",
  "authenticator_data": "base64url_encoded_data",
  "client_data_json": "base64url_encoded_client_data",
  "signature": "base64url_encoded_signature",
  "user_handle": "base64url_encoded_user_handle"
}

Response:
{
  "access_token": "jwt_token",
  "refresh_token": "refresh_token",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {...}
}
```

## 前端集成

前端代码已在 `static/admin/js/login.js` 中实现:

```javascript
async function loginWithWebAuthn() {
    // 1. 获取挑战
    const challengeData = await fetch('/api/v1/webauthn/authenticate/challenge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
    });

    // 2. 调用 WebAuthn API
    const assertion = await navigator.credentials.get({
        publicKey: publicKeyCredentialRequestOptions
    });

    // 3. 提交验证
    const authResponse = await fetch('/api/v1/webauthn/authenticate/verify', {
        method: 'POST',
        body: JSON.stringify({
            credential_id: arrayBufferToBase64(assertion.rawId),
            // ... 其他字段
        })
    });
}
```

## 数据存储

凭证数据存储在 `data/webauthn/` 目录:

```json
[
  {
    "id": "uuid",
    "user_id": "user_uuid",
    "credential_id": "base64url_encoded_id",
    "public_key": "base64url_encoded_public_key",
    "sign_count": 42,
    "aaguid": "hex_string",
    "transports": ["usb", "nfc"],
    "device_name": "YubiKey 5C",
    "is_backup_eligible": true,
    "is_backed_up": false,
    "created_at": "2024-01-01T00:00:00",
    "last_used": "2024-01-01T00:00:00"
  }
]
```

## 安全建议

### 1. 生产环境检查清单
- [ ] 使用 HTTPS (必需)
- [ ] 配置正确的 RP ID 和 Origin
- [ ] 限制允许的 Authenticator 类型
- [ ] 启用 User Verification (生物识别)
- [ ] 定期检查签名计数器异常
- [ ] 记录所有认证事件

### 2. 监控指标
- 认证成功/失败率
- 签名计数器异常检测
- 设备类型分布
- 用户验证使用率

### 3. 备份策略
- 建议用户注册多个安全密钥
- 保留传统密码作为备用方式
- 支持账户恢复机制

## 测试

### 支持的认证器
- ✅ YubiKey (所有型号)
- ✅ Windows Hello
- ✅ Touch ID (macOS/iOS)
- ✅ Face ID (iOS)
- ✅ Android Fingerprint
- ✅ Google Titan Key
- ✅ Feitian Keys

### 测试步骤

1. **注册测试**
```bash
# 访问安全密钥管理页面
http://localhost:8000/static/admin/webauthn-keys.html
```

2. **登录测试**
```bash
# 访问登录页面,点击"安全密钥登录"
http://localhost:8000/static/admin/login.html
```

## 故障排查

### 常见问题

1. **"此操作不安全"错误**
   - 检查是否使用 HTTPS (生产环境)
   - 检查 RP ID 和 Origin 配置

2. **"认证器不支持"错误**
   - 确认浏览器支持 WebAuthn
   - 检查认证器兼容性

3. **签名验证失败**
   - 检查 challenge 是否正确传递
   - 检查公钥是否正确存储

4. **克隆检测触发**
   - sign_count 没有递增
   - 可能的安全密钥克隆

## 下一步优化

1. **高级功能**
   - Conditional UI (自动填充建议)
   - 密钥使用统计
   - 异常检测和告警

2. **用户体验**
   - 设备类型识别
   - 密钥恢复机制
   - 多设备同步

3. **企业功能**
   - 策略管理
   - 批量密钥部署
   - 合规性报告

## 参考资料

- [WebAuthn 规范](https://www.w3.org/TR/webauthn-2/)
- [FIDO2 标准](https://fidoalliance.org/fido2/)
- [webauthn-python 文档](https://github.com/duo-labs/py_webauthn)
