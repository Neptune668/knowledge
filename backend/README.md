# 知识库管理平台 —— 后端服务

基于 FastAPI 的知识库管理平台后端，支持组织权限、知识单元、AI 鉴权问答、数据看板与知识沉淀。

## 技术栈

Python 3.11 + FastAPI + SQLAlchemy 2.x + PostgreSQL + Redis

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填写数据库连接、SECRET_KEY 等

# 3. 初始化数据库（建表 + 三角色种子数据）
python -m scripts.init_db

# 4. 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 访问

- 接口文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## 目录结构

见《后端开发文档.md》第 2 节。
