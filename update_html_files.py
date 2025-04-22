#!/usr/bin/env python3
"""
Script to update all HTML files to replace 'LLM 安全防火墙' with '本地大模型防护系统'
and update the logo image.
"""

import os
import re

# 定义要替换的内容
OLD_TITLE = "LLM 安全防火墙"
NEW_TITLE = "本地大模型防护系统"
OLD_LOGO = "https://cdn-icons-png.flaticon.com/512/2363/2363407.png"
NEW_LOGO = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJjdXJyZW50Q29sb3IiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBjbGFzcz0ibHVjaWRlIGx1Y2lkZS1zaGllbGQiPjxwYXRoIGQ9Ik0xMiAyMnMtOC01LTgtMTJWNWw4LTNoOGwxIDN2N2MwIDctOCAxMi04IDEyWiIvPjwvc3ZnPg=="

# 定义要处理的目录
STATIC_DIR = "static"

def update_html_files():
    """Update all HTML files in the static directory."""
    for root, _, files in os.walk(STATIC_DIR):
        for file in files:
            if file.endswith(".html"):
                file_path = os.path.join(root, file)
                update_file(file_path)

def update_file(file_path):
    """Update a single HTML file."""
    print(f"Processing {file_path}...")
    
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 替换标题
    content = content.replace(OLD_TITLE, NEW_TITLE)
    
    # 替换logo
    content = content.replace(OLD_LOGO, NEW_LOGO)
    
    # 替换title标签内容
    content = re.sub(
        r'<title>(.*?)' + re.escape(OLD_TITLE) + r'(.*?)</title>',
        r'<title>\1' + NEW_TITLE + r'\2</title>',
        content
    )
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Updated {file_path}")

if __name__ == "__main__":
    update_html_files()
    print("All HTML files have been updated.")
