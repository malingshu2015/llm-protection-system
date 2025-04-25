#!/usr/bin/env python3
"""
确认所有打包文件包含必要的文档。
"""

import os
import sys
import glob
import json
import platform
import subprocess
import tempfile
from datetime import datetime

# 获取项目根目录
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
# 获取版本号
VERSION_FILE = os.path.join(PROJECT_ROOT, "VERSION")
VERSION = "1.0.0"  # 默认版本
if os.path.exists(VERSION_FILE):
    with open(VERSION_FILE, "r") as f:
        VERSION = f.read().strip()

# 定义颜色
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
NC = "\033[0m"  # No Color

# 定义必要的文档
REQUIRED_DOCS = [
    "README.md",
    "LICENSE",
    "docs/pyinstaller_build_guide.md",
    "docs/release_plan_tracker.md",
]

def print_color(color, message):
    """打印彩色文本"""
    print(f"{color}{message}{NC}")

def run_command(command):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def check_python_package_docs():
    """检查Python包中的文档"""
    print_color(YELLOW, "检查Python包中的文档...")
    
    # 查找Python包
    wheel_files = glob.glob(os.path.join(PROJECT_ROOT, "dist", "*.whl"))
    if not wheel_files:
        print_color(YELLOW, "未找到Python wheel包")
        return False, "未找到Python wheel包", []
    
    wheel_file = wheel_files[0]
    print_color(YELLOW, f"找到Python wheel包: {os.path.basename(wheel_file)}")
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        # 解压wheel包
        print_color(YELLOW, "解压wheel包...")
        success, output = run_command(f"unzip -q {wheel_file} -d {temp_dir}")
        if not success:
            print_color(RED, f"解压wheel包失败: {output}")
            return False, f"解压wheel包失败: {output}", []
        
        # 检查文档
        print_color(YELLOW, "检查文档...")
        found_docs = []
        missing_docs = []
        
        for doc in REQUIRED_DOCS:
            doc_path = os.path.join(temp_dir, doc)
            if os.path.exists(doc_path):
                print_color(GREEN, f"找到文档: {doc}")
                found_docs.append(doc)
            else:
                print_color(RED, f"缺少文档: {doc}")
                missing_docs.append(doc)
        
        if missing_docs:
            print_color(RED, f"Python包缺少以下文档: {', '.join(missing_docs)}")
            return False, f"Python包缺少以下文档: {', '.join(missing_docs)}", found_docs
        else:
            print_color(GREEN, "Python包包含所有必要的文档!")
            return True, "Python包包含所有必要的文档", found_docs

def check_macos_package_docs():
    """检查macOS包中的文档"""
    if platform.system() != "Darwin":
        print_color(YELLOW, "非macOS平台，跳过macOS包文档检查")
        return False, "非macOS平台，跳过macOS包文档检查", []
    
    print_color(YELLOW, "检查macOS包中的文档...")
    
    # 查找DMG文件
    dmg_files = glob.glob(os.path.join(PROJECT_ROOT, "*.dmg"))
    if not dmg_files:
        print_color(YELLOW, "未找到DMG文件")
        return False, "未找到DMG文件", []
    
    dmg_file = dmg_files[0]
    print_color(YELLOW, f"找到DMG文件: {os.path.basename(dmg_file)}")
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        # 挂载DMG文件
        print_color(YELLOW, "挂载DMG文件...")
        success, output = run_command(f"hdiutil attach {dmg_file} -mountpoint {temp_dir}")
        if not success:
            print_color(RED, f"挂载DMG文件失败: {output}")
            return False, f"挂载DMG文件失败: {output}", []
        
        try:
            # 检查文档
            print_color(YELLOW, "检查文档...")
            found_docs = []
            missing_docs = []
            
            # 检查文档目录
            doc_dir = os.path.join(temp_dir, "文档")
            if os.path.exists(doc_dir):
                print_color(GREEN, "找到文档目录")
                
                # 检查文档文件
                for doc in REQUIRED_DOCS:
                    doc_name = os.path.basename(doc)
                    doc_path = os.path.join(doc_dir, doc_name)
                    if os.path.exists(doc_path):
                        print_color(GREEN, f"找到文档: {doc_name}")
                        found_docs.append(doc)
                    else:
                        print_color(RED, f"缺少文档: {doc_name}")
                        missing_docs.append(doc)
            else:
                print_color(RED, "缺少文档目录")
                missing_docs = REQUIRED_DOCS
            
            if missing_docs:
                print_color(RED, f"macOS包缺少以下文档: {', '.join(missing_docs)}")
                return False, f"macOS包缺少以下文档: {', '.join(missing_docs)}", found_docs
            else:
                print_color(GREEN, "macOS包包含所有必要的文档!")
                return True, "macOS包包含所有必要的文档", found_docs
        finally:
            # 卸载DMG文件
            print_color(YELLOW, "卸载DMG文件...")
            run_command(f"hdiutil detach {temp_dir}")

def check_windows_package_docs():
    """检查Windows包中的文档"""
    if platform.system() != "Windows":
        print_color(YELLOW, "非Windows平台，跳过Windows包文档检查")
        return False, "非Windows平台，跳过Windows包文档检查", []
    
    print_color(YELLOW, "检查Windows包中的文档...")
    
    # 查找EXE文件
    exe_files = glob.glob(os.path.join(PROJECT_ROOT, "*.exe"))
    if not exe_files:
        print_color(YELLOW, "未找到EXE文件")
        return False, "未找到EXE文件", []
    
    exe_file = exe_files[0]
    print_color(YELLOW, f"找到EXE文件: {os.path.basename(exe_file)}")
    
    # 由于无法直接解压EXE文件，这里只是简单地检查文件是否存在
    print_color(YELLOW, "无法直接检查EXE文件中的文档，请手动验证")
    return False, "无法直接检查EXE文件中的文档，请手动验证", []

def check_linux_package_docs():
    """检查Linux包中的文档"""
    if platform.system() != "Linux":
        print_color(YELLOW, "非Linux平台，跳过Linux包文档检查")
        return False, "非Linux平台，跳过Linux包文档检查", []
    
    print_color(YELLOW, "检查Linux包中的文档...")
    
    # 查找DEB文件
    deb_files = glob.glob(os.path.join(PROJECT_ROOT, "*.deb"))
    if not deb_files:
        print_color(YELLOW, "未找到DEB文件")
        return False, "未找到DEB文件", []
    
    deb_file = deb_files[0]
    print_color(YELLOW, f"找到DEB文件: {os.path.basename(deb_file)}")
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        # 解压DEB文件
        print_color(YELLOW, "解压DEB文件...")
        success, output = run_command(f"dpkg-deb -x {deb_file} {temp_dir}")
        if not success:
            print_color(RED, f"解压DEB文件失败: {output}")
            return False, f"解压DEB文件失败: {output}", []
        
        # 检查文档
        print_color(YELLOW, "检查文档...")
        found_docs = []
        missing_docs = []
        
        # 检查文档目录
        doc_dir = os.path.join(temp_dir, "usr", "local", "share", "doc", "llm-protection-system")
        if os.path.exists(doc_dir):
            print_color(GREEN, "找到文档目录")
            
            # 检查文档文件
            for doc in REQUIRED_DOCS:
                doc_name = os.path.basename(doc)
                doc_path = os.path.join(doc_dir, doc_name)
                if os.path.exists(doc_path):
                    print_color(GREEN, f"找到文档: {doc_name}")
                    found_docs.append(doc)
                else:
                    print_color(RED, f"缺少文档: {doc_name}")
                    missing_docs.append(doc)
        else:
            print_color(RED, "缺少文档目录")
            missing_docs = REQUIRED_DOCS
        
        if missing_docs:
            print_color(RED, f"Linux包缺少以下文档: {', '.join(missing_docs)}")
            return False, f"Linux包缺少以下文档: {', '.join(missing_docs)}", found_docs
        else:
            print_color(GREEN, "Linux包包含所有必要的文档!")
            return True, "Linux包包含所有必要的文档", found_docs

def check_docker_package_docs():
    """检查Docker包中的文档"""
    print_color(YELLOW, "检查Docker包中的文档...")
    
    # 检查Docker是否已安装
    success, output = run_command("docker --version")
    if not success:
        print_color(YELLOW, "Docker未安装，跳过Docker包文档检查")
        return False, "Docker未安装，跳过Docker包文档检查", []
    
    # 检查Docker守护进程是否运行
    success, output = run_command("docker info")
    if not success:
        print_color(YELLOW, "Docker守护进程未运行，跳过Docker包文档检查")
        return False, "Docker守护进程未运行，跳过Docker包文档检查", []
    
    # 查找Docker镜像
    success, output = run_command("docker images --format '{{.Repository}}:{{.Tag}}' | grep llm-protection-system")
    if not success or not output.strip():
        print_color(YELLOW, "未找到Docker镜像")
        return False, "未找到Docker镜像", []
    
    image_name = output.strip().split("\n")[0]
    print_color(YELLOW, f"找到Docker镜像: {image_name}")
    
    # 创建临时容器并检查文档
    print_color(YELLOW, "创建临时容器并检查文档...")
    container_name = f"doc-check-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    success, output = run_command(f"docker create --name {container_name} {image_name}")
    if not success:
        print_color(RED, f"创建临时容器失败: {output}")
        return False, f"创建临时容器失败: {output}", []
    
    try:
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 从容器中复制文档
            print_color(YELLOW, "从容器中复制文档...")
            found_docs = []
            missing_docs = []
            
            for doc in REQUIRED_DOCS:
                success, _ = run_command(f"docker cp {container_name}:/app/{doc} {temp_dir}/{os.path.basename(doc)}")
                if success:
                    print_color(GREEN, f"找到文档: {doc}")
                    found_docs.append(doc)
                else:
                    print_color(RED, f"缺少文档: {doc}")
                    missing_docs.append(doc)
            
            if missing_docs:
                print_color(RED, f"Docker包缺少以下文档: {', '.join(missing_docs)}")
                return False, f"Docker包缺少以下文档: {', '.join(missing_docs)}", found_docs
            else:
                print_color(GREEN, "Docker包包含所有必要的文档!")
                return True, "Docker包包含所有必要的文档", found_docs
    finally:
        # 删除临时容器
        print_color(YELLOW, "删除临时容器...")
        run_command(f"docker rm {container_name}")

def check_package_docs():
    """确认所有打包文件包含必要的文档"""
    print_color(GREEN, "=" * 50)
    print_color(GREEN, f"本地大模型防护系统打包文档检查工具 v{VERSION}")
    print_color(GREEN, "=" * 50)
    
    # 创建结果目录
    results_dir = os.path.join(PROJECT_ROOT, "package_check_results")
    os.makedirs(results_dir, exist_ok=True)
    
    # 创建结果文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"package_docs_{timestamp}.json")
    
    # 初始化结果
    results = {
        "timestamp": timestamp,
        "version": VERSION,
        "platform": platform.system(),
        "docs_checks": {},
    }
    
    # 检查Python包中的文档
    python_success, python_message, python_found_docs = check_python_package_docs()
    results["docs_checks"]["python"] = {
        "success": python_success,
        "message": python_message,
        "found_docs": python_found_docs,
    }
    
    # 检查macOS包中的文档
    macos_success, macos_message, macos_found_docs = check_macos_package_docs()
    results["docs_checks"]["macos"] = {
        "success": macos_success,
        "message": macos_message,
        "found_docs": macos_found_docs,
    }
    
    # 检查Windows包中的文档
    windows_success, windows_message, windows_found_docs = check_windows_package_docs()
    results["docs_checks"]["windows"] = {
        "success": windows_success,
        "message": windows_message,
        "found_docs": windows_found_docs,
    }
    
    # 检查Linux包中的文档
    linux_success, linux_message, linux_found_docs = check_linux_package_docs()
    results["docs_checks"]["linux"] = {
        "success": linux_success,
        "message": linux_message,
        "found_docs": linux_found_docs,
    }
    
    # 检查Docker包中的文档
    docker_success, docker_message, docker_found_docs = check_docker_package_docs()
    results["docs_checks"]["docker"] = {
        "success": docker_success,
        "message": docker_message,
        "found_docs": docker_found_docs,
    }
    
    # 保存结果
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print_color(GREEN, f"检查结果已保存到: {results_file}")
    
    # 生成报告
    report_file = os.path.join(results_dir, f"package_docs_report_{timestamp}.md")
    with open(report_file, "w") as f:
        f.write(f"# 本地大模型防护系统打包文档检查报告\n\n")
        f.write(f"- **版本**: {VERSION}\n")
        f.write(f"- **时间**: {timestamp}\n")
        f.write(f"- **平台**: {platform.system()}\n\n")
        
        f.write("## 检查结果\n\n")
        
        f.write("| 包类型 | 状态 | 消息 | 找到的文档 |\n")
        f.write("|-------|------|------|------------|\n")
        
        for package_type, check in results["docs_checks"].items():
            status = "✅ 通过" if check["success"] else "❌ 失败"
            found_docs = ", ".join([os.path.basename(doc) for doc in check["found_docs"]]) if check["found_docs"] else "无"
            f.write(f"| {package_type.capitalize()} | {status} | {check['message']} | {found_docs} |\n")
        
        f.write("\n## 必要的文档\n\n")
        f.write("以下是被认为必要的文档：\n\n")
        for doc in REQUIRED_DOCS:
            f.write(f"- {doc}\n")
    
    print_color(GREEN, f"检查报告已生成: {report_file}")
    print_color(GREEN, "=" * 50)
    print_color(GREEN, "打包文档检查完成!")
    print_color(GREEN, "=" * 50)

if __name__ == "__main__":
    check_package_docs()
