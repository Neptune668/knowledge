# 知识库管理平台 —— 后端服务

基于 FastAPI 的知识库管理平台后端，支持组织权限、知识单元、AI 鉴权问答、数据看板与知识沉淀。

## 技术栈

Python 3.11 + FastAPI + SQLAlchemy 2.x + PostgreSQL + Redis

## 快速开始

### 1. 启动依赖服务（PostgreSQL + Redis）

使用 Docker Compose 一键启动：

```bash
docker compose up -d
```

仅启动 PostgreSQL：

```bash
docker compose up -d postgres
```

> 数据库连接默认 `root:1234@localhost:5432/kami`，与 `.env.example` 保持一致。

### 2. 安装依赖

```bash
# 创建并激活虚拟环境
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填写 SECRET_KEY、数据库连接等
```

### 4. 初始化数据库（建表 + 三角色种子数据）

```bash
python -m scripts.init_db
```

### 5. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 访问

- 接口文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## 常用命令

```bash
# 查看容器状态
docker compose ps

# 查看 PostgreSQL 日志
docker compose logs -f postgres

# 停止并移除容器（保留数据卷）
docker compose down

# 停止并删除数据卷（清空数据库）
docker compose down -v

# 进入 PostgreSQL 命令行
docker compose exec postgres psql -U root -d kami
```

## 目录结构

见《后端开发文档.md》第 2 节。
