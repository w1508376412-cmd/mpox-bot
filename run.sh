#!/bin/bash

# 猴痘知识问答机器人 - 简单启动脚本

PROJECT_DIR="/Users/yanfei/Library/Application Support/0011/workspaces/default/mpox-bot"

echo "=================================="
echo "猴痘知识问答机器人"
echo "=================================="
echo ""

# 进入项目目录
cd "$PROJECT_DIR"

# 激活虚拟环境
source venv/bin/activate

# 启动服务
echo "正在启动服务..."
echo "服务地址: http://localhost:8000"
echo "按 Ctrl+C 停止服务"
echo ""

python backend/main.py
