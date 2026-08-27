"""组织架构相关请求/响应模型。"""

from datetime import datetime

from pydantic import BaseModel, Field


# ===== 部门 =====


class DepartmentBase(BaseModel):
    name: str = Field(..., description="部门名称")
    parent_id: int | None = Field(None, description="父部门 ID，根部门为 null")
    leader_id: int | None = Field(None, description="负责人用户 ID")
    sort_order: int = Field(0, description="排序值")


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: str | None = None
    parent_id: int | None = None
    leader_id: int | None = None
    sort_order: int | None = None


class DepartmentOut(DepartmentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DepartmentTreeNode(DepartmentOut):
    children: list["DepartmentTreeNode"] = []


# ===== 用户 =====


class UserBase(BaseModel):
    username: str = Field(..., description="用户名")
    display_name: str = Field(..., description="显示名")
    department_id: int | None = Field(None, description="所属部门 ID")
    role_ids: list[int] = Field(default_factory=list, description="角色 ID 列表")


class UserCreate(UserBase):
    password: str = Field(..., description="初始密码")


class UserUpdate(BaseModel):
    display_name: str | None = None
    department_id: int | None = None
    role_ids: list[int] | None = None


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    department_id: int | None
    department_name: str | None = None
    status: str
    role_ids: list[int] = []
    role_codes: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    total: int
    items: list[UserOut]


class ResetPasswordRequest(BaseModel):
    password: str = Field(..., description="新密码")


class UpdateStatusRequest(BaseModel):
    status: str = Field(..., description="目标状态：active / disabled")


# ===== 角色 =====


class RoleBase(BaseModel):
    role_name: str = Field(..., description="角色名称")
    role_code: str = Field(..., description="角色编码")
    description: str | None = None


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    role_name: str | None = None
    description: str | None = None


class RoleOut(RoleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssignPermissionRequest(BaseModel):
    permissions: list[dict] = Field(
        default_factory=list,
        description="权限列表，每项含 permission_code、permission_type",
    )
