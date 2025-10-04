#!/bin/bash
# LLM Protection System 后端服务器启动脚本

# 设置工作目录
cd "$(dirname "$0")"

# 激活虚拟环境
source venv/bin/activate

# 设置 PYTHONPATH
export PYTHONPATH=.

# 启动服务器
python src/main.py
