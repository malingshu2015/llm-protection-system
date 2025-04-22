#!/usr/bin/env python3
"""
Script to update the shield icon in all HTML files with a simpler approach.
"""

import os
import re

# 新的盾牌图标 - 已经是base64编码的SVG
NEW_SHIELD_ICON = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9ImN1cnJlbnRDb2xvciIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiIGNsYXNzPSJsdWNpZGUgbHVjaWRlLXNoaWVsZCI+PHBhdGggZD0iTTEyIDIycy04LTUtOC0xMlY1bDgtM2w4IDN2N2MwIDctOCAxMi04IDEyeiIvPjwvc3ZnPg=="

# 旧的盾牌图标模式
OLD_SHIELD_ICON_PATTERN = r'data:image/svg\+xml;base64,[A-Za-z0-9+/=]+'

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
    
    # 查找并替换图标
    if re.search(OLD_SHIELD_ICON_PATTERN, content):
        content = re.sub(OLD_SHIELD_ICON_PATTERN, NEW_SHIELD_ICON, content)
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Updated shield icon in {file_path}")
    else:
        print(f"No shield icon found in {file_path}")

if __name__ == "__main__":
    update_html_files()
    print("All HTML files have been updated.")
