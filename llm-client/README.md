# LLM 防护系统 - 统一客户端

统一的桌面客户端程序,为用户提供快捷、安全的大模型访问体验。

## 功能特性

- ✅ **快捷连接** - 一键连接到 LLM 防护网关
- ✅ **本地过滤** - 客户端预过滤敏感内容
- ✅ **会话管理** - 多会话支持,历史记录保存
- ✅ **策略同步** - 自动更新安全策略
- ✅ **跨平台** - 支持 Windows/macOS/Linux

## 技术栈

- **框架**: Electron 28 + React 18 + TypeScript 5
- **UI 组件**: Ant Design 5
- **状态管理**: Zustand 4
- **通信**: Socket.IO Client 4
- **本地存储**: better-sqlite3
- **构建工具**: Vite 5

## 开发环境设置

### 1. 安装依赖

```bash
cd llm-client
npm install
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件,设置服务器地址
```

### 3. 启动开发服务器

```bash
npm run dev
```

这将启动 Vite 开发服务器 (http://localhost:5173)。

### 4. 启动 Electron 应用

在另一个终端窗口:

```bash
npm run electron:dev
```

或者使用并发模式(自动启动):

```bash
npm run dev
```

## 项目结构

```
llm-client/
├── electron/              # Electron 主进程
│   ├── main.ts           # 主进程入口
│   └── preload.ts        # 预加载脚本
├── src/                  # React 应用
│   ├── pages/           # 页面组件
│   │   ├── Login.tsx    # 登录页
│   │   ├── Chat.tsx     # 聊天页
│   │   └── Settings.tsx # 设置页
│   ├── store/           # 状态管理
│   │   └── useAuthStore.ts
│   ├── types/           # TypeScript 类型
│   │   ├── api.ts
│   │   ├── chat.ts
│   │   └── policy.ts
│   ├── App.tsx          # 应用入口
│   └── main.tsx         # React 入口
├── index.html           # HTML 模板
├── package.json         # 依赖配置
├── tsconfig.json        # TypeScript 配置
└── vite.config.ts       # Vite 配置
```

## 构建打包

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

构建产物位于 `release/` 目录。

## 下一步开发计划

- [ ] 实现 WebSocket 连接模块
- [ ] 实现本地过滤引擎
- [ ] 实现会话管理功能
- [ ] 实现策略同步机制
- [ ] 完善 UI 界面和交互

## 相关文档

- [设计文档](../docs/unified-client-design.md)
- [实现指南](../docs/unified-client-implementation.md)
