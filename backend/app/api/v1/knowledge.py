"""知识单元接口。"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.services.permission_engine import permission_engine

router = APIRouter(prefix="/knowledge", tags=["知识单元"])


class CheckPermissionsRequest(BaseModel):
    user_id: int = Field(..., description="用户 ID")
    unit_ids: list[int] = Field(..., description="待校验的知识单元 ID 列表")


class CheckPermissionsResponse(BaseModel):
    authorized_unit_ids: list[int]
    unauthorized_unit_ids: list[int]


@router.post("/check-permissions", response_model=CheckPermissionsResponse)
async def check_permissions(
    req: CheckPermissionsRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """校验用户对指定知识单元集合的访问权限。"""
    authorized, unauthorized = await permission_engine.check_units(
        db, req.user_id, req.unit_ids
    )
    return CheckPermissionsResponse(
        authorized_unit_ids=authorized,
        unauthorized_unit_ids=unauthorized,
    )
