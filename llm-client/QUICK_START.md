# LLM 防护客户端 - 快速启动指南

## 🚀 快速开始

### 1. 安装依赖

```bash
cd llm-client
export ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
npm install
```

> **注意**: 如果遇到网络问题,使用上面的国内镜像加速 Electron 下载

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件,设置服务器地址:

```env
VITE_DEFAULT_SERVER_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000/ws
```

### 3. 启动开发服务器

```bash
npm run dev
```

这将启动 Vite 开发服务器在 http://localhost:5173

### 4. 启动 Electron 应用

**方式一**: 在新终端窗口运行

```bash
npm run electron:dev
```

**方式二**: 使用并发模式(推荐)

```bash
npm run dev
```

会自动启动 Vite 和 Electron

## 📦 项目结构

```
llm-client/
├── electron/                    # Electron 主进程
│   ├── main.ts                 # 主进程入口
│   └── preload.ts              # 预加载脚本
│
├── src/                        # React 应用
│   ├── components/             # UI 组件
│   │   └── Chat/              # 聊天组件
│   │       ├── SessionList.tsx # 会话列表
│   │       ├── MessageList.tsx # 消息列表
│   │       └── InputBox.tsx    # 输入框
│   │
│   ├── pages/                  # 页面
│   │   ├── Login.tsx          # 登录页
│   │   ├── Chat.tsx           # 聊天页
│   │   └── Settings.tsx       # 设置页
│   │
│   ├── services/               # 核心服务
│   │   ├── api/
│   │   │   └── gateway.ts     # WebSocket 连接
│   │   ├── filter/
│   │   │   └── input-filter.ts # 本地过滤
│   │   └── policy/
│   │       └── policy-manager.ts # 策略管理
│   │
│   ├── store/                  # 状态管理
│   │   ├── useAuthStore.ts    # 认证状态
│   │   └── useChatStore.ts    # 聊天状态
│   │
│   ├── types/                  # TypeScript 类型
│   │   ├── api.ts
│   │   ├── chat.ts
│   │   └── policy.ts
│   │
│   ├── App.tsx                 # 应用入口
│   └── main.tsx                # React 入口
│
├── index.html                  # HTML 模板
├── package.json                # 依赖配置
├── tsconfig.json               # TypeScript 配置
└── vite.config.ts              # Vite 配置
```

## 🔧 核心功能说明

### 1. WebSocket 连接管理

**文件**: `src/services/api/gateway.ts`

```typescript
import { gatewayClient } from '@/services/api/gateway';

// 连接到服务器
await gatewayClient.connect(serverUrl, token);

// 发送消息
await gatewayClient.sendMessage(sessionId, message);

// 流式响应
await gatewayClient.streamMessage(sessionId, message, (chunk) => {
  console.log('收到分块:', chunk);
});

// 断开连接
gatewayClient.disconnect();
```

### 2. 本地过滤引擎

**文件**: `src/services/filter/input-filter.ts`

```typescript
import { inputFilter } from '@/services/filter/input-filter';

// 加载策略
inputFilter.loadPolicy(policy);

// 过滤文本
const result = await inputFilter.filter(text);
if (result.blocked) {
  console.log('被拦截:', result.reason);
}
```

### 3. 策略同步管理

**文件**: `src/services/policy/policy-manager.ts`

```typescript
import { policyManager } from '@/services/policy/policy-manager';

// 初始化
await policyManager.initialize();

// 手动同步
await policyManager.sync();

// 监听更新
const unsubscribe = policyManager.onPolicyUpdate((policy) => {
  console.log('策略已更新:', policy);
});
```

### 4. 会话管理

**文件**: `src/store/useChatStore.ts`

```typescript
import { useChatStore } from '@/store/useChatStore';

const {
  sessions,                    // 所有会话
  currentSessionId,            // 当前会话 ID
  createSession,               // 创建会话
  deleteSession,               // 删除会话
  addMessage,                  // 添加消息
  exportSession,               // 导出会话
} = useChatStore();
```

## 🎨 UI 组件使用

### SessionList - 会话列表

```tsx
<SessionList
  sessions={sessions}
  currentSessionId={currentSessionId}
  onSelectSession={setCurrentSession}
  onCreateSession={handleCreateSession}
  onDeleteSession={handleDeleteSession}
/>
```

### MessageList - 消息列表

```tsx
<MessageList
  messages={messages}
  loading={loading}
  streamingText={streamingText}  // 流式响应文本
/>
```

### InputBox - 输入框

```tsx
<InputBox
  onSend={handleSendMessage}
  disabled={!connected}
  loading={loading}
/>
```

## 🔐 认证流程

### 1. 登录

```typescript
import { useAuthStore } from '@/store/useAuthStore';

const { login } = useAuthStore();

// 登录成功后
login(token, user, serverUrl);
```

### 2. 自动认证

应用启动时会自动从 localStorage 恢复认证状态:

```typescript
// App.tsx
const { initAuth } = useAuthStore();

useEffect(() => {
  initAuth();
}, []);
```

### 3. 登出

```typescript
const { logout } = useAuthStore();

logout();  // 清除认证信息
```

## 🛠️ 开发技巧

### TypeScript 类型检查

```bash
npm run type-check
```

### 代码格式化

```bash
npm run format
```

### 代码检查

```bash
npm run lint
```

## 📦 打包发布

### 开发构建

```bash
npm run build
```

### 生产构建

```bash
# Windows
npm run build:win

# macOS
npm run build:mac

# Linux
npm run build:linux
```

构建产物位于 `release/` 目录

## ⚠️ 常见问题

### 1. 依赖安装失败

**问题**: better-sqlite3 或 Electron 安装失败

**解决**:
```bash
# 使用国内镜像
export ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
npm install
```

### 2. Xcode 许可协议问题

**问题**: 需要编译原生模块,但未同意 Xcode 许可

**解决**:
```bash
sudo xcodebuild -license
```

### 3. WebSocket 连接失败

**问题**: 无法连接到服务器

**检查**:
- 服务器地址是否正确
- 服务器是否运行
- 网络是否畅通
- 防火墙设置

### 4. 类型错误

**问题**: TypeScript 类型检查报错

**解决**:
```bash
# 检查类型错误
npm run type-check

# 查看具体错误信息
tsc --noEmit
```

## 🔗 相关文档

- [设计文档](../docs/unified-client-design.md)
- [实现指南](../docs/unified-client-implementation.md)
- [Electron 文档](https://www.electronjs.org/docs)
- [React 文档](https://react.dev/)
- [Vite 文档](https://vitejs.dev/)

## 📞 技术支持

遇到问题请查看:
1. 项目 README
2. 相关技术文档
3. GitHub Issues
