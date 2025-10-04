# 客户端发布部署指南

本文档说明如何发布 LLM 防护客户端的新版本,包括手动发布和自动化 CI/CD 发布流程。

## 📋 发布前检查清单

### 1. 代码准备
- [ ] 所有功能已开发完成并测试通过
- [ ] 代码已经过类型检查 (`npm run type-check`)
- [ ] 已更新 CHANGELOG.md
- [ ] 已更新版本号 (package.json)

### 2. 环境准备
- [ ] Node.js 18+ 已安装
- [ ] 应用图标已准备 (build/ 目录)
- [ ] (可选) 代码签名证书已配置

### 3. 文档更新
- [ ] README.md 反映最新功能
- [ ] 更新日志已记录所有变更
- [ ] API 文档已同步更新

## 🚀 发布流程

### 方式 A: 手动发布 (本地构建)

#### 步骤 1: 更新版本号

编辑 `llm-client/package.json`:

```json
{
  "version": "1.1.0"
}
```

#### 步骤 2: 更新 CHANGELOG.md

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

#### 步骤 3: 本地构建测试

```bash
cd llm-client

# 运行类型检查
npm run type-check

# 构建当前平台
npm run build:mac    # macOS
npm run build:win    # Windows
npm run build:linux  # Linux

# 或构建所有平台 (需要在对应系统上运行)
npm run build
```

#### 步骤 4: 测试打包产物

构建完成后,检查 `llm-client/release/1.1.0/` 目录:

```bash
ls -lh llm-client/release/1.1.0/
```

应该包含:
- **macOS**: `.dmg` 和 `.zip` 文件
- **Windows**: `.exe` 安装包和便携版
- **Linux**: `.AppImage` 和 `.deb` 包

#### 步骤 5: 上传到服务器

```bash
# 示例: 使用 scp 上传
scp llm-client/release/1.1.0/* user@server:/var/www/downloads/

# 或使用 rsync
rsync -av llm-client/release/1.1.0/ user@server:/var/www/downloads/
```

#### 步骤 6: 更新下载页面

确保 `static/download.html` 中的版本号和链接正确:

```html
<div class="version-badge">
  <span class="label">当前版本</span>
  <span class="version">v1.1.0</span>
</div>
```

下载链接格式:
```
http://your-server/downloads/llm-protection-client-setup.exe
http://your-server/downloads/llm-protection-client.dmg
http://your-server/downloads/llm-protection-client.AppImage
```

### 方式 B: 自动化发布 (GitHub Actions)

#### 步骤 1: 准备 Git 标签

```bash
# 1. 确保所有更改已提交
git add .
git commit -m "chore: prepare release v1.1.0"

# 2. 创建版本标签
git tag -a v1.1.0 -m "Release version 1.1.0"

# 3. 推送代码和标签
git push origin main
git push origin v1.1.0
```

#### 步骤 2: GitHub Actions 自动构建

推送标签后,GitHub Actions 会自动:
1. 在 macOS、Ubuntu、Windows 上并行构建
2. 运行类型检查
3. 上传构建产物
4. 创建 GitHub Release
5. 附加所有平台的安装包

#### 步骤 3: 监控构建状态

访问 GitHub 仓库:
- **Actions**: 查看构建进度
- **Releases**: 查看发布结果

#### 步骤 4: 验证 Release

检查 Release 页面:
1. 版本号正确
2. 所有平台的文件都已上传
3. Release Notes 内容完整

## 🔐 代码签名发布 (生产环境)

### macOS 签名发布

如果已配置代码签名证书,构建时会自动签名:

```bash
# 确保证书已安装
security find-identity -v -p codesigning

# 构建 (自动签名)
npm run build:mac

# 公证应用 (macOS 10.15+)
xcrun notarytool submit release/1.1.0/llm-protection-client.dmg \
  --apple-id "your-email@example.com" \
  --team-id "TEAMID" \
  --password "app-specific-password" \
  --wait

# 装订公证票据
xcrun stapler staple release/1.1.0/llm-protection-client.dmg
```

### Windows 签名发布

配置了证书后,electron-builder 会自动签名:

```bash
# 设置证书密码环境变量
export WIN_CERT_PASSWORD="your-password"

# 构建 (自动签名)
npm run build:win
```

## 📦 发布到下载服务器

### 服务器目录结构

```
/var/www/
├── downloads/           # 客户端安装包
│   ├── latest/         # 最新版本
│   │   ├── llm-protection-client-setup.exe
│   │   ├── llm-protection-client.dmg
│   │   └── llm-protection-client.AppImage
│   └── archives/       # 历史版本
│       ├── v1.0.0/
│       └── v1.1.0/
└── static/
    └── download.html   # 下载页面
```

### 部署脚本示例

创建 `deploy.sh`:

```bash
#!/bin/bash

VERSION=$1
SERVER_USER="deploy"
SERVER_HOST="your-server.com"
SERVER_PATH="/var/www/downloads"

if [ -z "$VERSION" ]; then
  echo "用法: ./deploy.sh <version>"
  echo "示例: ./deploy.sh 1.1.0"
  exit 1
fi

echo "📦 部署版本 $VERSION 到生产服务器..."

# 1. 上传到归档目录
rsync -av llm-client/release/$VERSION/ \
  $SERVER_USER@$SERVER_HOST:$SERVER_PATH/archives/v$VERSION/

# 2. 更新 latest 目录
ssh $SERVER_USER@$SERVER_HOST "
  rm -rf $SERVER_PATH/latest/*
  cp -r $SERVER_PATH/archives/v$VERSION/* $SERVER_PATH/latest/
"

# 3. 更新下载页面
scp static/download.html \
  $SERVER_USER@$SERVER_HOST:/var/www/static/

echo "✅ 部署完成!"
echo "下载页面: http://your-server.com/download.html"
```

使用:
```bash
chmod +x deploy.sh
./deploy.sh 1.1.0
```

## 🧪 发布后验证

### 1. 下载测试

访问下载页面,测试每个平台的下载链接:

```bash
# 检查文件可访问
curl -I http://your-server/downloads/latest/llm-protection-client.dmg
curl -I http://your-server/downloads/latest/llm-protection-client-setup.exe
curl -I http://your-server/downloads/latest/llm-protection-client.AppImage
```

### 2. 安装测试

在各平台测试安装:

**macOS**:
```bash
# 下载并安装
curl -O http://your-server/downloads/latest/llm-protection-client.dmg
open llm-protection-client.dmg
```

**Windows**:
```powershell
# 下载
Invoke-WebRequest http://your-server/downloads/latest/llm-protection-client-setup.exe `
  -OutFile llm-protection-client-setup.exe

# 运行安装
.\llm-protection-client-setup.exe
```

**Linux**:
```bash
# 下载
wget http://your-server/downloads/latest/llm-protection-client.AppImage

# 添加执行权限
chmod +x llm-protection-client.AppImage

# 运行
./llm-protection-client.AppImage
```

### 3. 功能验证

安装后验证核心功能:
- [ ] 应用正常启动
- [ ] 能连接到服务器
- [ ] 认证功能正常
- [ ] WebSocket 连接稳定
- [ ] 策略同步正常
- [ ] 日志记录正常

## 📊 版本管理

### 语义化版本控制

遵循 [Semantic Versioning 2.0.0](https://semver.org/):

- **MAJOR (主版本)**: 不兼容的 API 修改
  - 示例: `1.0.0` → `2.0.0`
- **MINOR (次版本)**: 向后兼容的功能性新增
  - 示例: `1.0.0` → `1.1.0`
- **PATCH (修订版)**: 向后兼容的问题修正
  - 示例: `1.0.0` → `1.0.1`

### 版本发布节奏

- **Major**: 重大架构变更,不定期
- **Minor**: 新功能发布,每 2-4 周
- **Patch**: Bug 修复,按需发布

## 🔄 回滚流程

如果发现严重问题需要回滚:

### 1. 服务器端回滚

```bash
# SSH 到服务器
ssh deploy@your-server.com

# 回滚到上一版本
cd /var/www/downloads/
rm -rf latest/*
cp -r archives/v1.0.0/* latest/
```

### 2. Git 标签回滚

```bash
# 删除本地和远程标签
git tag -d v1.1.0
git push origin :refs/tags/v1.1.0

# 删除 GitHub Release
# 在 GitHub 网页端手动删除或使用 gh CLI
gh release delete v1.1.0
```

## 📝 发布通知

### 1. 更新官网公告

在网站首页添加新版本通知:

```markdown
## 🎉 新版本发布 v1.1.0

**发布日期**: 2025-10-04

### 主要更新
- ✨ 新增离线模式支持
- 🐛 修复 WebSocket 连接问题
- ⚡ 性能优化,减少 30% 内存占用

[立即下载](/download.html) | [查看完整更新日志](/changelog.html)
```

### 2. 通知用户

- 邮件通知 (如有用户列表)
- 社交媒体发布
- 应用内更新提示

## ⚠️ 常见问题

### 构建失败

**问题**: electron-builder 构建失败

**排查**:
```bash
# 清理缓存重试
rm -rf node_modules
npm install
npm run build
```

### 文件大小异常

**问题**: 打包文件过大

**检查**:
```bash
# 分析包体积
npm run build -- --analyze

# 确保 .gitignore 和 files 配置正确
```

### 下载速度慢

**解决**:
1. 使用 CDN 加速下载
2. 提供多个镜像下载链接
3. 考虑 BitTorrent 种子下载

## 📞 支持渠道

- **文档**: [完整文档](./BUILDING.md)
- **问题反馈**: GitHub Issues
- **紧急联系**: team@example.com

---

**最后更新**: 2025-10-04
**维护者**: LLM Protection Team
