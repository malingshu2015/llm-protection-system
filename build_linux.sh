#!/bin/bash
# Linux 平台构建脚本

# 设置颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 获取项目根目录
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$PROJECT_ROOT"

# 获取版本号
if [ -f "VERSION" ]; then
    VERSION=$(cat VERSION)
else
    VERSION="1.0.0"
fi

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}本地大模型防护系统 Linux 构建工具 v${VERSION}${NC}"
echo -e "${GREEN}=========================================${NC}"

# 检查 Python 版本
echo -e "${YELLOW}检查 Python 版本...${NC}"
PYTHON_VERSION=$(python3 --version)
echo "当前 Python 版本: $PYTHON_VERSION"

# 检查虚拟环境
if [ -d "venv_py39" ]; then
    echo -e "${YELLOW}使用现有的虚拟环境 venv_py39...${NC}"
    source venv_py39/bin/activate
else
    echo -e "${YELLOW}创建新的虚拟环境 venv_py39...${NC}"
    python3 -m venv venv_py39
    source venv_py39/bin/activate
fi

# 安装依赖项
echo -e "${YELLOW}安装依赖项...${NC}"
pip install -r requirements.txt
pip install pyinstaller

# 清理构建目录
echo -e "${YELLOW}清理构建目录...${NC}"
rm -rf build dist

# 构建应用程序
echo -e "${YELLOW}开始构建 Linux 应用程序...${NC}"
pyinstaller pyinstaller.spec --clean

# 检查构建结果
if [ -d "dist/llm-protection-system" ]; then
    echo -e "${GREEN}应用程序构建成功!${NC}"
    
    # 创建分发包
    echo -e "${YELLOW}创建分发包...${NC}"
    TIMESTAMP=$(date +"%Y%m%d")
    ARCH=$(uname -m)
    DIST_NAME="llm-protection-system-${VERSION}-linux-${ARCH}-${TIMESTAMP}"
    DIST_DIR="${PROJECT_ROOT}/${DIST_NAME}"
    
    # 创建分发目录
    mkdir -p "${DIST_DIR}"
    
    # 复制应用程序
    cp -R "dist/llm-protection-system" "${DIST_DIR}/"
    
    # 创建启动脚本
    cat > "${DIST_DIR}/start.sh" << EOF
#!/bin/bash
cd llm-protection-system
./llm-protection-system
EOF
    chmod +x "${DIST_DIR}/start.sh"
    
    # 复制文档
    cp README.md "${DIST_DIR}/"
    if [ -f "LICENSE" ]; then
        cp LICENSE "${DIST_DIR}/"
    fi
    
    # 创建文档目录
    mkdir -p "${DIST_DIR}/docs"
    
    # 复制文档文件
    for doc_file in docs/*.md; do
        if [ -f "$doc_file" ]; then
            cp "$doc_file" "${DIST_DIR}/docs/"
        fi
    done
    
    # 创建压缩包
    tar -czf "${DIST_NAME}.tar.gz" -C "${PROJECT_ROOT}" "${DIST_NAME}"
    
    # 删除临时目录
    rm -rf "${DIST_DIR}"
    
    echo -e "${GREEN}分发包已创建: ${DIST_NAME}.tar.gz${NC}"
    
    # 创建 DEB 包（如果系统支持）
    if command -v dpkg-deb &> /dev/null; then
        echo -e "${YELLOW}创建 DEB 包...${NC}"
        
        # 创建 DEB 包目录结构
        DEB_DIR="${PROJECT_ROOT}/deb-package"
        mkdir -p "${DEB_DIR}/DEBIAN"
        mkdir -p "${DEB_DIR}/usr/local/bin"
        mkdir -p "${DEB_DIR}/usr/local/share/llm-protection-system"
        mkdir -p "${DEB_DIR}/usr/local/share/applications"
        mkdir -p "${DEB_DIR}/usr/local/share/doc/llm-protection-system"
        
        # 复制应用程序文件
        cp -R "dist/llm-protection-system/"* "${DEB_DIR}/usr/local/share/llm-protection-system/"
        
        # 创建启动脚本
        cat > "${DEB_DIR}/usr/local/bin/llm-protection-system" << EOF
#!/bin/bash
cd /usr/local/share/llm-protection-system
./llm-protection-system
EOF
        chmod +x "${DEB_DIR}/usr/local/bin/llm-protection-system"
        
        # 创建桌面快捷方式
        cat > "${DEB_DIR}/usr/local/share/applications/llm-protection-system.desktop" << EOF
[Desktop Entry]
Name=本地大模型防护系统
Comment=A protection system for local large language models
Exec=/usr/local/bin/llm-protection-system
Icon=/usr/local/share/llm-protection-system/static/favicon.ico
Terminal=false
Type=Application
Categories=Utility;
EOF
        
        # 复制文档
        cp README.md "${DEB_DIR}/usr/local/share/doc/llm-protection-system/"
        if [ -f "LICENSE" ]; then
            cp LICENSE "${DEB_DIR}/usr/local/share/doc/llm-protection-system/"
        fi
        
        # 复制文档文件
        for doc_file in docs/*.md; do
            if [ -f "$doc_file" ]; then
                cp "$doc_file" "${DEB_DIR}/usr/local/share/doc/llm-protection-system/"
            fi
        done
        
        # 创建控制文件
        cat > "${DEB_DIR}/DEBIAN/control" << EOF
Package: llm-protection-system
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: $(dpkg --print-architecture)
Maintainer: Your Name <your.email@example.com>
Description: 本地大模型防护系统
 A protection system for local large language models.
 This system provides security features for local LLMs.
EOF
        
        # 创建 DEB 包
        dpkg-deb --build "${DEB_DIR}" "llm-protection-system-${VERSION}-${ARCH}.deb"
        
        # 删除临时目录
        rm -rf "${DEB_DIR}"
        
        echo -e "${GREEN}DEB 包已创建: llm-protection-system-${VERSION}-${ARCH}.deb${NC}"
    fi
    
    # 创建 RPM 包（如果系统支持）
    if command -v rpmbuild &> /dev/null; then
        echo -e "${YELLOW}创建 RPM 包...${NC}"
        
        # 创建 RPM 构建目录
        RPM_BUILD_DIR="${PROJECT_ROOT}/rpmbuild"
        mkdir -p "${RPM_BUILD_DIR}/SPECS"
        mkdir -p "${RPM_BUILD_DIR}/SOURCES"
        mkdir -p "${RPM_BUILD_DIR}/BUILD"
        mkdir -p "${RPM_BUILD_DIR}/RPMS"
        mkdir -p "${RPM_BUILD_DIR}/SRPMS"
        
        # 创建源码包
        mkdir -p "${RPM_BUILD_DIR}/SOURCES/llm-protection-system-${VERSION}"
        cp -R "dist/llm-protection-system/"* "${RPM_BUILD_DIR}/SOURCES/llm-protection-system-${VERSION}/"
        cp README.md "${RPM_BUILD_DIR}/SOURCES/llm-protection-system-${VERSION}/"
        if [ -f "LICENSE" ]; then
            cp LICENSE "${RPM_BUILD_DIR}/SOURCES/llm-protection-system-${VERSION}/"
        fi
        
        # 创建 tar.gz 源码包
        tar -czf "${RPM_BUILD_DIR}/SOURCES/llm-protection-system-${VERSION}.tar.gz" -C "${RPM_BUILD_DIR}/SOURCES" "llm-protection-system-${VERSION}"
        
        # 创建 SPEC 文件
        cat > "${RPM_BUILD_DIR}/SPECS/llm-protection-system.spec" << EOF
Name:           llm-protection-system
Version:        ${VERSION}
Release:        1%{?dist}
Summary:        A protection system for local large language models

License:        MIT
URL:            https://github.com/yourusername/LLM-firewall
Source0:        %{name}-%{version}.tar.gz

BuildArch:      $(uname -m)
Requires:       bash

%description
本地大模型防护系统
A protection system for local large language models.
This system provides security features for local LLMs.

%prep
%setup -q

%build
# Nothing to build

%install
mkdir -p %{buildroot}/usr/local/bin
mkdir -p %{buildroot}/usr/local/share/%{name}
mkdir -p %{buildroot}/usr/local/share/applications
mkdir -p %{buildroot}/usr/local/share/doc/%{name}

# Copy application files
cp -R * %{buildroot}/usr/local/share/%{name}/

# Create launcher script
cat > %{buildroot}/usr/local/bin/%{name} << 'EOF'
#!/bin/bash
cd /usr/local/share/llm-protection-system
./llm-protection-system
EOF
chmod +x %{buildroot}/usr/local/bin/%{name}

# Create desktop file
cat > %{buildroot}/usr/local/share/applications/%{name}.desktop << EOF
[Desktop Entry]
Name=本地大模型防护系统
Comment=A protection system for local large language models
Exec=/usr/local/bin/%{name}
Icon=/usr/local/share/%{name}/static/favicon.ico
Terminal=false
Type=Application
Categories=Utility;
EOF

%files
%{_usr}/local/bin/%{name}
%{_usr}/local/share/%{name}
%{_usr}/local/share/applications/%{name}.desktop
%{_usr}/local/share/doc/%{name}

%changelog
* $(date "+%a %b %d %Y") Your Name <your.email@example.com> - ${VERSION}-1
- Initial package
EOF
        
        # 构建 RPM 包
        rpmbuild --define "_topdir ${RPM_BUILD_DIR}" -ba "${RPM_BUILD_DIR}/SPECS/llm-protection-system.spec"
        
        # 复制 RPM 包到项目根目录
        find "${RPM_BUILD_DIR}/RPMS" -name "*.rpm" -exec cp {} "${PROJECT_ROOT}/" \;
        
        # 删除临时目录
        rm -rf "${RPM_BUILD_DIR}"
        
        echo -e "${GREEN}RPM 包已创建${NC}"
    fi
else
    echo -e "${RED}构建失败!${NC}"
    exit 1
fi

echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}构建完成!${NC}"
echo -e "${GREEN}=========================================${NC}"
