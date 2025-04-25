#!/usr/bin/env python3
"""
验证所有打包文件的功能。
"""

import os
import sys
import glob
import json
import platform
import subprocess
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

def verify_python_package():
    """验证Python包的功能"""
    print_color(YELLOW, "验证Python包...")
    
    # 查找Python包
    wheel_files = glob.glob(os.path.join(PROJECT_ROOT, "dist", "*.whl"))
    if not wheel_files:
        print_color(YELLOW, "未找到Python wheel包")
        return False, "未找到Python wheel包"
    
    wheel_file = wheel_files[0]
    print_color(YELLOW, f"找到Python wheel包: {os.path.basename(wheel_file)}")
    
    # 创建虚拟环境
    print_color(YELLOW, "创建虚拟环境...")
    venv_dir = os.path.join(PROJECT_ROOT, "verify_venv")
    if os.path.exists(venv_dir):
        print_color(YELLOW, "删除旧的虚拟环境...")
        if platform.system() == "Windows":
            success, output = run_command(f"rmdir /s /q {venv_dir}")
        else:
            success, output = run_command(f"rm -rf {venv_dir}")
    
    print_color(YELLOW, "创建新的虚拟环境...")
    success, output = run_command(f"python -m venv {venv_dir}")
    if not success:
        print_color(RED, f"创建虚拟环境失败: {output}")
        return False, f"创建虚拟环境失败: {output}"
    
    # 激活虚拟环境并安装包
    print_color(YELLOW, "安装Python包...")
    if platform.system() == "Windows":
        activate_cmd = f"{venv_dir}\\Scripts\\activate"
        pip_cmd = f"{venv_dir}\\Scripts\\pip"
    else:
        activate_cmd = f"source {venv_dir}/bin/activate"
        pip_cmd = f"{venv_dir}/bin/pip"
    
    success, output = run_command(f"{pip_cmd} install {wheel_file}")
    if not success:
        print_color(RED, f"安装Python包失败: {output}")
        return False, f"安装Python包失败: {output}"
    
    # 验证安装
    print_color(YELLOW, "验证安装...")
    if platform.system() == "Windows":
        python_cmd = f"{venv_dir}\\Scripts\\python"
    else:
        python_cmd = f"{venv_dir}/bin/python"
    
    success, output = run_command(f"{python_cmd} -c \"import src; print('导入成功')\"")
    if not success:
        print_color(RED, f"验证安装失败: {output}")
        return False, f"验证安装失败: {output}"
    
    print_color(GREEN, "Python包验证成功!")
    return True, "Python包验证成功"

def verify_macos_package():
    """验证macOS包的功能"""
    if platform.system() != "Darwin":
        print_color(YELLOW, "非macOS平台，跳过macOS包验证")
        return False, "非macOS平台，跳过macOS包验证"
    
    print_color(YELLOW, "验证macOS包...")
    
    # 查找DMG文件
    dmg_files = glob.glob(os.path.join(PROJECT_ROOT, "*.dmg"))
    if not dmg_files:
        print_color(YELLOW, "未找到DMG文件")
        return False, "未找到DMG文件"
    
    dmg_file = dmg_files[0]
    print_color(YELLOW, f"找到DMG文件: {os.path.basename(dmg_file)}")
    
    # 验证DMG文件
    print_color(YELLOW, "验证DMG文件完整性...")
    success, output = run_command(f"hdiutil verify {dmg_file}")
    if not success:
        print_color(RED, f"DMG文件验证失败: {output}")
        return False, f"DMG文件验证失败: {output}"
    
    print_color(GREEN, "macOS包验证成功!")
    return True, "macOS包验证成功"

def verify_windows_package():
    """验证Windows包的功能"""
    if platform.system() != "Windows":
        print_color(YELLOW, "非Windows平台，跳过Windows包验证")
        return False, "非Windows平台，跳过Windows包验证"
    
    print_color(YELLOW, "验证Windows包...")
    
    # 查找EXE文件
    exe_files = glob.glob(os.path.join(PROJECT_ROOT, "*.exe"))
    if not exe_files:
        print_color(YELLOW, "未找到EXE文件")
        return False, "未找到EXE文件"
    
    exe_file = exe_files[0]
    print_color(YELLOW, f"找到EXE文件: {os.path.basename(exe_file)}")
    
    # 验证EXE文件
    print_color(YELLOW, "验证EXE文件...")
    # 这里只是简单地检查文件是否存在，实际验证需要更复杂的逻辑
    if os.path.exists(exe_file) and os.path.getsize(exe_file) > 1024:
        print_color(GREEN, "Windows包验证成功!")
        return True, "Windows包验证成功"
    else:
        print_color(RED, "Windows包验证失败!")
        return False, "Windows包验证失败"

def verify_linux_package():
    """验证Linux包的功能"""
    if platform.system() != "Linux":
        print_color(YELLOW, "非Linux平台，跳过Linux包验证")
        return False, "非Linux平台，跳过Linux包验证"
    
    print_color(YELLOW, "验证Linux包...")
    
    # 查找DEB文件
    deb_files = glob.glob(os.path.join(PROJECT_ROOT, "*.deb"))
    if not deb_files:
        print_color(YELLOW, "未找到DEB文件")
        return False, "未找到DEB文件"
    
    deb_file = deb_files[0]
    print_color(YELLOW, f"找到DEB文件: {os.path.basename(deb_file)}")
    
    # 验证DEB文件
    print_color(YELLOW, "验证DEB文件...")
    success, output = run_command(f"dpkg --info {deb_file}")
    if not success:
        print_color(RED, f"DEB文件验证失败: {output}")
        return False, f"DEB文件验证失败: {output}"
    
    print_color(GREEN, "Linux包验证成功!")
    return True, "Linux包验证成功"

def verify_docker_package():
    """验证Docker包的功能"""
    print_color(YELLOW, "验证Docker包...")
    
    # 检查Docker是否已安装
    success, output = run_command("docker --version")
    if not success:
        print_color(YELLOW, "Docker未安装，跳过Docker包验证")
        return False, "Docker未安装，跳过Docker包验证"
    
    # 检查Docker守护进程是否运行
    success, output = run_command("docker info")
    if not success:
        print_color(YELLOW, "Docker守护进程未运行，跳过Docker包验证")
        return False, "Docker守护进程未运行，跳过Docker包验证"
    
    # 查找Docker镜像
    success, output = run_command("docker images --format '{{.Repository}}:{{.Tag}}' | grep llm-protection-system")
    if not success or not output.strip():
        print_color(YELLOW, "未找到Docker镜像")
        return False, "未找到Docker镜像"
    
    image_name = output.strip().split("\n")[0]
    print_color(YELLOW, f"找到Docker镜像: {image_name}")
    
    # 验证Docker镜像
    print_color(YELLOW, "验证Docker镜像...")
    success, output = run_command(f"docker inspect {image_name}")
    if not success:
        print_color(RED, f"Docker镜像验证失败: {output}")
        return False, f"Docker镜像验证失败: {output}"
    
    print_color(GREEN, "Docker包验证成功!")
    return True, "Docker包验证成功"

def verify_packages():
    """验证所有打包文件的功能"""
    print_color(GREEN, "=" * 50)
    print_color(GREEN, f"本地大模型防护系统打包功能验证工具 v{VERSION}")
    print_color(GREEN, "=" * 50)
    
    # 创建结果目录
    results_dir = os.path.join(PROJECT_ROOT, "package_check_results")
    os.makedirs(results_dir, exist_ok=True)
    
    # 创建结果文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"package_verify_{timestamp}.json")
    
    # 初始化结果
    results = {
        "timestamp": timestamp,
        "version": VERSION,
        "platform": platform.system(),
        "verifications": {},
    }
    
    # 验证Python包
    python_success, python_message = verify_python_package()
    results["verifications"]["python"] = {
        "success": python_success,
        "message": python_message,
    }
    
    # 验证macOS包
    macos_success, macos_message = verify_macos_package()
    results["verifications"]["macos"] = {
        "success": macos_success,
        "message": macos_message,
    }
    
    # 验证Windows包
    windows_success, windows_message = verify_windows_package()
    results["verifications"]["windows"] = {
        "success": windows_success,
        "message": windows_message,
    }
    
    # 验证Linux包
    linux_success, linux_message = verify_linux_package()
    results["verifications"]["linux"] = {
        "success": linux_success,
        "message": linux_message,
    }
    
    # 验证Docker包
    docker_success, docker_message = verify_docker_package()
    results["verifications"]["docker"] = {
        "success": docker_success,
        "message": docker_message,
    }
    
    # 保存结果
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print_color(GREEN, f"验证结果已保存到: {results_file}")
    
    # 生成报告
    report_file = os.path.join(results_dir, f"package_verify_report_{timestamp}.md")
    with open(report_file, "w") as f:
        f.write(f"# 本地大模型防护系统打包功能验证报告\n\n")
        f.write(f"- **版本**: {VERSION}\n")
        f.write(f"- **时间**: {timestamp}\n")
        f.write(f"- **平台**: {platform.system()}\n\n")
        
        f.write("## 验证结果\n\n")
        
        f.write("| 包类型 | 状态 | 消息 |\n")
        f.write("|-------|------|------|\n")
        
        for package_type, verification in results["verifications"].items():
            status = "✅ 通过" if verification["success"] else "❌ 失败"
            f.write(f"| {package_type.capitalize()} | {status} | {verification['message']} |\n")
    
    print_color(GREEN, f"验证报告已生成: {report_file}")
    print_color(GREEN, "=" * 50)
    print_color(GREEN, "打包功能验证完成!")
    print_color(GREEN, "=" * 50)

if __name__ == "__main__":
    verify_packages()
