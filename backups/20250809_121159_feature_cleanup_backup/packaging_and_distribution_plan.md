# 本地大模型防护系统打包与发布计划

## 一、准备工作

### 1. 代码整理与优化
- **依赖清理**：检查并移除不必要的依赖
- **代码审查**：确保代码质量和安全性
- **版本确认**：确定发布版本号（如v1.0.0）
- **文档更新**：确保README和文档是最新的

### 2. 测试与验证
- **单元测试**：确保所有单元测试通过
- **集成测试**：验证系统各组件协同工作
- **跨平台测试**：在Windows、macOS和Linux上测试
- **性能测试**：确保系统在各种负载下表现良好

## 二、打包策略

我建议采用多种打包方式，以满足不同用户的需求：

### 1. Python包（PyPI）
**优点**：适合熟悉Python的用户，安装简单

**步骤**：
1. 创建`setup.py`文件：
```python
from setuptools import setup, find_packages

setup(
    name="llm-protection-system",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "pydantic>=1.8.2",
        "aiohttp>=3.8.1",
        # 添加其他依赖
    ],
    entry_points={
        "console_scripts": [
            "llm-protection=src.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["static/**/*", "rules/**/*"],
    },
    python_requires=">=3.8",
    author="Your Name",
    author_email="your.email@example.com",
    description="本地大模型防护系统",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/llm-protection-system",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
```

2. 创建`MANIFEST.in`文件，确保包含静态文件：
```
include README.md
include LICENSE
recursive-include src/static *
recursive-include rules *
```

3. 构建并上传到PyPI：
```bash
python -m pip install --upgrade pip
python -m pip install --upgrade build twine
python -m build
python -m twine upload dist/*
```

### 2. Docker容器
**优点**：跨平台，环境一致，部署简单

**步骤**：
1. 创建`Dockerfile`：
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "-m", "src.main", "--port", "8080"]
```

2. 创建`docker-compose.yml`（可选，便于用户配置）：
```yaml
version: '3'

services:
  llm-protection:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
      - ./rules:/app/rules
    environment:
      - LOG_LEVEL=info
```

3. 构建并推送到Docker Hub：
```bash
docker build -t yourusername/llm-protection-system:1.0.0 .
docker push yourusername/llm-protection-system:1.0.0
```

### 3. 可执行文件（Windows/macOS/Linux）
**优点**：对非技术用户友好，无需安装Python

**步骤**：
1. 使用PyInstaller打包：
```bash
pip install pyinstaller
pyinstaller --name="LLM防护系统" --windowed --onefile --add-data "static:static" --add-data "rules:rules" src/main.py
```

2. 为不同平台创建安装程序：
   - **Windows**: 使用Inno Setup创建安装向导
   - **macOS**: 创建DMG文件或使用pkgbuild创建pkg安装包
   - **Linux**: 创建deb和rpm包

## 三、发布渠道

### 1. 代码托管平台
- 在GitHub/GitLab上创建Release
- 上传可执行文件和安装包
- 编写详细的Release Notes

### 2. 官方网站
- 创建简单的官方网站介绍产品
- 提供下载链接和文档
- 包含安装指南和教程

### 3. 包管理器
- PyPI（Python包）
- Docker Hub（Docker镜像）
- Homebrew（macOS）
- apt/yum仓库（Linux）

## 四、文档与支持

### 1. 用户文档
- 安装指南（各平台）
- 快速入门教程
- 配置参考
- API文档
- 常见问题解答

### 2. 开发者文档
- 架构概述
- 贡献指南
- 开发环境设置
- 插件开发指南

### 3. 支持渠道
- GitHub Issues
- 邮件支持
- 社区论坛/Discord

## 五、具体实施计划

### 第一阶段：准备（1-2周）
- [ ] 代码整理与优化
- [ ] 完成全面测试
- [ ] 准备文档
- [ ] 创建必要的构建文件（setup.py, Dockerfile等）

### 第二阶段：打包（1周）
- [ ] 创建Python包并测试
- [ ] 构建Docker镜像并测试
- [ ] 使用PyInstaller创建可执行文件
- [ ] 为各平台创建安装程序

### 第三阶段：发布（1周）
- [ ] 在GitHub创建Release
- [ ] 上传到PyPI和Docker Hub
- [ ] 创建/更新官方网站
- [ ] 发布公告

### 第四阶段：维护与支持（持续）
- [ ] 监控问题报告
- [ ] 提供用户支持
- [ ] 收集反馈
- [ ] 规划下一版本

## 六、特别注意事项

### 1. 许可证
确保选择合适的开源许可证（如MIT、Apache 2.0）或商业许可证，并在所有发布包中包含许可证文件。

### 2. 版本控制
采用语义化版本控制（Semantic Versioning），确保版本号反映变更的性质。

### 3. 安全考虑
- 避免在代码中包含敏感信息
- 确保默认配置是安全的
- 考虑添加自动更新机制

### 4. 国际化
- 考虑添加多语言支持
- 确保文档有英文版本

## 七、资源需求

### 1. 人力资源
- 开发人员：代码优化、打包
- 测试人员：跨平台测试
- 文档撰写者：用户指南、API文档

### 2. 基础设施
- CI/CD系统：自动化构建和测试
- 网站托管：官方网站
- 包分发服务：PyPI、Docker Hub等

### 3. 工具
- 构建工具：PyInstaller, Docker
- 打包工具：Inno Setup (Windows), pkgbuild (macOS)
- 文档工具：Sphinx, MkDocs

## 八、后续发展

### 1. 功能扩展
- 插件系统：允许第三方开发安全规则
- 企业版：添加高级功能和支持

### 2. 社区建设
- 开源贡献指南
- 社区活动和讨论

### 3. 商业化（可选）
- 免费社区版 + 付费专业版
- 提供托管服务
- 企业支持合同

## 九、平台特定打包详情

### Windows打包详细步骤

1. **使用PyInstaller创建可执行文件**:
```bash
# 安装PyInstaller
pip install pyinstaller

# 创建Windows可执行文件
pyinstaller --name="LLM防护系统" ^
            --windowed ^
            --icon=static/favicon.ico ^
            --add-data "static;static" ^
            --add-data "rules;rules" ^
            src/main.py
```

2. **使用Inno Setup创建安装程序**:
   - 下载并安装[Inno Setup](https://jrsoftware.org/isinfo.php)
   - 创建一个新的脚本文件`setup.iss`:

```
[Setup]
AppName=本地大模型防护系统
AppVersion=1.0.0
DefaultDirName={pf}\LLM防护系统
DefaultGroupName=本地大模型防护系统
OutputDir=output
OutputBaseFilename=LLM防护系统_安装程序_1.0.0
Compression=lzma
SolidCompression=yes
SetupIconFile=static\favicon.ico

[Files]
Source: "dist\LLM防护系统\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{group}\LLM防护系统"; Filename: "{app}\LLM防护系统.exe"
Name: "{commondesktop}\LLM防护系统"; Filename: "{app}\LLM防护系统.exe"

[Run]
Filename: "{app}\LLM防护系统.exe"; Description: "启动本地大模型防护系统"; Flags: nowait postinstall skipifsilent
```

3. **编译安装程序**:
   - 在Inno Setup中打开`setup.iss`文件
   - 点击"Build"或按F9编译
   - 在`output`目录中找到生成的安装程序

### macOS打包详细步骤

1. **使用PyInstaller创建应用程序**:
```bash
# 安装PyInstaller
pip install pyinstaller

# 创建macOS应用程序
pyinstaller --name="LLM防护系统" \
            --windowed \
            --icon=static/favicon.ico \
            --add-data "static:static" \
            --add-data "rules:rules" \
            src/main.py
```

2. **创建DMG文件**:
```bash
# 安装create-dmg工具
brew install create-dmg

# 创建DMG文件
create-dmg \
  --volname "LLM防护系统" \
  --volicon "static/favicon.ico" \
  --window-pos 200 120 \
  --window-size 800 400 \
  --icon-size 100 \
  --icon "LLM防护系统.app" 200 190 \
  --hide-extension "LLM防护系统.app" \
  --app-drop-link 600 185 \
  "LLM防护系统_1.0.0.dmg" \
  "dist/LLM防护系统.app"
```

3. **或者创建pkg安装包**:
```bash
# 创建临时目录结构
mkdir -p pkg_root/Applications
cp -R "dist/LLM防护系统.app" pkg_root/Applications/

# 创建pkg文件
pkgbuild --root pkg_root \
         --identifier com.yourcompany.llmprotection \
         --version 1.0.0 \
         "LLM防护系统_1.0.0.pkg"
```

### Linux打包详细步骤

1. **使用PyInstaller创建可执行文件**:
```bash
# 安装PyInstaller
pip install pyinstaller

# 创建Linux可执行文件
pyinstaller --name="llm-protection-system" \
            --add-data "static:static" \
            --add-data "rules:rules" \
            src/main.py
```

2. **创建DEB包**:
```bash
# 安装必要工具
sudo apt-get install dpkg-dev

# 创建目录结构
mkdir -p llm-protection-system_1.0.0/DEBIAN
mkdir -p llm-protection-system_1.0.0/usr/local/bin
mkdir -p llm-protection-system_1.0.0/usr/share/applications

# 复制文件
cp -R dist/llm-protection-system/* llm-protection-system_1.0.0/usr/local/bin/

# 创建控制文件
cat > llm-protection-system_1.0.0/DEBIAN/control << EOF
Package: llm-protection-system
Version: 1.0.0
Section: utils
Priority: optional
Architecture: amd64
Depends: libc6
Maintainer: Your Name <your.email@example.com>
Description: 本地大模型防护系统
 为本地部署的大型语言模型提供安全防护的系统。
EOF

# 创建桌面快捷方式
cat > llm-protection-system_1.0.0/usr/share/applications/llm-protection.desktop << EOF
[Desktop Entry]
Name=本地大模型防护系统
Exec=/usr/local/bin/llm-protection-system
Icon=/usr/local/bin/static/favicon.ico
Type=Application
Categories=Utility;
EOF

# 构建DEB包
dpkg-deb --build llm-protection-system_1.0.0
```

3. **创建RPM包**:
```bash
# 安装必要工具
sudo yum install rpm-build

# 创建spec文件
cat > llm-protection-system.spec << EOF
Name:           llm-protection-system
Version:        1.0.0
Release:        1%{?dist}
Summary:        本地大模型防护系统

License:        MIT
URL:            https://github.com/yourusername/llm-protection-system

BuildRequires:  python3
Requires:       python3

%description
为本地部署的大型语言模型提供安全防护的系统。

%install
mkdir -p %{buildroot}/usr/local/bin
cp -R dist/llm-protection-system/* %{buildroot}/usr/local/bin/

mkdir -p %{buildroot}/usr/share/applications
cat > %{buildroot}/usr/share/applications/llm-protection.desktop << EOL
[Desktop Entry]
Name=本地大模型防护系统
Exec=/usr/local/bin/llm-protection-system
Icon=/usr/local/bin/static/favicon.ico
Type=Application
Categories=Utility;
EOL

%files
/usr/local/bin/llm-protection-system
/usr/local/bin/static
/usr/local/bin/rules
/usr/share/applications/llm-protection.desktop

%changelog
* $(date "+%a %b %d %Y") Your Name <your.email@example.com> - 1.0.0-1
- Initial package
EOF

# 构建RPM包
rpmbuild -bb llm-protection-system.spec
```
