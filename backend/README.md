# 知识库管理平台 —— 后端服务

基于 FastAPI 的知识库管理平台后端，集知识维护、多维权限管理、AI 问答鉴权检索、数据看板与知识自动沉淀于一体。

## 功能特性

| 模块 | 能力 |
| --- | --- |
| 认证鉴权 | 用户登录、JWT 签发/校验、RBAC 操作权限拦截 |
| 组织权限 | 用户/角色/部门管理、部门树、四维混合数据权限（全局/部门/角色/个人） |
| 知识单元 | 文档导入（解析→切片→向量化→Milvus）、CRUD、版本管理、标签、状态管理 |
| AI 问答 | 混合召回（Milvus + 关键字）、数据权限鉴权、SSE 流式回答、模型兜底、多轮对话 |
| 数据看板 | 访问指标、常见问题 TOP、知识单元热度榜、Token/耗时趋势（日/周） |
| 知识沉淀 | FAQ 挖掘/审核/缓存、知识缺口识别与一键建档 |

## 技术栈

| 领域 | 选型 |
| --- | --- |
| Web 框架 | FastAPI |
| ORM | SQLAlchemy 2.x（异步） |
| 数据库 | PostgreSQL |
| 缓存 | Redis |
| 向量数据库 | Milvus |
| 工作流编排 | LangGraph |
| 向量化/大模型 | 外部 API（OpenAI 兼容协议） |
| 任务调度 | APScheduler |

## 目录结构

```
backend/
├── app/
│   ├── main.py               # 应用入口、路由注册、异常处理
│   ├── core/                 # 配置、安全、依赖注入、异常、数据库
│   ├── models/               # SQLAlchemy ORM 模型（11 张表）
│   ├── schemas/              # Pydantic 请求/响应模型
│   ├── api/v1/               # 路由层（auth/org/knowledge/ai/dashboard/settlement）
│   ├── services/             # 业务逻辑层（含权限引擎、AI 服务、Milvus 等）
│   ├── workflows/            # LangGraph 工作流（导入 + 检索）
│   ├── jobs/                 # 定时任务（FAQ 挖掘、缺口识别）
│   └── utils/                # 文档解析、文本切片
├── alembic/                  # 数据库迁移
├── scripts/init_db.py        # 建表 + 三角色种子数据
├── md/                       # 项目文档
│   ├── 后端开发文档.md
│   ├── 后端任务文档.md
│   ├── M7-知识入库开发文档.md
│   ├── M8-检索问答开发文档.md
│   └── 后端接口文档.md
├── requirements.txt
├── pyproject.toml
└── .env.example
```

## 环境要求

- Python >= 3.11
- PostgreSQL（含 pgvector 扩展可选）
- Redis
- Milvus（向量数据库）
- 外部 Embedding / LLM API（OpenAI 兼容协议）

## 快速开始

### 1. 创建并激活虚拟环境

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

> 也可使用 uv：`uv sync`

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填写数据库连接、SECRET_KEY、Milvus、Embedding、LLM 等配置
```

### 4. 初始化数据库

```bash
python -m scripts.init_db
```

> 自动建表并写入三角色（admin / knowledge_admin / user）及权限码种子数据。

### 5. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 访问

- 接口文档（Swagger）：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

## 配置项说明

核心配置见 `.env.example`，关键项如下：

| 配置项 | 说明 |
| --- | --- |
| DATABASE_URL | PostgreSQL 连接串 |
| REDIS_URL | Redis 连接串 |
| MILVUS_URL | Milvus 连接地址 |
| CHUNKS_COLLECTION | Milvus 切片集合名（默认 kb_chunks） |
| EMBEDDING_API_URL | 向量化 API 地址（OpenAI 兼容） |
| EMBEDDING_API_KEY | 向量化 API Key |
| EMBEDDING_MODEL | 向量化模型名 |
| EMBEDDING_DIM | 向量维度（默认 1024） |
| LLM_API_URL | 大模型 API 地址 |
| LLM_API_KEY | 大模型 API Key |
| LLM_MODEL | 大模型模型名 |
| SECRET_KEY | JWT 签名密钥 |

## 预置角色与权限

| 角色 | role_code | 默认权限 |
| --- | --- | --- |
| 系统管理员 | admin | 全部权限码 |
| 知识管理员 | knowledge_admin | knowledge:*、faq:*、gap:*、dashboard:view、ai:chat |
| 普通用户 | user | ai:chat |

## 文档导航

| 文档 | 说明 |
| --- | --- |
| [md/后端开发文档.md](md/后端开发文档.md) | 后端设计（技术栈、模块、数据模型、接口） |
| [md/后端任务文档.md](md/后端任务文档.md) | 任务拆解与排期 |
| [md/M7-知识入库开发文档.md](md/M7-知识入库开发文档.md) | 知识入库（解析→切片→向量化→Milvus） |
| [md/M8-检索问答开发文档.md](md/M8-检索问答开发文档.md) | 检索问答（召回→鉴权→兜底） |
| [md/后端接口文档.md](md/后端接口文档.md) | **接口文档（前端开发用）** |

## 核心业务流程

1. **知识导入**：上传文档 → LangGraph 工作流（解析→切片→向量化→Milvus 入库）
2. **AI 问答**：提问 → FAQ 缓存 → 混合召回 → 权限鉴权 → 流式生成（不足则模型兜底）
3. **知识沉淀**：定时挖掘高频问题 → 生成候选 FAQ → 审核发布 → 写入缓存；识别知识缺口

## 测试账号

初始化后默认**不创建管理员账号**（因需密码哈希）。可通过以下方式创建：

```python
# 在 backend 目录下运行
.\.venv\Scripts\python.exe -c "import asyncio; from app.core.database import async_session_factory; from app.models import User, UserRole; from app.core.security import hash_password; async def main(): async with async_session_factory() as db: u = User(username='admin', display_name='管理员', password_hash=hash_password('admin123'), status='active'); db.add(u); await db.flush(); db.add(UserRole(user_id=u.id, role_id=1)); await db.commit(); print('管理员创建成功'); asyncio.run(main())"
```

> 上述代码创建用户名 `admin`、密码 `admin123` 的系统管理员（角色 ID 1 为 admin）。

## 常用命令

```bash
# 启动服务（开发模式，热重载）
uvicorn app.main:app --reload

# 初始化/重置数据库
python -m scripts.init_db

# 运行接口文档
# 浏览器访问 http://localhost:8000/docs
```

## 许可证

内部项目，未开源。
