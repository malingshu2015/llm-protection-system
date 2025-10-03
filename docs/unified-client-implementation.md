# 统一客户端技术实现方案

## 一、快速开始原型

### 1.1 技术栈选择（推荐）

```
桌面端 (Electron)
├── 前端框架: React 18 + TypeScript
├── UI 组件: Ant Design 5 / Chakra UI
├── 状态管理: Zustand (轻量) / Redux Toolkit (复杂场景)
├── 路由管理: React Router 6
├── 通信层: Socket.IO-client / gRPC-Web
├── 本地存储: better-sqlite3 + IndexedDB
├── 加密库: crypto-js / tweetnacl
└── 打包工具: electron-builder
```

### 1.2 项目结构

```
llm-client/
├── electron/                    # Electron 主进程
│   ├── main.ts                 # 主进程入口
│   ├── preload.ts              # 预加载脚本
│   ├── ipc/                    # IPC 通信
│   │   ├── auth.ts            # 认证相关
│   │   ├── chat.ts            # 聊天相关
│   │   └── storage.ts         # 存储相关
│   └── services/               # 后台服务
│       ├── auto-updater.ts    # 自动更新
│       ├── tray.ts            # 托盘管理
│       └── shortcuts.ts       # 快捷键
│
├── src/                        # React 应用
│   ├── components/            # UI 组件
│   │   ├── Chat/             # 聊天组件
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── InputBox.tsx
│   │   │   └── SessionList.tsx
│   │   ├── Settings/         # 设置组件
│   │   └── Auth/             # 认证组件
│   │
│   ├── services/              # 业务服务
│   │   ├── api/              # API 客户端
│   │   │   ├── gateway.ts    # 网关 API
│   │   │   ├── chat.ts       # 聊天 API
│   │   │   └── policy.ts     # 策略 API
│   │   ├── filter/           # 过滤引擎
│   │   │   ├── input-filter.ts
│   │   │   └── output-filter.ts
│   │   ├── storage/          # 存储服务
│   │   │   ├── session-store.ts
│   │   │   └── config-store.ts
│   │   └── security/         # 安全服务
│   │       ├── encryption.ts
│   │       └── auth.ts
│   │
│   ├── store/                 # 状态管理
│   │   ├── useAuthStore.ts
│   │   ├── useChatStore.ts
│   │   └── useSettingsStore.ts
│   │
│   ├── types/                 # TypeScript 类型
│   │   ├── api.ts
│   │   ├── chat.ts
│   │   └── policy.ts
│   │
│   └── utils/                 # 工具函数
│       ├── crypto.ts
│       ├── logger.ts
│       └── validators.ts
│
├── server/                     # 服务器端扩展
│   └── client-gateway/        # 客户端专用网关
│       ├── websocket.py       # WebSocket 服务
│       ├── policy.py          # 策略管理
│       └── streaming.py       # 流式响应
│
└── shared/                     # 共享代码
    ├── protocols/             # 通信协议
    └── constants/             # 常量定义
```

## 二、核心功能实现

### 2.1 连接管理器

```typescript
// src/services/api/gateway.ts
import { io, Socket } from 'socket.io-client';

export class GatewayClient {
    private socket: Socket | null = null;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;

    async connect(serverUrl: string, token: string): Promise<void> {
        return new Promise((resolve, reject) => {
            this.socket = io(serverUrl, {
                auth: { token },
                transports: ['websocket'],
                reconnection: true,
                reconnectionDelay: 1000,
                reconnectionAttempts: this.maxReconnectAttempts
            });

            this.socket.on('connect', () => {
                console.log('✅ 已连接到服务器');
                this.reconnectAttempts = 0;
                resolve();
            });

            this.socket.on('disconnect', (reason) => {
                console.log('❌ 连接断开:', reason);
                if (reason === 'io server disconnect') {
                    // 服务器主动断开，需要重新认证
                    this.reconnect(serverUrl, token);
                }
            });

            this.socket.on('connect_error', (error) => {
                console.error('连接错误:', error);
                this.reconnectAttempts++;

                if (this.reconnectAttempts >= this.maxReconnectAttempts) {
                    reject(new Error('连接失败，请检查网络'));
                }
            });

            // 策略更新事件
            this.socket.on('policy_update', (policy) => {
                this.handlePolicyUpdate(policy);
            });

            // 强制下线事件
            this.socket.on('force_logout', (reason) => {
                this.handleForceLogout(reason);
            });
        });
    }

    async sendMessage(sessionId: string, message: string): Promise<string> {
        return new Promise((resolve, reject) => {
            if (!this.socket?.connected) {
                reject(new Error('未连接到服务器'));
                return;
            }

            this.socket.emit('chat:message', {
                sessionId,
                message,
                timestamp: Date.now()
            }, (response: any) => {
                if (response.error) {
                    reject(new Error(response.error));
                } else {
                    resolve(response.reply);
                }
            });
        });
    }

    // 流式响应
    async streamMessage(
        sessionId: string,
        message: string,
        onChunk: (chunk: string) => void
    ): Promise<void> {
        if (!this.socket?.connected) {
            throw new Error('未连接到服务器');
        }

        return new Promise((resolve, reject) => {
            const streamId = `stream_${Date.now()}`;

            this.socket!.emit('chat:stream', {
                streamId,
                sessionId,
                message
            });

            this.socket!.on(`stream:${streamId}:chunk`, (chunk) => {
                onChunk(chunk.data);
            });

            this.socket!.on(`stream:${streamId}:end`, () => {
                this.socket!.off(`stream:${streamId}:chunk`);
                this.socket!.off(`stream:${streamId}:end`);
                this.socket!.off(`stream:${streamId}:error`);
                resolve();
            });

            this.socket!.on(`stream:${streamId}:error`, (error) => {
                this.socket!.off(`stream:${streamId}:chunk`);
                this.socket!.off(`stream:${streamId}:end`);
                this.socket!.off(`stream:${streamId}:error`);
                reject(new Error(error.message));
            });
        });
    }

    disconnect(): void {
        this.socket?.disconnect();
        this.socket = null;
    }
}
```

### 2.2 本地过滤引擎

```typescript
// src/services/filter/input-filter.ts
import { Policy, FilterResult } from '@/types';

export class InputFilter {
    private sensitivePatterns: Map<string, RegExp> = new Map();
    private blockedKeywords: Set<string> = new Set();
    private policy: Policy | null = null;

    loadPolicy(policy: Policy): void {
        this.policy = policy;

        // 编译正则表达式
        this.sensitivePatterns.clear();
        for (const [name, pattern] of Object.entries(policy.patterns)) {
            this.sensitivePatterns.set(name, new RegExp(pattern, 'gi'));
        }

        // 加载敏感词
        this.blockedKeywords = new Set(policy.keywords);
    }

    async filter(text: string): Promise<FilterResult> {
        // 1. 快速检查：敏感词
        const keywordCheck = this.checkKeywords(text);
        if (keywordCheck.blocked) {
            return keywordCheck;
        }

        // 2. 模式匹配检查
        const patternCheck = this.checkPatterns(text);
        if (patternCheck.blocked) {
            return patternCheck;
        }

        // 3. 自定义规则检查
        if (this.policy?.customRules) {
            const customCheck = await this.checkCustomRules(text);
            if (customCheck.blocked) {
                return customCheck;
            }
        }

        return {
            blocked: false,
            text,
            confidence: 1.0
        };
    }

    private checkKeywords(text: string): FilterResult {
        const lowerText = text.toLowerCase();

        for (const keyword of this.blockedKeywords) {
            if (lowerText.includes(keyword.toLowerCase())) {
                return {
                    blocked: true,
                    reason: `包含敏感词: ${keyword}`,
                    suggestions: [
                        '请重新表述您的问题',
                        '避免使用敏感词汇'
                    ],
                    text,
                    confidence: 1.0
                };
            }
        }

        return { blocked: false, text, confidence: 1.0 };
    }

    private checkPatterns(text: string): FilterResult {
        for (const [name, pattern] of this.sensitivePatterns) {
            const matches = text.match(pattern);
            if (matches) {
                return {
                    blocked: true,
                    reason: `匹配到敏感模式: ${name}`,
                    matches: matches.map(m => ({ text: m, pattern: name })),
                    text,
                    confidence: 0.9
                };
            }
        }

        return { blocked: false, text, confidence: 1.0 };
    }

    private async checkCustomRules(text: string): Promise<FilterResult> {
        // 执行自定义 JavaScript 规则
        try {
            for (const rule of this.policy!.customRules!) {
                const fn = new Function('text', rule.code);
                const result = fn(text);

                if (result.blocked) {
                    return {
                        blocked: true,
                        reason: result.reason || '违反自定义规则',
                        text,
                        confidence: result.confidence || 0.8
                    };
                }
            }
        } catch (error) {
            console.error('自定义规则执行失败:', error);
        }

        return { blocked: false, text, confidence: 1.0 };
    }
}
```

### 2.3 会话管理

```typescript
// src/store/useChatStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Message, Session } from '@/types';
import { v4 as uuidv4 } from 'uuid';

interface ChatState {
    sessions: Map<string, Session>;
    currentSessionId: string | null;

    // Actions
    createSession: (modelId: string, title?: string) => Session;
    deleteSession: (sessionId: string) => void;
    setCurrentSession: (sessionId: string) => void;
    addMessage: (sessionId: string, message: Message) => void;
    updateMessage: (sessionId: string, messageId: string, updates: Partial<Message>) => void;
    clearHistory: (sessionId: string) => void;
    exportSession: (sessionId: string, format: 'json' | 'markdown') => Promise<Blob>;
}

export const useChatStore = create<ChatState>()(
    persist(
        (set, get) => ({
            sessions: new Map(),
            currentSessionId: null,

            createSession: (modelId: string, title?: string) => {
                const session: Session = {
                    id: uuidv4(),
                    modelId,
                    title: title || '新对话',
                    messages: [],
                    createdAt: new Date(),
                    updatedAt: new Date(),
                    metadata: {
                        tags: [],
                        tokens: 0,
                        cost: 0
                    }
                };

                set((state) => ({
                    sessions: new Map(state.sessions).set(session.id, session),
                    currentSessionId: session.id
                }));

                return session;
            },

            deleteSession: (sessionId: string) => {
                set((state) => {
                    const newSessions = new Map(state.sessions);
                    newSessions.delete(sessionId);

                    const newCurrentId = state.currentSessionId === sessionId
                        ? Array.from(newSessions.keys())[0] || null
                        : state.currentSessionId;

                    return {
                        sessions: newSessions,
                        currentSessionId: newCurrentId
                    };
                });
            },

            setCurrentSession: (sessionId: string) => {
                set({ currentSessionId: sessionId });
            },

            addMessage: (sessionId: string, message: Message) => {
                set((state) => {
                    const session = state.sessions.get(sessionId);
                    if (!session) return state;

                    const updatedSession = {
                        ...session,
                        messages: [...session.messages, message],
                        updatedAt: new Date(),
                        metadata: {
                            ...session.metadata,
                            tokens: session.metadata.tokens + (message.tokens || 0)
                        }
                    };

                    return {
                        sessions: new Map(state.sessions).set(sessionId, updatedSession)
                    };
                });
            },

            updateMessage: (sessionId: string, messageId: string, updates: Partial<Message>) => {
                set((state) => {
                    const session = state.sessions.get(sessionId);
                    if (!session) return state;

                    const messages = session.messages.map(msg =>
                        msg.id === messageId ? { ...msg, ...updates } : msg
                    );

                    const updatedSession = { ...session, messages, updatedAt: new Date() };

                    return {
                        sessions: new Map(state.sessions).set(sessionId, updatedSession)
                    };
                });
            },

            clearHistory: (sessionId: string) => {
                set((state) => {
                    const session = state.sessions.get(sessionId);
                    if (!session) return state;

                    const clearedSession = {
                        ...session,
                        messages: [],
                        updatedAt: new Date(),
                        metadata: { ...session.metadata, tokens: 0, cost: 0 }
                    };

                    return {
                        sessions: new Map(state.sessions).set(sessionId, clearedSession)
                    };
                });
            },

            exportSession: async (sessionId: string, format: 'json' | 'markdown') => {
                const session = get().sessions.get(sessionId);
                if (!session) throw new Error('会话不存在');

                if (format === 'json') {
                    return new Blob(
                        [JSON.stringify(session, null, 2)],
                        { type: 'application/json' }
                    );
                } else {
                    const markdown = session.messages.map(msg =>
                        `**${msg.role === 'user' ? '用户' : '助手'}** (${new Date(msg.timestamp).toLocaleString()}):\n\n${msg.content}\n\n---\n`
                    ).join('\n');

                    return new Blob([markdown], { type: 'text/markdown' });
                }
            }
        }),
        {
            name: 'chat-storage',
            // 序列化 Map
            serialize: (state) => JSON.stringify({
                ...state,
                sessions: Array.from(state.sessions.entries())
            }),
            // 反序列化 Map
            deserialize: (str) => {
                const parsed = JSON.parse(str);
                return {
                    ...parsed,
                    sessions: new Map(parsed.sessions)
                };
            }
        }
    )
);
```

### 2.4 策略同步

```typescript
// src/services/policy/policy-manager.ts
import { Policy } from '@/types';
import { GatewayClient } from '../api/gateway';

export class PolicyManager {
    private currentPolicy: Policy | null = null;
    private syncInterval: NodeJS.Timeout | null = null;
    private listeners: Set<(policy: Policy) => void> = new Set();

    constructor(private gateway: GatewayClient) {}

    async initialize(): Promise<void> {
        // 1. 从本地加载缓存的策略
        const cachedPolicy = await this.loadFromCache();
        if (cachedPolicy) {
            this.currentPolicy = cachedPolicy;
            this.notifyListeners();
        }

        // 2. 同步最新策略
        await this.sync();

        // 3. 启动定时同步
        this.startAutoSync();
    }

    async sync(): Promise<Policy> {
        try {
            const response = await this.gateway.request<{ policy: Policy }>({
                method: 'GET',
                path: '/api/v1/client/policies/latest',
                params: {
                    client_version: process.env.APP_VERSION,
                    current_policy_version: this.currentPolicy?.version
                }
            });

            const newPolicy = response.policy;

            // 检查是否有更新
            if (!this.currentPolicy || newPolicy.version > this.currentPolicy.version) {
                this.currentPolicy = newPolicy;
                await this.saveToCache(newPolicy);
                this.notifyListeners();

                console.log(`✅ 策略已更新到版本 ${newPolicy.version}`);
            }

            return newPolicy;

        } catch (error) {
            console.error('策略同步失败:', error);

            // 使用缓存的策略
            if (this.currentPolicy) {
                console.log('⚠️ 使用本地缓存的策略');
                return this.currentPolicy;
            }

            throw new Error('无法获取安全策略，请检查网络连接');
        }
    }

    private startAutoSync(): void {
        // 每 5 分钟同步一次
        this.syncInterval = setInterval(() => {
            this.sync().catch(console.error);
        }, 5 * 60 * 1000);
    }

    onPolicyUpdate(callback: (policy: Policy) => void): () => void {
        this.listeners.add(callback);
        // 返回取消监听函数
        return () => this.listeners.delete(callback);
    }

    private notifyListeners(): void {
        if (this.currentPolicy) {
            this.listeners.forEach(cb => cb(this.currentPolicy!));
        }
    }

    private async loadFromCache(): Promise<Policy | null> {
        try {
            const cached = localStorage.getItem('cached_policy');
            return cached ? JSON.parse(cached) : null;
        } catch {
            return null;
        }
    }

    private async saveToCache(policy: Policy): Promise<void> {
        localStorage.setItem('cached_policy', JSON.stringify(policy));
    }

    getCurrentPolicy(): Policy | null {
        return this.currentPolicy;
    }

    destroy(): void {
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
        }
        this.listeners.clear();
    }
}
```

## 三、UI 组件实现

### 3.1 聊天窗口

```tsx
// src/components/Chat/ChatWindow.tsx
import React, { useState, useRef, useEffect } from 'react';
import { useChatStore } from '@/store/useChatStore';
import { GatewayClient } from '@/services/api/gateway';
import { InputFilter } from '@/services/filter/input-filter';
import { MessageList } from './MessageList';
import { InputBox } from './InputBox';

export const ChatWindow: React.FC = () => {
    const { currentSessionId, addMessage } = useChatStore();
    const [isStreaming, setIsStreaming] = useState(false);
    const [streamingText, setStreamingText] = useState('');
    const gatewayRef = useRef<GatewayClient>();
    const filterRef = useRef<InputFilter>();

    const handleSendMessage = async (text: string) => {
        if (!currentSessionId || !gatewayRef.current) return;

        // 1. 本地过滤
        const filterResult = await filterRef.current?.filter(text);
        if (filterResult?.blocked) {
            // 显示错误提示
            notification.error({
                message: '内容被拦截',
                description: filterResult.reason,
                duration: 3
            });
            return;
        }

        // 2. 添加用户消息
        const userMessage = {
            id: `msg_${Date.now()}`,
            role: 'user' as const,
            content: text,
            timestamp: new Date()
        };
        addMessage(currentSessionId, userMessage);

        // 3. 发送到服务器（流式响应）
        setIsStreaming(true);
        setStreamingText('');

        try {
            await gatewayRef.current.streamMessage(
                currentSessionId,
                text,
                (chunk) => {
                    setStreamingText(prev => prev + chunk);
                }
            );

            // 4. 添加助手回复
            const assistantMessage = {
                id: `msg_${Date.now()}`,
                role: 'assistant' as const,
                content: streamingText,
                timestamp: new Date()
            };
            addMessage(currentSessionId, assistantMessage);

        } catch (error) {
            notification.error({
                message: '发送失败',
                description: error instanceof Error ? error.message : '未知错误'
            });
        } finally {
            setIsStreaming(false);
            setStreamingText('');
        }
    };

    return (
        <div className="chat-window">
            <MessageList
                sessionId={currentSessionId}
                streamingText={isStreaming ? streamingText : undefined}
            />
            <InputBox
                onSend={handleSendMessage}
                disabled={isStreaming}
            />
        </div>
    );
};
```

### 3.2 输入框

```tsx
// src/components/Chat/InputBox.tsx
import React, { useState, useRef, KeyboardEvent } from 'react';
import { Button, Tooltip } from 'antd';
import { SendOutlined, PaperClipOutlined } from '@ant-design/icons';

interface InputBoxProps {
    onSend: (text: string) => void;
    disabled?: boolean;
}

export const InputBox: React.FC<InputBoxProps> = ({ onSend, disabled }) => {
    const [text, setText] = useState('');
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const handleSend = () => {
        if (!text.trim() || disabled) return;

        onSend(text);
        setText('');

        // 重置高度
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
        }
    };

    const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
        // Ctrl/Cmd + Enter 发送
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            handleSend();
        }
    };

    const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
        setText(e.target.value);

        // 自动调整高度
        const textarea = e.target;
        textarea.style.height = 'auto';
        textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    };

    return (
        <div className="input-box">
            <div className="input-wrapper">
                <Tooltip title="附加文件">
                    <Button
                        type="text"
                        icon={<PaperClipOutlined />}
                        className="attach-btn"
                    />
                </Tooltip>

                <textarea
                    ref={textareaRef}
                    value={text}
                    onChange={handleInput}
                    onKeyDown={handleKeyDown}
                    placeholder="输入消息... (Ctrl+Enter 发送)"
                    disabled={disabled}
                    rows={1}
                    className="message-input"
                />

                <Button
                    type="primary"
                    icon={<SendOutlined />}
                    onClick={handleSend}
                    disabled={!text.trim() || disabled}
                    className="send-btn"
                >
                    发送
                </Button>
            </div>

            <div className="input-footer">
                <span className="hint">
                    {text.length} 字符 | Ctrl+Enter 发送
                </span>
            </div>
        </div>
    );
};
```

## 四、服务器端扩展

### 4.1 WebSocket 服务

```python
# server/client-gateway/websocket.py
from fastapi import WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import json
import asyncio

class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str, client_id: str):
        """建立连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket

        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(client_id)

        logger.info(f"客户端已连接: user={user_id}, client={client_id}")

    def disconnect(self, client_id: str, user_id: str):
        """断开连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

        if user_id in self.user_connections:
            self.user_connections[user_id].discard(client_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        logger.info(f"客户端已断开: client={client_id}")

    async def send_to_client(self, client_id: str, message: dict):
        """发送消息到指定客户端"""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

    async def broadcast_to_user(self, user_id: str, message: dict):
        """广播消息到用户的所有客户端"""
        if user_id in self.user_connections:
            tasks = [
                self.send_to_client(client_id, message)
                for client_id in self.user_connections[user_id]
            ]
            await asyncio.gather(*tasks)

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    client_id: str = Query(...)
):
    """WebSocket 端点"""
    try:
        # 验证 token
        user = await auth_service.verify_token(token)
        if not user:
            await websocket.close(code=4001, reason="未授权")
            return

        # 建立连接
        await manager.connect(websocket, user.id, client_id)

        # 发送欢迎消息
        await websocket.send_json({
            "type": "connected",
            "user": user.dict(),
            "server_time": datetime.utcnow().isoformat()
        })

        # 消息循环
        while True:
            data = await websocket.receive_json()
            await handle_message(websocket, user, data)

    except WebSocketDisconnect:
        manager.disconnect(client_id, user.id)
    except Exception as e:
        logger.error(f"WebSocket 错误: {str(e)}")
        await websocket.close(code=1011, reason="服务器错误")

async def handle_message(websocket: WebSocket, user: User, data: dict):
    """处理客户端消息"""
    msg_type = data.get("type")

    if msg_type == "chat:message":
        await handle_chat_message(websocket, user, data)

    elif msg_type == "chat:stream":
        await handle_stream_message(websocket, user, data)

    elif msg_type == "policy:sync":
        await handle_policy_sync(websocket, user, data)

    elif msg_type == "ping":
        await websocket.send_json({"type": "pong", "timestamp": data.get("timestamp")})

async def handle_stream_message(websocket: WebSocket, user: User, data: dict):
    """处理流式消息"""
    stream_id = data["streamId"]
    session_id = data["sessionId"]
    message = data["message"]

    try:
        # 输入过滤
        filtered = await security_service.filter_input(message, user)
        if filtered.blocked:
            await websocket.send_json({
                "type": f"stream:{stream_id}:error",
                "error": {"message": filtered.reason}
            })
            return

        # 流式生成
        async for chunk in llm_service.stream_generate(filtered.text, user):
            # 输出过滤
            filtered_chunk = await security_service.filter_output(chunk, user)

            # 发送分块
            await websocket.send_json({
                "type": f"stream:{stream_id}:chunk",
                "data": filtered_chunk.text,
                "metadata": filtered_chunk.metadata
            })

        # 发送结束信号
        await websocket.send_json({
            "type": f"stream:{stream_id}:end"
        })

    except Exception as e:
        await websocket.send_json({
            "type": f"stream:{stream_id}:error",
            "error": {"message": str(e)}
        })

# 策略更新推送
async def push_policy_update(user_id: str, policy: dict):
    """推送策略更新到客户端"""
    await manager.broadcast_to_user(user_id, {
        "type": "policy_update",
        "policy": policy,
        "timestamp": datetime.utcnow().isoformat()
    })
```

## 五、打包与分发

### 5.1 Electron 打包配置

```javascript
// electron-builder.config.js
module.exports = {
    appId: 'com.llm.protection.client',
    productName: 'LLM 防护客户端',
    copyright: 'Copyright © 2024',

    directories: {
        output: 'dist',
        buildResources: 'build'
    },

    files: [
        'dist-electron/**/*',
        'dist/**/*',
        '!**/{.gitignore,.DS_Store}'
    ],

    mac: {
        target: ['dmg', 'zip'],
        category: 'public.app-category.productivity',
        icon: 'build/icon.icns',
        hardenedRuntime: true,
        gatekeeperAssess: false,
        entitlements: 'build/entitlements.mac.plist',
        entitlementsInherit: 'build/entitlements.mac.plist'
    },

    win: {
        target: ['nsis', 'portable'],
        icon: 'build/icon.ico',
        publisherName: 'LLM Protection System'
    },

    linux: {
        target: ['AppImage', 'deb'],
        icon: 'build/icon.png',
        category: 'Utility'
    },

    nsis: {
        oneClick: false,
        allowToChangeInstallationDirectory: true,
        createDesktopShortcut: true,
        createStartMenuShortcut: true,
        shortcutName: 'LLM 防护客户端'
    },

    publish: {
        provider: 'github',
        owner: 'your-org',
        repo: 'llm-client'
    }
};
```

### 5.2 自动更新

```typescript
// electron/services/auto-updater.ts
import { autoUpdater } from 'electron-updater';
import { BrowserWindow, dialog } from 'electron';
import log from 'electron-log';

export class AutoUpdater {
    private mainWindow: BrowserWindow;

    constructor(window: BrowserWindow) {
        this.mainWindow = window;
        this.setupAutoUpdater();
    }

    private setupAutoUpdater() {
        // 配置日志
        autoUpdater.logger = log;
        autoUpdater.logger.transports.file.level = 'info';

        // 检查更新
        autoUpdater.on('checking-for-update', () => {
            this.sendStatusToWindow('正在检查更新...');
        });

        // 发现新版本
        autoUpdater.on('update-available', (info) => {
            this.sendStatusToWindow('发现新版本，正在下载...');
        });

        // 没有新版本
        autoUpdater.on('update-not-available', (info) => {
            this.sendStatusToWindow('当前已是最新版本');
        });

        // 下载进度
        autoUpdater.on('download-progress', (progressObj) => {
            this.sendStatusToWindow(
                `下载进度: ${progressObj.percent.toFixed(2)}%`
            );
        });

        // 下载完成
        autoUpdater.on('update-downloaded', (info) => {
            dialog.showMessageBox(this.mainWindow, {
                type: 'info',
                title: '更新准备就绪',
                message: '新版本已下载完成，是否立即重启应用？',
                buttons: ['稍后', '立即重启']
            }).then(result => {
                if (result.response === 1) {
                    autoUpdater.quitAndInstall();
                }
            });
        });

        // 错误处理
        autoUpdater.on('error', (err) => {
            dialog.showErrorBox('更新错误', err.message);
        });
    }

    checkForUpdates() {
        autoUpdater.checkForUpdatesAndNotify();
    }

    private sendStatusToWindow(text: string) {
        this.mainWindow.webContents.send('update-status', text);
    }
}
```

## 六、总结

这个实现方案提供了：

1. **完整的客户端架构** - 从连接管理到 UI 组件
2. **安全的通信机制** - WebSocket + 加密传输
3. **本地过滤引擎** - 离线也能保护安全
4. **策略自动同步** - 实时更新安全规则
5. **流式响应支持** - 更好的用户体验
6. **跨平台支持** - Windows/Mac/Linux
7. **自动更新机制** - 无缝升级

**下一步建议:**
1. 创建基础项目框架
2. 实现核心通信层
3. 开发 UI 组件
4. 集成过滤引擎
5. 添加自动更新
6. 测试和优化
