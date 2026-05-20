#!/bin/bash

# 猴痘知识库 - 每日数据自动更新脚本
# 此脚本由 Gemini CLI 自动生成

# 1. 获取项目根目录 (根据脚本位置)
PROJECT_DIR="/Users/yanfei/Library/Application Support/0011/workspaces/default/mpox-bot"
cd "$PROJECT_DIR"

# 2. 载入环境变量 (如果需要)
if [ -f .env ]; then
    # 简单载入方式，注意 key=value 格式
    export $(grep -v '^#' .env | xargs)
fi

# 3. 设置 PYTHONPATH
export PYTHONPATH="$PROJECT_DIR/backend"

# 4. 执行更新程序
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始更新任务..." >> update.log
./venv/bin/python3 backend/process_dashboard_data.py >> update.log 2>&1

if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 更新成功" >> update.log
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 更新失败，请检查日志" >> update.log
fi
