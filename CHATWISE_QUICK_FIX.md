# 🚨 ChatWise连接问题快速修复指南

## 问题诊断

✅ **服务器状态**: 正常运行在端口8082  
✅ **API功能**: 所有接口正常工作  
❌ **配置问题**: ChatWise客户端配置的端口不正确  

## 🔧 立即修复步骤

### 步骤1: 更新ChatWise配置

在ChatWise客户端中，将API Base URL从：
```
http://localhost:8081/v1
```

更改为：
```
http://localhost:8082/v1
```

### 步骤2: 确认API密钥

使用以下任一API密钥：
- `chatwise-key` (推荐)
- `api_key_123456`
- `cherry-studio-key`
- `demo-key-12345`

### 步骤3: 测试连接

点击ChatWise中的"测试连接"按钮，应该能够成功连接。

## 🧪 验证修复

运行以下命令验证服务正常：

```bash
# 测试健康状态
curl http://localhost:8082/health

# 测试API密钥
curl -H "Authorization: Bearer chatwise-key" http://localhost:8082/v1/models

# 测试聊天功能
curl -X POST -H "Authorization: Bearer chatwise-key" -H "Content-Type: application/json" \
  -d '{"model": "qwen3:latest", "messages": [{"role": "user", "content": "测试连接"}], "stream": false}' \
  http://localhost:8082/v1/chat/completions
```

## 📋 测试结果

根据最新测试（2025-09-01）：

- ✅ 健康检查: 通过
- ✅ 模型列表: 7个模型可用
- ✅ 聊天功能: 正常工作
- ✅ API认证: 所有密钥有效

## 🎯 推荐配置

**最佳配置组合**：
- API Base URL: `http://localhost:8082/v1`
- API Key: `chatwise-key`
- 推荐模型: `qwen3:latest`

## ❓ 仍有问题？

如果按照上述步骤操作后仍无法连接，请：

1. 确认防火墙系统正在运行
2. 检查网络连接
3. 重启ChatWise客户端
4. 查看系统日志获取详细错误信息

---

**更新时间**: 2025-09-01  
**状态**: ✅ 问题已识别并提供解决方案