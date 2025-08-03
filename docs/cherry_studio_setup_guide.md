# Cherry Studio 配置详细指南

## 🎯 概述

本指南将帮助您在Cherry Studio中配置LLM安全防火墙，实现安全的AI对话体验。

## ✅ 前提条件

1. **LLM安全防火墙已启动**
   ```bash
   WEB_PORT=8082 python3 -m src.main
   ```

2. **验证服务状态**
   ```bash
   curl http://localhost:8082/health
   # 应该返回: {"status":"healthy",...}
   ```

3. **Cherry Studio已安装**
   - 从官网下载并安装Cherry Studio
   - 确保版本支持自定义API配置

## 🔧 配置步骤

### 步骤1：打开Cherry Studio设置

1. 启动Cherry Studio应用
2. 点击左下角的**设置**图标（齿轮图标）
3. 在设置界面中选择**模型**选项卡

### 步骤2：添加自定义API

1. 在模型设置页面，点击**添加自定义API**按钮
2. 选择API类型为**OpenAI Compatible**

### 步骤3：配置API参数

**推荐配置（OpenAI兼容）：**
```
API名称: LLM Security Firewall
API类型: OpenAI Compatible
Base URL: http://localhost:8082/v1
API Key: cherry-studio-key
```

**备用配置（Ollama兼容）：**
```
API名称: LLM Security Firewall (Ollama)
API类型: Ollama
Base URL: http://localhost:8082/api/v1/ollama/v1
API Key: cherry-studio-key
```

**重要说明：**
- 推荐使用OpenAI兼容配置，兼容性最好
- API Key必须是`cherry-studio-key`（与防火墙配置一致）
- 不要在URL末尾添加斜杠
- 系统已自动处理Cherry Studio的路径重复问题

### 步骤4：测试连接

1. 点击**测试连接**按钮
2. 等待连接测试完成
3. 如果显示"连接成功"，说明配置正确

### 步骤5：选择模型

1. 在模型列表中，您应该看到可用的模型：
   - `tinyllama:latest` (推荐用于测试)
   - `phi3:latest`
   - `qwen3:latest`
   - `llama3.2:latest`
   - 其他已安装的模型

2. 选择一个模型进行测试

### 步骤6：开始对话

1. 创建新的对话
2. 选择刚才配置的模型
3. 发送测试消息，如："Hello, how are you?"
4. 验证模型正常响应

## 🔍 故障排除

### 问题1：无法连接到服务

**症状：** Cherry Studio显示"连接失败"或"无法访问API"

**解决方案：**
1. 确认防火墙程序正在运行：
   ```bash
   curl http://localhost:8082/health
   ```

2. 检查端口是否被占用：
   ```bash
   lsof -i :8082
   ```

3. 尝试重启防火墙程序

### 问题2：API密钥验证失败

**症状：** 返回403 Forbidden错误

**解决方案：**
1. 确认API Key设置为：`cherry-studio-key`
2. 检查是否有多余的空格或特殊字符
3. 重新输入API Key

### 问题3：无法获取模型列表

**症状：** 模型列表为空或加载失败

**解决方案：**
1. 确认Ollama服务正在运行：
   ```bash
   ollama list
   ```

2. 检查防火墙日志是否有错误信息

3. 尝试不同的Base URL配置：
   - `http://localhost:8082/v1`
   - `http://localhost:8082/api/v1/ollama`

### 问题4：模型无响应

**症状：** 发送消息后长时间无响应

**解决方案：**
1. 检查所选模型是否已正确下载
2. 尝试使用较小的模型（如tinyllama:latest）
3. 查看防火墙日志获取详细错误信息

### 问题5：响应被安全系统拦截

**症状：** 收到安全拦截提示

**解决方案：**
1. 这是正常的安全防护功能
2. 避免发送可能触发安全规则的内容
3. 如需调整安全规则，请参考安全配置文档

## 🧪 测试工具

我们提供了专门的测试工具来验证配置：

```bash
# 运行Cherry Studio兼容性测试
python3 tools/cherry_studio_tester.py

# 运行完整API测试
python3 tools/api_tester.py --test all
```

## 📋 配置模板

### 标准OpenAI兼容配置
```
API名称: LLM Security Firewall
API类型: OpenAI Compatible
Base URL: http://localhost:8082/v1
API Key: cherry-studio-key
```

### 备用Ollama兼容配置
```
API名称: LLM Security Firewall (Ollama)
API类型: Ollama
Base URL: http://localhost:8082/api/v1/ollama
API Key: cherry-studio-key
```

## 🔒 安全特性

配置完成后，您的Cherry Studio将享受以下安全保护：

1. **提示注入防护** - 自动检测和阻止恶意提示
2. **越狱尝试拦截** - 识别绕过安全限制的行为
3. **内容过滤** - 过滤有害和不当内容
4. **会话监控** - 跟踪和记录安全事件

## 📞 获取帮助

如果您在配置过程中遇到问题：

1. **查看日志**：检查防火墙程序的控制台输出
2. **运行测试**：使用提供的测试工具验证配置
3. **检查文档**：参考完整的API文档和配置指南
4. **重置配置**：删除Cherry Studio中的API配置并重新添加

## 🎉 成功标志

配置成功后，您应该能够：

- ✅ 在Cherry Studio中看到可用的模型列表
- ✅ 成功发送消息并收到AI响应
- ✅ 看到安全防护功能正常工作
- ✅ 享受流畅的对话体验

现在您可以安全地使用Cherry Studio进行AI对话了！
