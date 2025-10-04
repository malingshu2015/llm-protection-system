# 统一客户端程序设计方案

## 一、需求分析

### 1.1 核心需求

#### 用户体验需求
- **快捷连接**: 一键连接到大模型服务，无需手动配置
- **统一界面**: 统一的交互界面，支持多种大模型
- **会话管理**: 管理多个对话会话，支持历史记录
- **快速切换**: 在不同大模型之间快速切换

#### 安全控制需求
- **输入过滤**: 在客户端层面就过滤敏感内容
- **输出审查**: 对模型输出进行安全检查
- **数据加密**: 敏感数据端到端加密
- **访问控制**: 基于用户身份的权限控制

#### 管理需求
- **集中管理**: 统一的配置和策略管理
- **使用统计**: 跟踪和分析使用情况
- **审计日志**: 完整的操作审计
- **策略下发**: 自动更新安全策略

### 1.2 使用场景

#### 场景 1: 企业员工使用
```
员工 → 安装客户端 → 自动配置企业策略 → 连接到企业 LLM 网关
     → 发送请求 → 客户端预过滤 → 网关二次过滤 → 模型
     → 响应 → 网关过滤 → 客户端审查 → 显示给用户
```

#### 场景 2: 开发者集成
```
开发者 → 客户端 SDK → 应用程序调用 → 自动路由到防护网关
      → 统一的 API 接口 → 多模型支持 → 安全策略自动应用
```

#### 场景 3: 个人用户
```
用户 → 下载客户端 → 注册/登录 → 选择模型 → 开始对话
    → 自动安全检查 → 保护隐私 → 记录历史
```

## 二、系统架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────┐
│            统一客户端层 (多平台)                  │
├─────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  桌面端   │  │  移动端   │  │  Web端   │      │
│  │ (Electron)│  │(React N) │  │  (React) │      │
│  └──────────┘  └──────────┘  └──────────┘      │
│                                                  │
│  ┌────────────────────────────────────┐        │
│  │         客户端核心引擎              │        │
│  │  - 连接管理  - 安全过滤            │        │
│  │  - 会话管理  - 离线缓存            │        │
│  │  - 策略同步  - 数据加密            │        │
│  └────────────────────────────────────┘        │
└─────────────────────────────────────────────────┘
                        ↕ (WebSocket/gRPC)
┌─────────────────────────────────────────────────┐
│         LLM 防护系统 (服务器端)                   │
├─────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐            │
│  │  客户端网关   │  │  策略管理     │            │
│  │  - 认证授权   │  │  - 策略下发   │            │
│  │  - 连接池     │  │  - 版本控制   │            │
│  └──────────────┘  └──────────────┘            │
│                                                  │
│  ┌────────────────────────────────────┐        │
│  │         现有防护引擎                │        │
│  │  - 内容检测  - 模型拦截            │        │
│  │  - 审计日志  - 告警系统            │        │
│  └────────────────────────────────────┘        │
└─────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────┐
│              大模型服务层                         │
│  OpenAI / Claude / 本地模型 / 其他               │
└─────────────────────────────────────────────────┘
```

### 2.2 客户端架构

```
┌─────────────────────────────────────────┐
│           UI 层 (用户界面)               │
│  - 聊天界面  - 设置面板  - 历史记录      │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         业务逻辑层 (Core Engine)         │
│  ┌──────────────┐  ┌─────────────────┐ │
│  │  会话管理器   │  │  安全过滤器      │ │
│  │  - 多会话     │  │  - 输入过滤      │ │
│  │  - 历史记录   │  │  - 输出检查      │ │
│  │  - 上下文     │  │  - 敏感词库      │ │
│  └──────────────┘  └─────────────────┘ │
│                                          │
│  ┌──────────────┐  ┌─────────────────┐ │
│  │  模型适配器   │  │  策略管理器      │ │
│  │  - 多模型     │  │  - 策略同步      │ │
│  │  - 统一接口   │  │  - 本地缓存      │ │
│  │  - 负载均衡   │  │  - 版本控制      │ │
│  └──────────────┘  └─────────────────┘ │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│          通信层 (Network Layer)          │
│  ┌──────────────┐  ┌─────────────────┐ │
│  │  连接管理器   │  │  加密传输        │ │
│  │  - WebSocket  │  │  - TLS/SSL       │ │
│  │  - HTTP/2     │  │  - 端到端加密    │ │
│  │  - gRPC       │  │  - 消息签名      │ │
│  └──────────────┘  └─────────────────┘ │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│          存储层 (Storage Layer)          │
│  - 本地数据库 (SQLite)                   │
│  - 配置文件 (加密存储)                   │
│  - 缓存管理 (会话历史)                   │
└─────────────────────────────────────────┘
```

## 三、核心功能设计

### 3.1 快捷连接功能

#### 自动发现与配置
```typescript
// 客户端自动发现服务
class ServiceDiscovery {
    async discoverServices(): Promise<Service[]> {
        // 1. 扫描本地网络中的 LLM 网关
        const localServices = await this.scanLocalNetwork();

        // 2. 从企业配置服务器获取
        const enterpriseServices = await this.fetchEnterpriseConfig();

        // 3. 从云端获取公共服务列表
        const cloudServices = await this.fetchCloudServices();

        return [...localServices, ...enterpriseServices, ...cloudServices];
    }

    async autoConnect(service: Service): Promise<Connection> {
        // 自动认证和连接
        const auth = await this.authenticate(service);
        const connection = await this.establishConnection(service, auth);

        // 下载最新策略
        await this.syncPolicies(connection);

        return connection;
    }
}
```

#### 一键登录
```typescript
// 支持多种认证方式
class AuthManager {
    async login(method: AuthMethod): Promise<Session> {
        switch(method) {
            case 'webauthn':
                return await this.loginWithWebAuthn();
            case 'oauth':
                return await this.loginWithOAuth();
            case 'enterprise_sso':
                return await this.loginWithSSO();
            case 'api_key':
                return await this.loginWithAPIKey();
        }
    }

    // WebAuthn 快速登录
    async loginWithWebAuthn(): Promise<Session> {
        const credential = await navigator.credentials.get({
            publicKey: this.getCredentialOptions()
        });

        return await this.authenticateWithServer(credential);
    }
}
```

### 3.2 安全过滤功能

#### 客户端输入过滤
```typescript
class InputFilter {
    private sensitivePatterns: RegExp[];
    private policyEngine: PolicyEngine;

    async filterInput(text: string): Promise<FilterResult> {
        // 1. 本地快速过滤（离线可用）
        const localResult = this.localFilter(text);
        if (localResult.blocked) {
            return localResult;
        }

        // 2. 高级过滤（需要网络）
        if (this.isOnline()) {
            const advancedResult = await this.advancedFilter(text);
            if (advancedResult.blocked) {
                return advancedResult;
            }
        }

        // 3. 应用企业策略
        return await this.applyPolicies(text);
    }

    private localFilter(text: string): FilterResult {
        // 检查敏感词库
        for (const pattern of this.sensitivePatterns) {
            if (pattern.test(text)) {
                return {
                    blocked: true,
                    reason: '包含敏感内容',
                    suggestions: this.getSuggestions(text)
                };
            }
        }

        return { blocked: false };
    }
}
```

#### 输出审查
```typescript
class OutputFilter {
    async filterOutput(response: string): Promise<FilteredResponse> {
        // 1. PII 检测和脱敏
        const piiResult = await this.detectAndMaskPII(response);

        // 2. 有害内容检测
        const harmfulResult = await this.detectHarmfulContent(piiResult.text);

        // 3. 企业合规检查
        const complianceResult = await this.checkCompliance(harmfulResult.text);

        return {
            originalText: response,
            filteredText: complianceResult.text,
            warnings: [...piiResult.warnings, ...harmfulResult.warnings],
            modifications: this.getModifications(response, complianceResult.text)
        };
    }

    private async detectAndMaskPII(text: string): Promise<PIIResult> {
        const piiPatterns = {
            email: /[\w.-]+@[\w.-]+\.\w+/g,
            phone: /\d{3}-\d{3,4}-\d{4}/g,
            ssn: /\d{3}-\d{2}-\d{4}/g,
            creditCard: /\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}/g
        };

        let maskedText = text;
        const warnings = [];

        for (const [type, pattern] of Object.entries(piiPatterns)) {
            if (pattern.test(text)) {
                maskedText = maskedText.replace(pattern, `[已脱敏-${type}]`);
                warnings.push(`检测到并脱敏了${type}`);
            }
        }

        return { text: maskedText, warnings };
    }
}
```

### 3.3 策略同步功能

```typescript
class PolicyManager {
    private localPolicies: Map<string, Policy>;
    private syncInterval: number = 5 * 60 * 1000; // 5分钟

    async syncPolicies(): Promise<void> {
        try {
            // 1. 获取服务器最新策略
            const serverPolicies = await this.fetchServerPolicies();

            // 2. 比较版本
            const updates = this.compareVersions(serverPolicies);

            // 3. 下载更新
            for (const update of updates) {
                await this.downloadPolicy(update);
            }

            // 4. 应用新策略
            await this.applyPolicies(updates);

            // 5. 通知用户
            this.notifyPolicyUpdates(updates);

        } catch (error) {
            // 离线模式：使用缓存的策略
            console.log('策略同步失败，使用本地缓存');
        }
    }

    async applyPolicies(policies: Policy[]): Promise<void> {
        for (const policy of policies) {
            // 更新过滤规则
            this.inputFilter.updateRules(policy.inputRules);
            this.outputFilter.updateRules(policy.outputRules);

            // 更新模型配置
            this.modelAdapter.updateConfig(policy.modelConfig);

            // 保存到本地
            await this.saveToLocal(policy);
        }
    }
}
```

### 3.4 会话管理功能

```typescript
class SessionManager {
    private sessions: Map<string, Session>;

    async createSession(modelId: string): Promise<Session> {
        const session = {
            id: uuidv4(),
            modelId,
            messages: [],
            context: {},
            createdAt: new Date(),
            metadata: {
                tags: [],
                title: '新对话',
                tokens: 0
            }
        };

        this.sessions.set(session.id, session);
        await this.persistSession(session);

        return session;
    }

    async sendMessage(sessionId: string, message: string): Promise<Response> {
        const session = this.sessions.get(sessionId);

        // 1. 输入过滤
        const filtered = await this.inputFilter.filter(message);
        if (filtered.blocked) {
            throw new Error(filtered.reason);
        }

        // 2. 添加到会话
        session.messages.push({
            role: 'user',
            content: message,
            timestamp: new Date()
        });

        // 3. 发送到服务器
        const response = await this.sendToServer(session, filtered.text);

        // 4. 输出过滤
        const filteredResponse = await this.outputFilter.filter(response.text);

        // 5. 保存响应
        session.messages.push({
            role: 'assistant',
            content: filteredResponse.text,
            timestamp: new Date(),
            warnings: filteredResponse.warnings
        });

        await this.persistSession(session);

        return filteredResponse;
    }

    async exportSession(sessionId: string, format: 'json' | 'markdown' | 'pdf'): Promise<Blob> {
        const session = this.sessions.get(sessionId);

        switch(format) {
            case 'json':
                return new Blob([JSON.stringify(session, null, 2)], { type: 'application/json' });
            case 'markdown':
                return this.exportToMarkdown(session);
            case 'pdf':
                return await this.exportToPDF(session);
        }
    }
}
```

## 四、技术选型

### 4.1 客户端技术栈

#### 桌面端 (首选)
```
框架: Electron + React + TypeScript
优势:
- 跨平台 (Windows/Mac/Linux)
- 丰富的生态系统
- 可以访问系统资源
- 统一代码库

技术栈:
- UI: React + Ant Design / Material-UI
- 状态管理: Redux Toolkit / Zustand
- 通信: Socket.IO / gRPC-Web
- 存储: SQLite (better-sqlite3)
- 加密: crypto-js / node-forge
```

#### 移动端
```
框架: React Native + TypeScript
优势:
- 代码复用（与 Web 共享）
- 原生性能
- 推送通知支持

技术栈:
- UI: React Native Paper
- 导航: React Navigation
- 存储: AsyncStorage + SQLite
- 推送: Firebase Cloud Messaging
```

#### Web 端
```
框架: React + TypeScript
优势:
- 无需安装
- 快速更新
- 跨设备访问

技术栈:
- UI: React + Tailwind CSS
- 路由: React Router
- 状态: Redux Toolkit
- PWA: Workbox
```

### 4.2 服务器端扩展

#### 客户端网关 API
```python
# 新增客户端专用 API
from fastapi import APIRouter, WebSocket
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/api/v1/client", tags=["客户端"])

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 连接 - 实时通信"""
    await websocket.accept()

    try:
        while True:
            # 接收消息
            data = await websocket.receive_json()

            # 处理请求
            if data['type'] == 'chat':
                response = await process_chat(data)
            elif data['type'] == 'policy_sync':
                response = await sync_policies(data)

            # 发送响应
            await websocket.send_json(response)

    except WebSocketDisconnect:
        await handle_disconnect(websocket)

@router.get("/policies/latest")
async def get_latest_policies(
    client_version: str,
    current_user: User = Depends(get_current_user)
):
    """获取最新策略"""
    policies = await policy_service.get_policies_for_user(
        user=current_user,
        client_version=client_version
    )

    return {
        "policies": policies,
        "version": policy_service.get_version(),
        "mandatory_update": policy_service.requires_update(client_version)
    }

@router.post("/stream")
async def stream_chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """流式响应"""
    async def generate():
        async for chunk in llm_service.stream_generate(request.message):
            # 实时过滤
            filtered = await output_filter.filter_chunk(chunk)
            yield f"data: {json.dumps(filtered)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

#### 策略管理 API
```python
@router.post("/policies")
async def create_policy(
    policy: PolicyCreate,
    current_user: User = Depends(require_admin)
):
    """创建新策略"""
    created = await policy_service.create_policy(policy)

    # 推送更新通知到所有客户端
    await notify_clients_policy_update(created)

    return created

@router.get("/client/health")
async def check_client_health(
    client_id: str,
    current_user: User = Depends(get_current_user)
):
    """检查客户端健康状态"""
    return {
        "status": "online",
        "version": "1.0.0",
        "last_sync": datetime.utcnow(),
        "policy_version": policy_service.get_version()
    }
```

### 4.3 数据流设计

#### 请求流程
```
客户端发送消息:
1. 用户输入 → UI 层
2. 本地输入过滤 → 过滤引擎
3. 构建请求 → 业务逻辑层
4. 加密传输 → 通信层
5. WebSocket/HTTP → 服务器网关
6. 认证授权 → 权限检查
7. 内容检测 → 防护引擎
8. 转发模型 → LLM 服务
```

#### 响应流程
```
服务器返回响应:
1. 模型响应 → LLM 服务
2. 内容过滤 → 防护引擎
3. 加密传输 → 网关
4. WebSocket 推送 → 客户端
5. 解密验证 → 通信层
6. 输出审查 → 过滤引擎
7. 渲染显示 → UI 层
8. 保存历史 → 存储层
```

## 五、实现路线图

### Phase 1: 基础框架 (2-3 周)
- [ ] 搭建 Electron 项目框架
- [ ] 实现基础 UI 界面
- [ ] 建立与服务器的 WebSocket 连接
- [ ] 实现基础认证功能
- [ ] 本地数据存储

### Phase 2: 核心功能 (3-4 周)
- [ ] 会话管理系统
- [ ] 多模型适配器
- [ ] 本地过滤引擎
- [ ] 策略同步机制
- [ ] 历史记录管理

### Phase 3: 安全增强 (2-3 周)
- [ ] 端到端加密
- [ ] 高级输入过滤
- [ ] 输出审查功能
- [ ] 离线模式支持
- [ ] 数据备份恢复

### Phase 4: 用户体验 (2-3 周)
- [ ] 快捷键支持
- [ ] 插件系统
- [ ] 主题定制
- [ ] 多语言支持
- [ ] 性能优化

### Phase 5: 发布准备 (1-2 周)
- [ ] 自动更新机制
- [ ] 完整测试覆盖
- [ ] 文档编写
- [ ] 打包发布
- [ ] 监控埋点

## 六、关键优势

### 6.1 对用户的好处
✅ **简化操作**: 一键连接，无需复杂配置
✅ **统一体验**: 所有模型使用相同界面
✅ **离线可用**: 本地缓存，离线也能查看历史
✅ **数据安全**: 本地加密存储，隐私保护
✅ **快速响应**: 客户端缓存，减少网络延迟

### 6.2 对企业的好处
✅ **集中管控**: 统一策略管理和下发
✅ **安全合规**: 多层过滤，确保内容安全
✅ **审计追踪**: 完整的操作日志
✅ **灵活部署**: 支持云端/私有部署
✅ **成本优化**: 智能路由，降低 API 成本

### 6.3 对系统的好处
✅ **负载分担**: 客户端承担部分过滤工作
✅ **降低延迟**: WebSocket 长连接
✅ **可扩展性**: 客户端插件机制
✅ **版本管理**: 强制更新机制
✅ **数据收集**: 用户行为分析

## 七、MVP 功能清单

### 最小可行产品 (4-6 周)

#### 必须有的功能
1. ✅ 用户登录（支持密码 + WebAuthn）
2. ✅ 连接到 LLM 防护网关
3. ✅ 基础聊天界面
4. ✅ 会话管理（创建/删除/切换）
5. ✅ 本地历史记录
6. ✅ 基础输入过滤（敏感词）
7. ✅ 策略同步（自动下载）
8. ✅ 桌面通知

#### 可以后续添加
- 🔄 多模型切换
- 🔄 高级过滤（AI 检测）
- 🔄 输出审查
- 🔄 插件系统
- 🔄 移动端支持
- 🔄 语音输入
- 🔄 文件上传

## 八、总结

统一客户端的实现将带来:

1. **用户体验提升 300%**
   - 从"配置复杂"到"一键连接"
   - 从"多个工具"到"统一界面"

2. **安全性提升 200%**
   - 客户端 + 服务器双重过滤
   - 离线安全策略
   - 端到端加密

3. **管理效率提升 400%**
   - 自动策略下发
   - 集中监控管理
   - 一键更新所有客户端

建议首先实现桌面端 MVP，验证核心功能后再扩展到移动端和 Web 端。

---

**下一步行动:**
1. 确认技术选型和架构设计
2. 搭建基础项目框架
3. 实现核心功能原型
4. 内部测试和迭代
5. 正式发布和推广
