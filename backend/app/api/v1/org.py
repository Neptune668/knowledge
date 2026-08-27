"""组织架构接口：部门、用户、角色管理。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_permission
from app.schemas.org import (
    AssignPermissionRequest,
    DepartmentCreate,
    DepartmentOut,
    DepartmentTreeNode,
    DepartmentUpdate,
    ResetPasswordRequest,
    RoleCreate,
    RoleOut,
    RoleUpdate,
    UpdateStatusRequest,
    UserCreate,
    UserListResponse,
    UserOut,
    UserUpdate,
)
from app.services.org_service import org_service

router = APIRouter(prefix="/org", tags=["组织架构"])


# ===== 部门 =====


@router.get("/departments", response_model=list[DepartmentTreeNode])
async def get_departments(db: AsyncSession = Depends(get_db)):
    """获取部门树形列表。"""
    return await org_service.get_department_tree(db)


@router.post("/departments", response_model=DepartmentOut)
async def create_department(
    req: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("dept:create")),
):
    """新增部门。"""
    return await org_service.create_department(db, req)


@router.put("/departments/{dept_id}", response_model=DepartmentOut)
async def update_department(
    dept_id: int,
    req: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("dept:update")),
):
    """编辑部门。"""
    return await org_service.update_department(db, dept_id, req)


@router.delete("/departments/{dept_id}")
async def delete_department(
    dept_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("dept:delete")),
):
    """删除部门（需无子部门与成员）。"""
    await org_service.delete_department(db, dept_id)
    return {"code": 0, "message": "ok", "data": None}


# ===== 用户 =====


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    department_id: int | None = None,
    role_id: int | None = None,
    status: str | None = None,
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("user:view")),
):
    """用户分页列表。"""
    return await org_service.list_users(
        db, page, page_size, department_id, role_id, status, keyword
    )


@router.post("/users", response_model=UserOut)
async def create_user(
    req: UserCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("user:create")),
):
    """新增用户。"""
    return await org_service.create_user(db, req)


@router.put("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    req: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("user:update")),
):
    """编辑用户。"""
    return await org_service.update_user(db, user_id, req)


@router.post("/users/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    req: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("user:reset_pwd")),
):
    """重置密码。"""
    await org_service.reset_password(db, user_id, req.password)
    return {"code": 0, "message": "ok", "data": None}


@router.put("/users/{user_id}/status", response_model=UserOut)
async def update_status(
    user_id: int,
    req: UpdateStatusRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("user:status")),
):
    """启用/停用用户。"""
    return await org_service.update_status(db, user_id, req.status)


# ===== 角色 =====


@router.get("/roles", response_model=list[RoleOut])
async def list_roles(db: AsyncSession = Depends(get_db)):
    """角色列表。"""
    return await org_service.list_roles(db)


@router.post("/roles", response_model=RoleOut)
async def create_role(
    req: RoleCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("role:create")),
):
    """新增角色。"""
    return await org_service.create_role(db, req)


@router.put("/roles/{role_id}", response_model=RoleOut)
async def update_role(
    role_id: int,
    req: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("role:update")),
):
    """编辑角色。"""
    return await org_service.update_role(db, role_id, req)


@router.post("/roles/{role_id}/permissions")
async def assign_permissions(
    role_id: int,
    req: AssignPermissionRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("role:assign_perm")),
):
    """角色权限分配（覆盖式写入）。"""
    await org_service.assign_permissions(db, role_id, req)
    return {"code": 0, "message": "ok", "data": None}
