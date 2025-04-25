#!/usr/bin/env python3
"""
打包质量检查脚本，用于检查所有打包文件的完整性。
"""

import os
import sys
import glob
import hashlib
import json
import platform
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

# 定义打包文件类型
PACKAGE_TYPES = {
    "python": ["*.whl", "*.tar.gz"],
    "macos": ["*.dmg", "dist/*.app"],
    "windows": ["*.exe", "*.msi"],
    "linux": ["*.deb", "*.rpm", "*.tar.gz"],
    "docker": ["*.tar"],
}

def print_color(color, message):
    """打印彩色文本"""
    print(f"{color}{message}{NC}")

def calculate_file_hash(file_path, algorithm="sha256"):
    """计算文件哈希值"""
    if os.path.isdir(file_path):
        return "目录，无法计算哈希值"

    hash_obj = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

def check_file_exists(file_path):
    """检查文件是否存在"""
    return os.path.exists(file_path)

def check_file_size(file_path, min_size=1024):
    """检查文件大小是否合理"""
    if not os.path.exists(file_path):
        return False
    return os.path.getsize(file_path) >= min_size

def check_package_integrity():
    """检查所有打包文件的完整性"""
    print_color(GREEN, "=" * 50)
    print_color(GREEN, f"本地大模型防护系统打包质量检查工具 v{VERSION}")
    print_color(GREEN, "=" * 50)

    # 创建结果目录
    results_dir = os.path.join(PROJECT_ROOT, "package_check_results")
    os.makedirs(results_dir, exist_ok=True)

    # 创建结果文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = os.path.join(results_dir, f"package_check_{timestamp}.json")

    # 初始化结果
    results = {
        "timestamp": timestamp,
        "version": VERSION,
        "platform": platform.system(),
        "packages": {},
    }

    # 检查所有打包文件
    for package_type, patterns in PACKAGE_TYPES.items():
        print_color(YELLOW, f"检查 {package_type} 包...")
        results["packages"][package_type] = []

        for pattern in patterns:
            files = glob.glob(os.path.join(PROJECT_ROOT, pattern))

            if not files:
                print_color(YELLOW, f"未找到匹配 {pattern} 的文件")
                continue

            for file_path in files:
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                file_hash = calculate_file_hash(file_path) if os.path.exists(file_path) else ""

                print_color(YELLOW, f"检查文件: {file_name}")
                print(f"  路径: {file_path}")
                print(f"  大小: {file_size} 字节")
                print(f"  SHA256: {file_hash}")

                # 检查文件完整性
                exists = check_file_exists(file_path)
                size_ok = check_file_size(file_path)

                if exists and size_ok:
                    print_color(GREEN, "  检查通过!")
                    status = "通过"
                else:
                    if not exists:
                        print_color(RED, "  文件不存在!")
                        status = "文件不存在"
                    elif not size_ok:
                        print_color(RED, "  文件大小异常!")
                        status = "文件大小异常"

                # 添加到结果
                results["packages"][package_type].append({
                    "file_name": file_name,
                    "file_path": file_path,
                    "file_size": file_size,
                    "file_hash": file_hash,
                    "status": status,
                })

    # 保存结果
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)

    print_color(GREEN, f"检查结果已保存到: {results_file}")

    # 生成报告
    report_file = os.path.join(results_dir, f"package_check_report_{timestamp}.md")
    with open(report_file, "w") as f:
        f.write(f"# 本地大模型防护系统打包质量检查报告\n\n")
        f.write(f"- **版本**: {VERSION}\n")
        f.write(f"- **时间**: {timestamp}\n")
        f.write(f"- **平台**: {platform.system()}\n\n")

        f.write("## 检查结果\n\n")

        for package_type, packages in results["packages"].items():
            f.write(f"### {package_type.capitalize()} 包\n\n")

            if not packages:
                f.write("未找到包文件\n\n")
                continue

            f.write("| 文件名 | 大小 | 状态 |\n")
            f.write("|-------|------|------|\n")

            for package in packages:
                size_mb = package["file_size"] / (1024 * 1024)
                f.write(f"| {package['file_name']} | {size_mb:.2f} MB | {package['status']} |\n")

            f.write("\n")

    print_color(GREEN, f"检查报告已生成: {report_file}")
    print_color(GREEN, "=" * 50)
    print_color(GREEN, "打包质量检查完成!")
    print_color(GREEN, "=" * 50)

if __name__ == "__main__":
    check_package_integrity()
