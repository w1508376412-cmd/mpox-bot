#!/bin/bash

# 猴痘知识问答机器人 - 快速启动脚本

set -e

echo "=================================="
echo "猴痘知识问答机器人 - 快速启动"
echo "=================================="

# 检查Python版本
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python 3"
    echo "请先安装 Python 3.9 或更高版本"
    exit 1
fi

echo "✓ Python 版本: $(python3 --version)"

# 检查PostgreSQL
if ! command -v psql &> /dev/null; then
    echo "❌ 错误: 未找到 PostgreSQL"
    echo "请先安装 PostgreSQL 和 pgvector"
    echo ""
    echo "macOS: brew install postgresql pgvector"
    echo "Ubuntu: sudo apt-get install postgresql postgresql-contrib"
    exit 1
fi

echo "✓ PostgreSQL 已安装"

# 检查.env文件
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  未找到 .env 文件"
    echo "正在从 .env.example 创建..."
    cp .env.example .env
    echo ""
    echo "请编辑 .env 文件，填入您的 OpenAI API Key："
    echo "  OPENAI_API_KEY=your_api_key_here"
    echo ""
    read -p "按回车键继续..."
fi

# 检查API Key
source .env
if [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ] || [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ 错误: 请先在 .env 文件中配置 OPENAI_API_KEY"
    exit 1
fi

echo "✓ 环境变量已配置"

# 安装依赖
echo ""
echo "正在安装 Python 依赖..."
pip3 install -q -r requirements.txt
echo "✓ 依赖安装完成"

# 检查数据库
echo ""
echo "正在检查数据库..."
if ! psql -lqt | cut -d \| -f 1 | grep -qw mpox_bot; then
    echo "创建数据库 mpox_bot..."
    createdb mpox_bot
    echo "✓ 数据库创建完成"
fi

# 初始化数据库表
echo "初始化数据库表..."
psql mpox_bot < init_db.sql > /dev/null 2>&1
echo "✓ 数据库表初始化完成"

# 检查是否有数据
CHUNK_COUNT=$(psql mpox_bot -t -c "SELECT COUNT(*) FROM chunks;" 2>/dev/null | xargs)

if [ "$CHUNK_COUNT" = "0" ] || [ -z "$CHUNK_COUNT" ]; then
    echo ""
    echo "⚠️  数据库中没有数据"
    echo "是否现在抓取和处理数据？(这可能需要几分钟)"
    read -p "继续? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "正在抓取权威数据源..."
        cd backend
        python3 crawler.py
        echo ""
        echo "正在处理数据并生成向量..."
        python3 process_data.py
        cd ..
        echo "✓ 数据处理完成"
    else
        echo ""
        echo "⚠️  跳过数据处理"
        echo "稍后可以运行以下命令处理数据："
        echo "  cd backend && python3 crawler.py && python3 process_data.py"
    fi
else
    echo "✓ 数据库中已有 $CHUNK_COUNT 条知识片段"
fi

# 启动服务
echo ""
echo "=================================="
echo "准备启动服务..."
echo "=================================="
echo ""
echo "API 地址: http://localhost:8000"
echo "前端页面: http://localhost:8000"
echo "API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

cd backend
python3 main.py
