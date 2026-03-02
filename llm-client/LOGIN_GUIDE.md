# LLM 防护客户端 - 登录指南

## 📋 系统已启动

✅ **后端服务**: `http://localhost:8082`
✅ **前端客户端**: Electron 应用已运行

## 🔐 登录凭据

### 测试用户账号

```
服务器地址: http://localhost:8082
用户名: test
密码: Test1234
```

### 密码要求

系统密码必须满足以下条件:
- ✅ 至少 8 个字符
- ✅ 包含大写字母 (A-Z)
- ✅ 包含小写字母 (a-z)
- ✅ 包含数字 (0-9)

**有效密码示例**:
- `Test1234`
- `Admin123`
- `Password1`
- `Welcome2024`

## 🚀 快速开始

1. **打开客户端**
   - Electron 应用应该已经自动打开
   - 如果没有,请重新运行: `cd llm-client && npm run electron:dev`

2. **登录**
   - 服务器地址: `http://localhost:8082`
   - 用户名: `test`
   - 密码: `Test1234`
   - 点击"登录"按钮

3. **开始使用**
   - 登录成功后会自动跳转到聊天界面
   - 可以开始与 LLM 对话

## ⚠️ 常见问题

### 问题 1: 显示 "[object Object]" 错误
**原因**: 服务器地址不正确或网络连接失败
**解决方案**:
- 确认服务器地址是 `http://localhost:8082` (不是 8000)
- 检查后端服务是否正常运行

### 问题 2: "账号已被锁定"
**原因**: 多次登录失败导致账号被临时锁定
**解决方案**:
- 等待 15 分钟后重试
- 或者使用其他测试账号

### 问题 3: "用户名或密码错误"
**原因**: 凭据输入错误
**解决方案**:
- 确认用户名: `test` (全小写)
- 确认密码: `Test1234` (注意大小写)
- 确保密码符合要求

## 📝 创建新用户

如果需要创建新用户,可以使用注册接口:

```bash
curl -X POST http://localhost:8082/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "NewPass123"
  }'
```

## 🔧 管理后台

除了桌面客户端,还可以访问 Web 管理界面:

- **聊天演示**: http://localhost:8082/static/chat/index.html
- **安全仪表板**: http://localhost:8082/static/admin/security-dashboard.html
- **模型管理**: http://localhost:8082/static/admin/models_v2.html
- **规则配置**: http://localhost:8082/static/admin/rules_v2.html

## 💡 提示

1. **首次登录**建议使用测试账号 `test/Test1234`
2. **密码安全**:生产环境请使用更强的密码
3. **多设备登录**:同一账号可在多个设备同时登录
4. **会话保持**:登录后令牌有效期 15 分钟,之后需要重新登录

## 🆘 需要帮助?

如果遇到其他问题,请检查:
1. 后端日志: `tail -f backend.log`
2. 浏览器控制台(开发者工具)
3. 客户端日志输出

---

**最后更新**: 2025-10-18
**版本**: v1.0.0
