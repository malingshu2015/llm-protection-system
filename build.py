#!/usr/bin/env python3
"""
构建脚本，用于使用 PyInstaller 构建本地大模型防护系统的可执行文件。
支持 Windows、macOS 和 Linux 平台。
"""

import os
import sys
import platform
import subprocess
import shutil
from datetime import datetime

# 获取项目根目录
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
# 获取构建目录
BUILD_DIR = os.path.join(PROJECT_ROOT, 'dist')
# 获取版本号
VERSION_FILE = os.path.join(PROJECT_ROOT, 'VERSION')
VERSION = "1.0.0"  # 默认版本
if os.path.exists(VERSION_FILE):
    with open(VERSION_FILE, "r") as f:
        VERSION = f.read().strip()


def clean_build_dir():
    """清理构建目录"""
    print("清理构建目录...")
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    if os.path.exists(os.path.join(PROJECT_ROOT, 'build')):
        shutil.rmtree(os.path.join(PROJECT_ROOT, 'build'))
    print("构建目录已清理")


def install_requirements():
    """安装依赖项"""
    print("安装依赖项...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    # 安装 PyInstaller
    subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)
    print("依赖项已安装")


def build_executable():
    """构建可执行文件"""
    print(f"开始构建 {platform.system()} 平台的可执行文件...")
    
    # 使用 PyInstaller 构建
    subprocess.run([
        sys.executable, 
        "-m", 
        "PyInstaller", 
        "pyinstaller.spec",
        "--clean",
    ], check=True)
    
    print("可执行文件构建完成")


def create_distribution_package():
    """创建分发包"""
    print("创建分发包...")
    
    # 获取当前系统信息
    system = platform.system().lower()
    architecture = platform.machine().lower()
    timestamp = datetime.now().strftime("%Y%m%d")
    
    # 创建分发包名称
    dist_name = f"llm-protection-system-{VERSION}-{system}-{architecture}-{timestamp}"
    dist_dir = os.path.join(PROJECT_ROOT, dist_name)
    
    # 创建分发目录
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir)
    
    # 复制构建文件到分发目录
    if system == "windows":
        # Windows 平台
        shutil.copytree(
            os.path.join(BUILD_DIR, "llm-protection-system"),
            os.path.join(dist_dir, "llm-protection-system")
        )
        # 创建启动脚本
        with open(os.path.join(dist_dir, "start.bat"), "w") as f:
            f.write("@echo off\n")
            f.write("cd llm-protection-system\n")
            f.write("start llm-protection-system.exe\n")
    elif system == "darwin":
        # macOS 平台
        shutil.copytree(
            os.path.join(BUILD_DIR, "本地大模型防护系统.app"),
            os.path.join(dist_dir, "本地大模型防护系统.app")
        )
        # 创建启动脚本
        with open(os.path.join(dist_dir, "start.sh"), "w") as f:
            f.write("#!/bin/bash\n")
            f.write("open \"本地大模型防护系统.app\"\n")
        os.chmod(os.path.join(dist_dir, "start.sh"), 0o755)
    else:
        # Linux 平台
        shutil.copytree(
            os.path.join(BUILD_DIR, "llm-protection-system"),
            os.path.join(dist_dir, "llm-protection-system")
        )
        # 创建启动脚本
        with open(os.path.join(dist_dir, "start.sh"), "w") as f:
            f.write("#!/bin/bash\n")
            f.write("cd llm-protection-system\n")
            f.write("./llm-protection-system\n")
        os.chmod(os.path.join(dist_dir, "start.sh"), 0o755)
    
    # 复制文档文件
    shutil.copy(os.path.join(PROJECT_ROOT, "README.md"), dist_dir)
    if os.path.exists(os.path.join(PROJECT_ROOT, "LICENSE")):
        shutil.copy(os.path.join(PROJECT_ROOT, "LICENSE"), dist_dir)
    
    # 创建文档目录
    docs_dir = os.path.join(dist_dir, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    
    # 复制文档文件
    for doc_file in os.listdir(os.path.join(PROJECT_ROOT, "docs")):
        if doc_file.endswith(".md"):
            shutil.copy(
                os.path.join(PROJECT_ROOT, "docs", doc_file),
                os.path.join(docs_dir, doc_file)
            )
    
    # 创建压缩包
    if system == "windows":
        # Windows 平台使用 zip
        shutil.make_archive(dist_name, "zip", PROJECT_ROOT, dist_name)
    else:
        # macOS 和 Linux 平台使用 tar.gz
        shutil.make_archive(dist_name, "gztar", PROJECT_ROOT, dist_name)
    
    # 删除临时目录
    shutil.rmtree(dist_dir)
    
    print(f"分发包已创建: {dist_name}")


def main():
    """主函数"""
    print("=" * 50)
    print(f"本地大模型防护系统构建工具 v{VERSION}")
    print("=" * 50)
    
    # 清理构建目录
    clean_build_dir()
    
    # 安装依赖项
    install_requirements()
    
    # 构建可执行文件
    build_executable()
    
    # 创建分发包
    create_distribution_package()
    
    print("=" * 50)
    print("构建完成!")
    print("=" * 50)


if __name__ == "__main__":
    main()
