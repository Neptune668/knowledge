# 知识库管理平台

集知识维护、多维权限管理、AI 问答鉴权检索、数据看板与知识自动沉淀于一体的知识库管理平台。

## 项目结构

```
kami/
├── backend/                    # 后端服务（Python FastAPI）
│   ├── app/                    # 应用代码
│   ├── alembic/                # 数据库迁移
│   ├── scripts/                # 初始化脚本
│   ├── md/                     # 后端相关文档
│   │   ├── 后端需求文档.md
│   │   ├── 后端开发文档.md
│   │   └── 后端任务文档.md
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── .env.example
│   └── README.md               # 后端运行说明
├── 需求文档.md                  # 总需求文档
└── 前端需求文档.md              # 前端需求文档
```

## 文档导航

| 文档 | 说明 |
| --- | --- |
| [需求文档.md](./需求文档.md) | 平台总体需求 |
| [前端需求文档.md](./前端需求文档.md) | 前端页面与交互需求 |
| [backend/md/后端需求文档.md](./backend/md/后端需求文档.md) | 后端需求（服务模块、接口契约、数据模型） |
| [backend/md/后端开发文档.md](./backend/md/后端开发文档.md) | 后端开发设计（技术栈、模块设计、接口） |
| [backend/md/后端任务文档.md](./backend/md/后端任务文档.md) | 后端任务拆解与排期 |

## 技术栈

- **后端**：Python 3.11 + FastAPI + SQLAlchemy 2.x + PostgreSQL + Redis + LangGraph

## 快速开始

后端启动方式见 [backend/README.md](./backend/README.md)。

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # 编辑数据库连接、SECRET_KEY
python -m scripts.init_db
uvicorn app.main:app --reload
```
