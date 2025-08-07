# 本地大模型防护系统 v1.0.0

## 发布概述

本地大模型防护系统 v1.0.0 是我们的首个稳定版本，提供了全面的本地大模型安全防护功能，帮助用户安全地使用本地部署的大型语言模型。

## 主要功能

- 提示注入检测与防护
- 越狱尝试检测与阻止
- 有害内容过滤
- 自定义安全规则配置
- 自动检测本地Ollama模型
- 实时系统监控与可视化
- 多平台支持（Windows、macOS、Linux）

## 下载

### 预编译包

- [Windows安装程序 (64位)](https://github.com/yourusername/LLM-firewall/releases/download/v1.0.0/llm-protection-system-1.0.0-windows-x64.exe)
- [macOS DMG (Intel/Apple Silicon)](https://github.com/yourusername/LLM-firewall/releases/download/v1.0.0/本地大模型防护系统-1.0.0.dmg)
- [Linux DEB包 (Ubuntu/Debian)](https://github.com/yourusername/LLM-firewall/releases/download/v1.0.0/llm-protection-system-1.0.0-amd64.deb)
- [Linux RPM包 (RHEL/CentOS/Fedora)](https://github.com/yourusername/LLM-firewall/releases/download/v1.0.0/llm-protection-system-1.0.0-x86_64.rpm)

### 源代码

- [Source code (zip)](https://github.com/yourusername/LLM-firewall/archive/refs/tags/v1.0.0.zip)
- [Source code (tar.gz)](https://github.com/yourusername/LLM-firewall/archive/refs/tags/v1.0.0.tar.gz)

## 安装指南

详细的安装指南请参阅[文档](https://github.com/yourusername/LLM-firewall/blob/main/docs/installation_guide.md)。

### 快速安装

#### Python包

```bash
pip install llm-protection-system
```

#### Docker

```bash
docker pull yourusername/llm-protection-system:1.0.0
docker run -d -p 8080:8080 yourusername/llm-protection-system:1.0.0
```

## 完整发布说明

详细的发布说明请参阅[RELEASE_NOTES.md](https://github.com/yourusername/LLM-firewall/blob/main/docs/release_notes_v1.0.0.md)。

## 反馈与支持

如有任何问题或建议，请[提交Issue](https://github.com/yourusername/LLM-firewall/issues/new)或发送邮件至support@example.com。
