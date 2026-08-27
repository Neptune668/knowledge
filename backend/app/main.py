"""FastAPI 应用入口。"""

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.exceptions import (
    BizError,
    biz_error_handler,
    http_error_handler,
    validation_error_handler,
)
from app.api.v1 import ai, auth, dashboard, knowledge, org, settlement

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 注册异常处理器
app.add_exception_handler(BizError, biz_error_handler)
app.add_exception_handler(StarletteHTTPException, http_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(org.router, prefix="/api")
app.include_router(knowledge.router, prefix="/api")
app.include_router(ai.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(settlement.router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """应用启动：启动定时任务调度器。"""
    from app.jobs.settlement_jobs import start_scheduler

    start_scheduler()


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭：停止调度器。"""
    from app.jobs.settlement_jobs import shutdown_scheduler

    shutdown_scheduler()


@app.get("/health", tags=["系统"])
async def health():
    """健康检查。"""
    return {"status": "ok", "app": settings.app_name}
