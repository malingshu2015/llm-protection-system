# 客户端打包与发布指南

## 📦 快速开始

### 前提条件

**必需软件:**
- Node.js 18+
- npm 或 yarn
- Git

**平台特定要求:**
- **Windows**: Windows 10 SDK
- **macOS**: Xcode Command Line Tools
- **Linux**: 无额外要求

### 安装依赖

```bash
cd llm-client
npm install
```

## 🔨 本地开发

### 开发模式

```bash
# 启动开发服务器
npm run dev

# 或启动 Electron 开发模式
npm run electron:dev
```

开发服务器将在 `http://localhost:5173` 启动。

### 类型检查

```bash
npm run type-check
```

## 📦 打包构建

### 打包所有平台

```bash
npm run build
```

这将构建:
- Windows: `.exe` 安装包 + 便携版
- macOS: `.dmg` 镜像 + `.zip` 压缩包
- Linux: `AppImage` + `.deb` 包

### 打包特定平台

```bash
# 仅 Windows
npm run build:win

# 仅 macOS
npm run build:mac

# 仅 Linux
npm run build:linux
```

### 输出位置

打包后的文件位于:
```
llm-client/release/
└── 1.0.0/
    ├── llm-protection-client-setup.exe      # Windows 安装包
    ├── llm-protection-client-portable.exe   # Windows 便携版
    ├── llm-protection-client.dmg            # macOS 镜像
    ├── llm-protection-client.zip            # macOS 压缩包
    ├── llm-protection-client.AppImage       # Linux AppImage
    └── llm-protection-client.deb            # Linux Debian 包
```

## 🎯 发布流程

### 1. 更新版本号

编辑 `llm-client/package.json`:
```json
{
  "version": "1.1.0"
}
```

### 2. 构建所有平台

```bash
npm run build
```

### 3. 上传到服务器

将 `release/1.1.0/` 目录下的所有文件上传到服务器的 `/downloads/` 目录:

```bash
# 示例: 使用 scp
scp -r release/1.1.0/* user@server:/path/to/static/downloads/
```

### 4. 更新下载页面

确保 `static/download.html` 中的版本号和下载链接正确:

```html
<span class="version">v1.1.0</span>
```

### 5. 测试下载链接

访问 `http://your-server/download.html` 测试所有下载链接是否正常。

## 🔐 代码签名 (可选但推荐)

### macOS 代码签名

1. 获取 Apple Developer 证书
2. 更新 `package.json`:

```json
{
  "build": {
    "mac": {
      "identity": "Developer ID Application: Your Name (TEAMID)",
      "hardenedRuntime": true,
      "gatekeeperAssess": false,
      "entitlements": "build/entitlements.mac.plist",
      "entitlementsInherit": "build/entitlements.mac.plist"
    }
  }
}
```

3. 创建 `build/entitlements.mac.plist`

### Windows 代码签名

1. 获取代码签名证书
2. 更新 `package.json`:

```json
{
  "build": {
    "win": {
      "certificateFile": "path/to/certificate.pfx",
      "certificatePassword": "your-password"
    }
  }
}
```

## 📝 打包配置详解

### electron-builder 配置

完整配置在 `package.json` 的 `build` 字段:

```json
{
  "build": {
    "appId": "com.llm.protection.client",
    "productName": "LLM防护客户端",
    "directories": {
      "output": "release/${version}"
    },
    "files": [
      "dist",
      "dist-electron"
    ],
    "mac": {
      "target": ["dmg", "zip"],
      "icon": "build/icon.icns",
      "category": "public.app-category.utilities"
    },
    "win": {
      "target": ["nsis", "portable"],
      "icon": "build/icon.ico"
    },
    "linux": {
      "target": ["AppImage", "deb"],
      "icon": "build/icon.png",
      "category": "Utility"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true,
      "createDesktopShortcut": true,
      "createStartMenuShortcut": true
    }
  }
}
```

## 🖼️ 应用图标

需要为每个平台准备图标:

```
llm-client/build/
├── icon.icns     # macOS (1024x1024)
├── icon.ico      # Windows (256x256)
└── icon.png      # Linux (512x512)
```

### 生成图标

可以使用在线工具或命令行工具:

```bash
# 使用 electron-icon-maker (需要安装)
npm install -g electron-icon-maker
electron-icon-maker --input=logo.png --output=./build
```

## 🚀 自动化发布 (CI/CD)

### GitHub Actions 示例

创建 `.github/workflows/release.yml`:

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [macos-latest, ubuntu-latest, windows-latest]

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          cd llm-client
          npm install

      - name: Build
        run: |
          cd llm-client
          npm run build

      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: ${{ matrix.os }}-build
          path: llm-client/release/**/*
```

## 📊 版本管理

### 语义化版本

遵循 [Semantic Versioning](https://semver.org/):

- **MAJOR**: 不兼容的 API 修改
- **MINOR**: 向后兼容的功能性新增
- **PATCH**: 向后兼容的问题修正

示例:
- `1.0.0` - 初始版本
- `1.1.0` - 新功能
- `1.1.1` - Bug 修复
- `2.0.0` - 重大更新

### 更新日志

在 `CHANGELOG.md` 中记录每个版本的变更:

```markdown
## [1.1.0] - 2025-10-04

### Added
- 新增离线模式支持
- 添加快捷键配置

### Fixed
- 修复 WebSocket 断线重连问题
- 优化内存使用

### Changed
- 更新 UI 样式
```

## 🐛 常见问题

### 打包失败

**问题**: `Error: Application entry file "dist-electron/main.js" in the ...`

**解决**: 确保先运行 TypeScript 编译:
```bash
npm run type-check
tsc
```

### macOS 无法打开应用

**问题**: "App is damaged and can't be opened"

**解决**: 需要代码签名或用户手动信任:
```bash
sudo xattr -rd com.apple.quarantine /Applications/LLM防护客户端.app
```

### Windows SmartScreen 警告

**问题**: "Windows protected your PC"

**解决**: 使用有效的代码签名证书签名应用

## 📞 获取帮助

- **文档**: [Electron Builder 文档](https://www.electron.build/)
- **问题**: 在 GitHub Issues 提交问题
- **社区**: Electron Discord 服务器

---

**最后更新**: 2025-10-04
**维护者**: LLM Protection Team
