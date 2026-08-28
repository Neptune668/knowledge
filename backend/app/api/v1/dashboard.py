"""数据看板接口。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_permission
from app.models import User
from app.schemas.dashboard import (
    MetricsResponse,
    QuestionRankingItem,
    TokenTrendItem,
    UnitRankingItem,
)
from app.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["数据看板"])


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("dashboard:view")),
):
    """查询访问总次数、独立用户数、知识单元数、Token 总量与平均耗时。"""
    return await dashboard_service.get_metrics(db)


@router.get("/rankings/questions", response_model=list[QuestionRankingItem])
async def get_question_rankings(
    top: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("dashboard:view")),
):
    """查询常见问题 TOP 榜。"""
    return await dashboard_service.get_question_rankings(db, top)


@router.get("/rankings/units", response_model=list[UnitRankingItem])
async def get_unit_rankings(
    top: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("dashboard:view")),
):
    """查询最常访问知识单元 TOP 榜。"""
    return await dashboard_service.get_unit_rankings(db, top)


@router.get("/stats/tokens", response_model=list[TokenTrendItem])
async def get_token_trend(
    days: int = Query(7, ge=1, le=90),
    granularity: str = Query("day", pattern="^(day|week)$"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("dashboard:view")),
):
    """查询 Token 消耗与响应时间趋势（按日/周）。"""
    return await dashboard_service.get_token_trend(db, days, granularity)
