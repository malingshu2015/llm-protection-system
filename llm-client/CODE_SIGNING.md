# 代码签名配置指南

代码签名是发布正式应用的重要步骤,可以让用户信任您的应用并减少安全警告。

## 📋 前提条件

### macOS 代码签名
- **Apple Developer 账号** (个人或企业账号,99美元/年)
- **开发者证书**: Developer ID Application 证书
- **Xcode Command Line Tools** 已安装

### Windows 代码签名
- **代码签名证书** (从 DigiCert、Sectigo 等 CA 购买,约 100-400 美元/年)
- 证书格式: `.pfx` 或 `.p12` 文件
- 证书密码

## 🍎 macOS 代码签名配置

### 1. 获取开发者证书

1. 访问 [Apple Developer](https://developer.apple.com/)
2. 登录后进入 **Certificates, Identifiers & Profiles**
3. 创建 **Developer ID Application** 证书
4. 下载并双击安装证书到钥匙串

### 2. 查看可用证书

```bash
# 列出所有开发者证书
security find-identity -v -p codesigning
```

输出示例:
```
1) ABC123... "Developer ID Application: Your Name (TEAMID)"
```

### 3. 更新 package.json

在 `llm-client/package.json` 的 `build.mac` 中添加签名配置:

```json
{
  "build": {
    "mac": {
      "target": ["dmg", "zip"],
      "icon": "build/icon.icns",
      "category": "public.app-category.utilities",
      "identity": "Developer ID Application: Your Name (TEAMID)",
      "hardenedRuntime": true,
      "gatekeeperAssess": false,
      "entitlements": "build/entitlements.mac.plist",
      "entitlementsInherit": "build/entitlements.mac.plist"
    }
  }
}
```

### 4. 权限配置说明

`build/entitlements.mac.plist` 已创建,包含以下权限:

- ✅ **网络访问**: 允许客户端连接服务器
- ✅ **文件读写**: 允许用户选择文件
- ✅ **JIT 编译**: 支持 V8 引擎
- ❌ **摄像头/麦克风**: 默认关闭(如需要可启用)

### 5. 公证 (Notarization)

从 macOS 10.15+ 开始,还需要公证应用:

```bash
# 打包后公证
xcrun notarytool submit "release/1.0.0/llm-protection-client.dmg" \
  --apple-id "your-email@example.com" \
  --team-id "TEAMID" \
  --password "app-specific-password"

# 检查公证状态
xcrun notarytool info <submission-id> \
  --apple-id "your-email@example.com" \
  --team-id "TEAMID" \
  --password "app-specific-password"

# 公证成功后装订
xcrun stapler staple "release/1.0.0/llm-protection-client.dmg"
```

**自动公证**: 可在 package.json 中配置 `afterSign` 脚本自动化此流程。

## 🪟 Windows 代码签名配置

### 1. 获取代码签名证书

推荐证书提供商:
- [DigiCert](https://www.digicert.com/) - EV 代码签名证书
- [Sectigo](https://sectigo.com/) - OV 代码签名证书
- [SSL.com](https://www.ssl.com/) - 各类代码签名

### 2. 证书类型

- **OV (Organization Validation)**: 标准代码签名,约 100-200 美元/年
- **EV (Extended Validation)**: 增强验证,约 300-400 美元/年,可立即获得 SmartScreen 信誉

### 3. 配置方式

#### 方式 A: 使用证书文件 (.pfx)

更新 `llm-client/package.json`:

```json
{
  "build": {
    "win": {
      "target": ["nsis", "portable"],
      "icon": "build/icon.ico",
      "certificateFile": "certs/windows-cert.pfx",
      "certificatePassword": "${env.WIN_CERT_PASSWORD}"
    }
  }
}
```

**安全存储密码**:
```bash
# 设置环境变量
export WIN_CERT_PASSWORD="your-certificate-password"

# 或在 CI/CD 中使用 GitHub Secrets
# Settings -> Secrets -> New repository secret
# Name: WIN_CERT_PASSWORD
# Value: your-certificate-password
```

#### 方式 B: 使用 Windows Store Certificate

如果证书在 Windows 证书存储中:

```json
{
  "build": {
    "win": {
      "target": ["nsis", "portable"],
      "icon": "build/icon.ico",
      "certificateSubjectName": "Your Company Name",
      "signingHashAlgorithms": ["sha256"],
      "rfc3161TimeStampServer": "http://timestamp.digicert.com"
    }
  }
}
```

### 4. 时间戳服务器

建议配置时间戳服务器,使签名在证书过期后仍有效:

```json
{
  "build": {
    "win": {
      "rfc3161TimeStampServer": "http://timestamp.digicert.com"
    }
  }
}
```

常用时间戳服务器:
- DigiCert: `http://timestamp.digicert.com`
- Sectigo: `http://timestamp.sectigo.com`
- GlobalSign: `http://timestamp.globalsign.com`

## 🔐 CI/CD 环境中的代码签名

### GitHub Actions 配置

#### macOS 签名 (GitHub Actions)

```yaml
- name: Import Apple Certificate
  env:
    CERTIFICATE_BASE64: ${{ secrets.APPLE_CERTIFICATE_BASE64 }}
    CERTIFICATE_PASSWORD: ${{ secrets.APPLE_CERTIFICATE_PASSWORD }}
  run: |
    echo "$CERTIFICATE_BASE64" | base64 --decode > certificate.p12
    security create-keychain -p actions temp.keychain
    security default-keychain -s temp.keychain
    security unlock-keychain -p actions temp.keychain
    security import certificate.p12 -k temp.keychain -P "$CERTIFICATE_PASSWORD" -T /usr/bin/codesign
    security set-key-partition-list -S apple-tool:,apple:,codesign: -s -k actions temp.keychain

- name: Build and Sign
  env:
    APPLE_ID: ${{ secrets.APPLE_ID }}
    APPLE_APP_SPECIFIC_PASSWORD: ${{ secrets.APPLE_APP_SPECIFIC_PASSWORD }}
    APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
  run: |
    cd llm-client
    npm run build:mac
```

**准备证书为 Base64**:
```bash
base64 -i certificate.p12 -o certificate.base64.txt
# 将 certificate.base64.txt 的内容添加到 GitHub Secrets
```

#### Windows 签名 (GitHub Actions)

```yaml
- name: Build and Sign (Windows)
  env:
    WIN_CERT_PASSWORD: ${{ secrets.WIN_CERT_PASSWORD }}
  run: |
    cd llm-client
    npm run build:win
```

在 GitHub Secrets 中添加:
- `WIN_CERT_PASSWORD`: 证书密码
- 证书文件 `.pfx` 需要提交到仓库的私有路径或使用 base64 解码

## 📊 成本估算

| 平台 | 证书类型 | 年费用 | 备注 |
|------|---------|--------|------|
| macOS | Apple Developer | $99 | 包含所有苹果平台 |
| Windows | OV 代码签名 | $100-200 | 标准验证 |
| Windows | EV 代码签名 | $300-400 | 增强验证,即时信誉 |

**总计**: 约 $200-500/年 (取决于 Windows 证书类型)

## 🧪 测试签名

### 验证 macOS 签名

```bash
# 检查签名
codesign -dv --verbose=4 "LLM防护客户端.app"

# 验证签名有效性
codesign --verify --deep --strict --verbose=2 "LLM防护客户端.app"

# 检查公证状态
spctl -a -vv "LLM防护客户端.app"
```

### 验证 Windows 签名

```powershell
# 使用 PowerShell
Get-AuthenticodeSignature "llm-protection-client-setup.exe" | Format-List

# 或使用 signtool
signtool verify /pa /v llm-protection-client-setup.exe
```

## ⚠️ 常见问题

### macOS: "App is damaged and can't be opened"

**原因**: 应用未签名或公证失败

**临时解决** (开发测试用):
```bash
sudo xattr -rd com.apple.quarantine "/Applications/LLM防护客户端.app"
```

**正式解决**: 确保应用已正确签名并公证

### Windows: SmartScreen 警告

**原因**:
1. 应用未签名
2. 使用 OV 证书且缺乏下载历史/信誉

**解决**:
1. 使用 EV 证书(立即获得信誉)
2. 或等待应用积累足够下载量(通常需要几周到几个月)

### 证书过期

**影响**:
- macOS: 已分发的应用仍可运行,但新签名的应用需要新证书
- Windows: 如果使用时间戳,已签名应用永久有效

**建议**: 设置证书过期提醒,提前 1-2 个月续费

## 🚀 无证书发布选项

如果暂时无法获取代码签名证书:

### 开发/测试版本
- 在下载页面明确标注 "开发版本"
- 提供手动安全检查步骤说明
- 使用 SHA256 校验和供用户验证

### 开源项目策略
- 发布源代码,让用户自行编译
- 使用 GitHub Releases 的可信度
- 提供详细的构建说明

### 示例说明文本

```markdown
## 安全提示

本应用当前为开发版本,未经代码签名。系统可能显示安全警告,这是正常现象。

**Windows 用户**:
1. 下载后,右键点击文件 -> 属性
2. 勾选 "解除锁定" 或 "Unblock"
3. 点击 "应用" 后运行安装程序

**macOS 用户**:
1. 下载后,在 Finder 中右键点击应用
2. 选择 "打开" (不要双击)
3. 在弹出对话框中点击 "打开"

**文件校验和**:
- SHA256: [生成的校验和]
```

## 📚 参考资源

- [Electron Code Signing](https://www.electron.build/code-signing)
- [Apple Notarization Guide](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [Windows Authenticode](https://docs.microsoft.com/windows/win32/seccrypto/cryptography-tools)

---

**更新日期**: 2025-10-04
