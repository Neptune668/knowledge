# 云端部署说明（腾讯云 + 算力云）

## 1. 部署架构

```
腾讯云服务器（主服务，单机 Docker Compose）
├── Nginx         :80/443  托管前端静态页面 + 反向代理后端 /api
├── 后端 FastAPI  :8000    业务服务
├── PostgreSQL    :5432    业务数据库
├── Redis         :6379    缓存
├── Milvus        :19530   向量数据库（standalone 模式）
├── etcd          :2379    Milvus 元数据
└── MinIO         :9000    Milvus 对象存储

算力云服务器（GPU）
└── embedding 服务（FastAPI 封装模型，OpenAI 兼容 /embeddings）
      ↑ 腾讯云后端通过 EMBEDDING_API_URL 调用
```

## 2. 前置准备

1. 腾讯云服务器（建议 4C8G 以上，Milvus 较吃内存）
2. 服务器已安装 Docker 与 Docker Compose
3. 算力云 embedding 服务已就绪（确认可访问的 URL）
4. （可选）LLM 大模型 API（OpenAI 兼容）

## 3. 部署步骤

### 3.1 上传代码

将整个项目（至少 `backend/` 和 `frontend/` 目录）上传到腾讯云服务器：

```bash
# 示例：通过 git 或 scp 上传到 /opt/kami
mkdir -p /opt/kami
# 上传 backend/ 和 frontend/ 到 /opt/kami/
```

### 3.2 配置环境变量

```bash
cd /opt/kami/backend/deploy/prod
cp .env.prod.example .env.prod
vim .env.prod
```

必改项：
- `SECRET_KEY`：改成随机长字符串
- `POSTGRES_PASSWORD` / `DATABASE_URL`：改数据库密码（两处保持一致）
- `EMBEDDING_API_URL`：改成算力云 embedding 服务的地址
- `LLM_API_URL` / `LLM_API_KEY`：配置大模型（如需模型兜底）

### 3.3 构建并启动

```bash
cd /opt/kami/backend/deploy/prod
docker compose up -d --build
```

首次启动会拉取多个镜像（postgres/redis/milvus/etcd/minio/nginx），耗时较长。

### 3.4 验证

```bash
# 查看容器状态（应全部 Up/healthy）
docker compose ps

# 验证后端
curl http://localhost:8000/health

# 验证 Nginx 转发
curl http://localhost/api/health
# 或浏览器访问 http://服务器IP/ 应看到登录页
```

### 3.5 创建管理员账号

后端容器内执行：

```bash
docker exec -it kami-backend sh
# 进入容器后，执行 Python 创建管理员
python -c "
import asyncio
from app.core.database import async_session_factory
from app.models import User, UserRole
from app.core.security import hash_password
from sqlalchemy import select
from app.models import Role

async def main():
    async with async_session_factory() as db:
        rid = (await db.execute(select(Role.id).where(Role.role_code=='admin'))).scalar_one()
        u = User(username='admin', display_name='管理员', password_hash=hash_password('你的密码'), status='active')
        db.add(u); await db.flush()
        db.add(UserRole(user_id=u.id, role_id=rid))
        await db.commit()
        print('OK')

asyncio.run(main())
"
exit
```

## 4. 算力云 embedding 服务要求

算力云的 embedding 服务需实现 OpenAI 兼容的 `/embeddings` 接口：

**请求**：
```json
POST /v1/embeddings
{ "model": "qwen3.7-text-embedding", "input": "文本" }
```

**响应**：
```json
{
  "data": [{ "embedding": [0.1, 0.2, ...] }]
}
```

> 关键：返回的向量维度必须与 `EMBEDDING_DIM`（默认 1024）一致。
> 若你封装的 FastAPI 服务返回格式不同，需同步调整 `backend/app/services/embedding_client.py`。

## 5. 常用运维命令

```bash
cd /opt/kami/backend/deploy/prod

# 查看所有容器状态
docker compose ps

# 查看后端日志
docker compose logs -f backend

# 重启后端
docker compose restart backend

# 更新代码后重新构建后端
docker compose up -d --build backend

# 停止所有服务
docker compose down

# 停止并清空数据（危险！）
docker compose down -v
```

## 6. 安全注意事项

1. **修改默认密码**：PostgreSQL 密码、SECRET_KEY 务必修改
2. **MinIO 默认凭证**：`minioadmin/minioadmin` 建议修改（Milvus 内部用）
3. **防火墙**：只开放 80/443（Nginx），不要直接暴露 8000/5432/6379/19530 到公网
4. **HTTPS**：有域名时启用 nginx.conf 里的 HTTPS 配置 + SSL 证书
5. **CORS**：同源部署时 `CORS_ORIGINS` 留空即可
6. **算力云安全组**：embedding 服务只允许腾讯云服务器 IP 访问

## 7. 常见问题

| 问题 | 处理 |
| --- | --- |
| Milvus 启动失败/内存不足 | 腾讯云至少 4G 内存；或改用云托管向量库（改 MILVUS_URL） |
| embedding 调用失败 | 检查算力云安全组是否放行腾讯云 IP；检查 URL 格式 |
| 登录后接口 401 | 确认前端 BASE_URL 为 `/api`（同源部署） |
| 数据看板报错 | 确认已执行 init_db 建表（后端容器启动时自动执行） |
