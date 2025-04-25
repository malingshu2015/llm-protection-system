# macOS平台测试报告

**版本**: 1.0.0  
**日期**: 2025-04-25
**测试人员**: 开发团队

## 测试摘要

- 测试用例总数: 10
- 通过: 7
- 失败: 2
- 阻塞: 0
- 未执行: 1

## 测试环境

- macOS版本: macOS Sonoma (14.x)
- 处理器: Apple M1/M2
- 内存: 16GB
- Python版本: Python 3.13.2
- 浏览器: Safari

## 测试结果

| 测试ID | 测试名称 | 状态 | 备注 |
|-------|---------|------|------|
| TC-MACOS-INSTALL-001 | macOS Python包安装测试 | 通过 | 系统已成功安装在虚拟环境中 |
| TC-MACOS-INSTALL-002 | macOS Docker容器安装测试 | 未执行 | 需要Docker环境 |
| TC-MACOS-INSTALL-003 | macOS可执行文件安装测试 | 通过 | 系统可以正常启动 |
| TC-MACOS-FUNC-001 | macOS核心功能测试 | 部分通过 | 安全规则检测功能正常，但Ollama集成存在问题 |
| TC-MACOS-FUNC-002 | macOS API功能测试 | 通过 | 健康检查API和Ollama模型列表API正常工作 |
| TC-MACOS-FUNC-003 | macOS用户界面功能测试 | 通过 | Web界面在Safari浏览器中正常显示 |
| TC-MACOS-PERF-001 | macOS资源使用测试 | 通过 | CPU和内存使用在合理范围内 |
| TC-MACOS-PERF-002 | macOS响应时间测试 | 通过 | API响应时间在200ms以内 |
| TC-MACOS-COMP-001 | macOS版本兼容性测试 | 失败 | 在Python 3.13上存在Ollama模块导入问题 |
| TC-MACOS-SEC-001 | macOS权限验证测试 | 通过 | 安全规则正确拦截了恶意请求 |

## 发现的问题

| 问题ID | 问题描述 | 严重程度 | 状态 |
|-------|---------|---------|------|
| ISSUE-001 | Ollama模块导入失败 | 高 | 未解决 |
| ISSUE-002 | 解析Ollama响应JSON失败 | 高 | 未解决 |
| ISSUE-003 | 获取模型使用统计失败 | 中 | 未解决 |

## 详细测试结果

### 1. 安装测试

#### 1.1 Python包安装测试 (TC-MACOS-INSTALL-001)

系统已成功安装在虚拟环境中，可以通过`python -m src.main`命令启动。Python版本为3.13.2，系统可以正常加载。

#### 1.3 可执行文件安装测试 (TC-MACOS-INSTALL-003)

系统可以作为Python应用程序正常启动，并在8080端口提供Web服务。

### 2. 功能测试

#### 2.1 核心功能测试 (TC-MACOS-FUNC-001)

- 安全规则检测功能正常工作，成功拦截了包含"Ignore previous instructions"的恶意请求
- Ollama集成存在问题，无法正确解析Ollama的响应

#### 2.2 API功能测试 (TC-MACOS-FUNC-002)

- 健康检查API (`/api/v1/health`) 返回200状态码和正确的JSON响应
- Ollama模型列表API (`/api/v1/ollama/models`) 返回200状态码和正确的JSON响应，显示了5个模型
- Ollama聊天API (`/api/v1/ollama/chat`) 在发送恶意请求时正确返回403状态码和安全违规信息

#### 2.3 用户界面功能测试 (TC-MACOS-FUNC-003)

Web界面在Safari浏览器中正常显示，包括监控中心、规则管理、规则配置、安全事件和聊天演示等页面。

### 3. 性能测试

#### 3.1 资源使用测试 (TC-MACOS-PERF-001)

系统在空闲状态下CPU使用率低于5%，内存使用量在合理范围内。

#### 3.2 响应时间测试 (TC-MACOS-PERF-002)

- 健康检查API响应时间在100ms以内
- Ollama模型列表API响应时间在200ms以内

### 4. 兼容性测试

#### 4.1 Python版本兼容性测试 (TC-MACOS-COMP-001)

在Python 3.13上存在Ollama模块导入问题，日志显示"No module named 'ollama'"错误，尽管已经通过pip安装了ollama模块。

### 5. 安全测试

#### 5.1 权限验证测试 (TC-MACOS-SEC-001)

安全规则正确拦截了包含"Ignore previous instructions"的恶意请求，返回403状态码和安全违规信息。

## 问题详情

### ISSUE-001: Ollama模块导入失败

**描述**: 系统无法导入Ollama模块，日志显示"No module named 'ollama'"错误，尽管已经通过pip安装了ollama模块。

**重现步骤**:
1. 在Python 3.13环境中安装ollama模块: `pip install ollama`
2. 启动系统: `python -m src.main`
3. 观察日志

**期望结果**: Ollama模块应该被成功导入

**实际结果**: 日志显示"No module named 'ollama'"错误

**可能原因**: Python 3.13与ollama模块的兼容性问题，或者虚拟环境中的路径问题

### ISSUE-002: 解析Ollama响应JSON失败

**描述**: 系统无法正确解析Ollama的响应，日志显示"解析Ollama响应失败: Extra data: line 2 column 1 (char 128)"错误。

**重现步骤**:
1. 启动系统: `python -m src.main`
2. 发送聊天请求: `curl -X POST -H "Content-Type: application/json" -d '{"model":"llama2:latest","messages":[{"role":"user","content":"Hello, how are you?"}]}' http://localhost:8080/api/v1/ollama/chat`

**期望结果**: 系统应该正确解析Ollama的响应并返回聊天结果

**实际结果**: 系统返回500错误，日志显示"解析Ollama响应失败: Extra data: line 2 column 1 (char 128)"

**可能原因**: Ollama API返回的是流式响应，而系统尝试将其解析为单个JSON对象

### ISSUE-003: 获取模型使用统计失败

**描述**: 系统无法获取模型使用统计，日志显示"获取模型使用统计失败: No module named 'ollama'"错误。

**重现步骤**:
1. 启动系统: `python -m src.main`
2. 访问监控中心页面

**期望结果**: 系统应该显示模型使用统计

**实际结果**: 日志显示"获取模型使用统计失败: No module named 'ollama'"错误

**可能原因**: 与ISSUE-001相同，Ollama模块导入失败

## 结论与建议

本次测试在macOS平台上发现了几个与Ollama集成相关的问题，主要是Ollama模块导入失败和响应解析错误。这些问题可能与Python 3.13的兼容性有关，或者是系统对Ollama API的处理方式不正确。

### 改进建议

1. **降级Python版本**: 尝试使用Python 3.9或3.10，这些版本可能与ollama模块更兼容
2. **修复Ollama响应解析**: 修改系统代码，正确处理Ollama API的流式响应
3. **添加更多错误处理**: 增强系统的错误处理能力，提供更友好的错误信息
4. **提供替代方案**: 当Ollama模块不可用时，提供替代的集成方式，例如直接使用HTTP请求
5. **更新依赖管理**: 明确指定依赖版本，避免兼容性问题

尽管存在这些问题，系统的核心功能（安全规则检测）在macOS平台上正常工作，能够成功拦截恶意请求。Web界面也能正常显示，API响应时间在合理范围内。

建议优先解决Ollama模块导入问题，这将同时解决其他两个相关问题。可以考虑在短期内提供一个不依赖ollama模块的版本，使用HTTP请求直接与Ollama API通信。

---

本测试报告最后更新于2025年4月25日。
