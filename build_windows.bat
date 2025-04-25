@echo off
REM Windows 平台构建脚本

setlocal enabledelayedexpansion

REM 获取项目根目录
set "PROJECT_ROOT=%~dp0"
cd "%PROJECT_ROOT%"

REM 获取版本号
if exist VERSION (
    set /p VERSION=<VERSION
) else (
    set "VERSION=1.0.0"
)

echo =========================================
echo 本地大模型防护系统 Windows 构建工具 v%VERSION%
echo =========================================

REM 检查 Python 版本
echo 检查 Python 版本...
python --version

REM 检查虚拟环境
if exist venv_py39 (
    echo 使用现有的虚拟环境 venv_py39...
    call venv_py39\Scripts\activate.bat
) else (
    echo 创建新的虚拟环境 venv_py39...
    python -m venv venv_py39
    call venv_py39\Scripts\activate.bat
)

REM 安装依赖项
echo 安装依赖项...
pip install -r requirements.txt
pip install pyinstaller

REM 清理构建目录
echo 清理构建目录...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM 构建应用程序
echo 开始构建 Windows 应用程序...
pyinstaller pyinstaller.spec --clean

REM 检查构建结果
if exist "dist\llm-protection-system" (
    echo 应用程序构建成功!
    
    REM 创建分发包
    echo 创建分发包...
    for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do set "dt=%%a"
    set "TIMESTAMP=%dt:~0,8%"
    
    REM 获取系统架构
    if exist "%PROGRAMFILES(X86)%" (
        set "ARCH=x64"
    ) else (
        set "ARCH=x86"
    )
    
    set "DIST_NAME=llm-protection-system-%VERSION%-windows-%ARCH%-%TIMESTAMP%"
    set "DIST_DIR=%PROJECT_ROOT%%DIST_NAME%"
    
    REM 创建分发目录
    if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
    mkdir "%DIST_DIR%"
    
    REM 复制应用程序
    xcopy "dist\llm-protection-system" "%DIST_DIR%\llm-protection-system\" /E /I /H /Y
    
    REM 创建启动脚本
    echo @echo off > "%DIST_DIR%\start.bat"
    echo cd llm-protection-system >> "%DIST_DIR%\start.bat"
    echo start llm-protection-system.exe >> "%DIST_DIR%\start.bat"
    
    REM 复制文档
    copy README.md "%DIST_DIR%\"
    if exist LICENSE copy LICENSE "%DIST_DIR%\"
    
    REM 创建文档目录
    mkdir "%DIST_DIR%\docs"
    
    REM 复制文档文件
    for %%f in (docs\*.md) do (
        copy "%%f" "%DIST_DIR%\docs\"
    )
    
    REM 创建压缩包
    if exist "%DIST_NAME%.zip" del "%DIST_NAME%.zip"
    powershell -command "Compress-Archive -Path '%DIST_DIR%\*' -DestinationPath '%DIST_NAME%.zip'"
    
    REM 删除临时目录
    rmdir /s /q "%DIST_DIR%"
    
    echo 分发包已创建: %DIST_NAME%.zip
) else (
    echo 构建失败!
    exit /b 1
)

echo =========================================
echo 构建完成!
echo =========================================

endlocal
