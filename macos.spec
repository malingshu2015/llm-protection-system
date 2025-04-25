# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

# 获取项目根目录
project_root = os.path.abspath(os.getcwd())

# 收集所有需要的数据文件
datas = [
    # 静态文件
    (os.path.join(project_root, 'static'), 'static'),
    # 规则文件
    (os.path.join(project_root, 'rules'), 'rules'),
    # 版本文件
    (os.path.join(project_root, 'VERSION'), '.'),
    # 添加其他可能需要的数据文件
    (os.path.join(project_root, 'README.md'), '.'),
]

# 主要的 Python 脚本
a = Analysis(
    [os.path.join(project_root, 'src', 'main.py')],
    pathex=[project_root],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'fastapi',
        'uvicorn',
        'starlette',
        'pydantic',
        'pydantic_settings',
        'aiohttp',
        'requests',
        'httpx',
        'psutil',
        'python-dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 创建 PYZ 归档
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 创建可执行文件
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='llm-protection-system',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_root, 'static', 'favicon.ico'),
)

# 创建收集文件
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='llm-protection-system',
)

# macOS 应用程序打包
app = BUNDLE(
    coll,
    name='本地大模型防护系统.app',
    # 移除图标设置，因为需要Pillow库来转换图标文件
    # icon=os.path.join(project_root, 'static', 'favicon.ico'),
    bundle_identifier='com.llm.protection.system',
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': 'True',
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
    },
)
