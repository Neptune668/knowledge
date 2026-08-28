#!/bin/sh
set -e

echo "=== 后端容器启动 ==="

# 等待 PostgreSQL 就绪（最多 60 秒）
echo "等待 PostgreSQL 就绪..."
RETRIES=30
while [ $RETRIES -gt 0 ]; do
    if python /app/check_db.py; then
        echo "PostgreSQL 连接成功"
        break
    fi
    RETRIES=$((RETRIES-1))
    if [ $RETRIES -le 0 ]; then
        echo "PostgreSQL 连接超时，退出"
        exit 1
    fi
    echo "PostgreSQL 尚未就绪，重试中...（剩余 $RETRIES 次）"
    sleep 2
done

# 初始化数据库
echo "初始化数据库..."
python -m scripts.init_db

# 启动服务
echo "启动后端服务..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
