# 知识库管理平台后端镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置时区与编码
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100

# 配置 pip 使用国内镜像源（清华源），加速依赖下载
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 先复制依赖文件，利用 Docker 缓存层
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app ./app
COPY scripts ./scripts
COPY alembic.ini .
COPY alembic ./alembic

# 复制入口脚本
COPY deploy/docker-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# 暴露端口
EXPOSE 8000

# 入口
ENTRYPOINT ["/entrypoint.sh"]
