"""知识沉淀接口：FAQ 审核发布、知识缺口管理。"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models import User
from app.schemas.settlement import (
    FaqOut,
    FaqReviewRequest,
    KnowledgeGapOut,
    ResolveGapRequest,
    UpdateGapStatusRequest,
)
from app.services.settlement_service import settlement_service

router = APIRouter(prefix="/settlement", tags=["知识沉淀"])


# ===== FAQ =====


@router.get("/faqs/recommendations", response_model=list[FaqOut])
async def list_recommendations(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("faq:view")),
):
    """查询待审核 FAQ 推荐列表。"""
    return await settlement_service.list_recommendations(db)


@router.get("/faqs/published", response_model=list[FaqOut])
async def list_published(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("faq:view")),
):
    """查询已发布 FAQ 库。"""
    return await settlement_service.list_published(db)


@router.post("/faqs/{faq_id}/review", response_model=FaqOut)
async def review_faq(
    faq_id: int,
    req: FaqReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("faq:review")),
):
    """审核 FAQ（approve / reject）。"""
    return await settlement_service.review_faq(db, faq_id, req, user.id)


# ===== 知识缺口 =====


@router.get("/knowledge-gaps", response_model=list[KnowledgeGapOut])
async def list_gaps(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("gap:view")),
):
    """查询知识缺口列表与未命中频次。"""
    return await settlement_service.list_gaps(db)


@router.post("/knowledge-gaps/{gap_id}/resolve", response_model=KnowledgeGapOut)
async def resolve_gap(
    gap_id: int,
    req: ResolveGapRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("gap:resolve")),
):
    """处理知识缺口（关联或创建知识单元）。"""
    return await settlement_service.resolve_gap(db, gap_id, req)


@router.put("/knowledge-gaps/{gap_id}/status", response_model=KnowledgeGapOut)
async def update_gap_status(
    gap_id: int,
    req: UpdateGapStatusRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("gap:resolve")),
):
    """变更知识缺口状态。"""
    return await settlement_service.update_gap_status(db, gap_id, req)
