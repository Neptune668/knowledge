# 后端项目本机 Docker 部署说明

本目录用于后端项目的 Docker 化部署，编排后端服务 + PostgreSQL + Redis 三个容器（Milvus 为外部已有服务，不纳入本编排）。

## 目录结构

```
deploy/
├── Dockerfile             # 后端镜像构建文件
├── docker-compose.yml     # 编排后端 + PostgreSQL + Redis
├── docker-entrypoint.sh   # 容器启动脚本（等待DB→初始化→启动）
├── .env.docker            # Docker 部署环境变量（按需修改）
└── README.md              # 本说明
```

> 另有 `../.dockerignore`（在 backend 根目录），用于排除 venv、缓存、文档等无关文件。

## 前置条件

1. 已安装 Docker 与 Docker Compose（`docker compose version` 可验证）
2. Milvus 服务可访问（外部地址，见 `.env.docker` 的 `MILVUS_URL`）
3. Embedding API 可用（`.env.docker` 已配置 DashScope）

## 部署步骤

### 1. 检查/修改环境变量

编辑 `deploy/.env.docker`，确认以下配置正确：

- `SECRET_KEY`：生产环境务必修改
- `EMBEDDING_API_KEY`：向量化 API Key
- `MILVUS_URL`：Milvus 地址
- `LLM_API_URL` / `LLM_API_KEY`：大模型 API（如使用模型兜底，需配置）

### 2. 构建并启动

在 `backend` 目录下执行：

```bash
cd backend
docker compose -f deploy/docker-compose.yml up -d --build
```

> 首次构建需拉取镜像并安装依赖，耗时较长（取决于网络）。

### 3. 查看运行状态

```bash
docker compose -f deploy/docker-compose.yml ps
```

预期三个容器均为 `Up`（或 `healthy`）状态：`kami-postgres`、`kami-redis`、`kami-backend`。

### 4. 验证服务

```bash
# 健康检查
curl http://localhost:8000/health

# 查看接口文档
# 浏览器访问 http://localhost:8000/docs
```

## 查看日志

```bash
# 后端日志
docker logs -f kami-backend

# PostgreSQL 日志
docker logs -f kami-postgres
```

## 停止与清理

```bash
# 停止容器（保留数据卷）
docker compose -f deploy/docker-compose.yml down

# 停止并删除数据卷（清空数据库，谨慎）
docker compose -f deploy/docker-compose.yml down -v

# 停止并删除镜像
docker compose -f deploy/docker-compose.yml down --rmi all
```

## 常用操作

```bash
# 重新构建后端镜像（代码更新后）
docker compose -f deploy/docker-compose.yml up -d --build backend

# 进入后端容器
docker exec -it kami-backend sh

# 进入 PostgreSQL
docker exec -it kami-postgres psql -U root -d kami
```

## 配置说明

| 配置项 | 说明 |
| --- | --- |
| DATABASE_URL | 容器内自动指向 `postgres` 服务（compose 覆盖） |
| REDIS_URL | 容器内自动指向 `redis` 服务（compose 覆盖） |
| MILVUS_URL | 外部 Milvus 地址（宿主机网络） |
| CHUNKS_COLLECTION | Milvus 切片集合名 |
| EMBEDDING_API_URL/KEY | 向量化 API（DashScope OpenAI 兼容） |
| LLM_API_URL/KEY | 大模型 API |

## 注意事项

1. **数据库自动初始化**：后端容器启动时会自动执行 `init_db`（建表 + 三角色种子），首次启动即可用。
2. **默认无管理员账号**：初始化只建角色不建用户，需手动创建管理员（见 `../README.md` 测试账号章节）。
3. **Milvus 需外部可访问**：`MILVUS_URL=http://192.168.222.99:19530` 是宿主机网络地址，容器内需能访问该地址。
4. **端口冲突**：若本机 5432/6379/8000 已被占用，修改 `docker-compose.yml` 中对应 `ports` 映射。
5. **敏感信息**：`.env.docker` 含 API Key，请勿提交到版本库（建议加入 `.gitignore`）。
