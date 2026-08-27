"""知识单元接口。"""

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models import User
from app.schemas.knowledge import (
    BatchDeleteRequest,
    ConfigPermissionsRequest,
    KnowledgeUnitDetail,
    KnowledgeUnitListResponse,
    KnowledgeUnitOut,
    KnowledgeUnitUpdate,
    UnitPermissionOut,
)
from app.services.import_service import import_service
from app.services.knowledge_service import knowledge_service
from app.services.permission_engine import permission_engine

router = APIRouter(prefix="/knowledge", tags=["知识单元"])


class CheckPermissionsRequest(BaseModel):
    user_id: int = Field(..., description="用户 ID")
    unit_ids: list[int] = Field(..., description="待校验的知识单元 ID 列表")


class CheckPermissionsResponse(BaseModel):
    authorized_unit_ids: list[int]
    unauthorized_unit_ids: list[int]


# ===== 数据权限校验 =====


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


# ===== 知识单元 CRUD =====


@router.get("/units", response_model=KnowledgeUnitListResponse)
async def list_units(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    title: str | None = None,
    category: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("knowledge:view")),
):
    """分页查询知识单元列表。"""
    return await knowledge_service.list_units(db, page, page_size, title, category, status)


@router.get("/units/{unit_id}", response_model=KnowledgeUnitDetail)
async def get_unit(
    unit_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("knowledge:view")),
):
    """查询知识单元详情与已配置权限列表。"""
    return await knowledge_service.get_unit(db, unit_id)


@router.put("/units/{unit_id}", response_model=KnowledgeUnitOut)
async def update_unit(
    unit_id: int,
    req: KnowledgeUnitUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("knowledge:update")),
):
    """更新知识单元内容。"""
    return await knowledge_service.update_unit(db, unit_id, req)


@router.delete("/units")
async def delete_units(
    req: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("knowledge:delete")),
):
    """批量删除知识单元。"""
    await knowledge_service.delete_units(db, req.unit_ids)
    return {"code": 0, "message": "ok", "data": None}


@router.post("/units/{unit_id}/permissions", response_model=list[UnitPermissionOut])
async def config_permissions(
    unit_id: int,
    req: ConfigPermissionsRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("knowledge:perm_config")),
):
    """批量配置知识单元数据权限（覆盖式写入）。"""
    return await knowledge_service.config_permissions(db, unit_id, req)


# ===== 导入 =====


@router.post("/import")
async def import_knowledge(
    files: list[UploadFile] = File(...),
    _: User = Depends(require_permission("knowledge:import")),
):
    """单/多文件上传解析入库。"""
    file_list = [(f.filename, await f.read()) for f in files]
    task_id = await import_service.import_files(file_list)
    return {"code": 0, "message": "ok", "data": {"task_id": task_id}}


@router.get("/import/{task_id}")
async def get_import_status(
    task_id: str,
    _: User = Depends(require_permission("knowledge:import")),
):
    """查询导入任务进度。"""
    status = import_service.get_status(task_id)
    if status is None:
        return {"code": 0, "message": "ok", "data": None}
    return {"code": 0, "message": "ok", "data": status}
