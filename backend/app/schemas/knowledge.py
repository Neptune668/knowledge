"""知识单元相关请求/响应模型。"""

from datetime import datetime

from pydantic import BaseModel, Field


# ===== 知识单元 =====


class KnowledgeUnitOut(BaseModel):
    id: int
    unit_code: str
    title: str
    content: str
    summary: str | None = None
    category: str | None = None
    source_file_name: str | None = None
    file_type: str | None = None
    file_size: int | None = None
    status: str
    creator_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeUnitDetail(KnowledgeUnitOut):
    permissions: list["UnitPermissionOut"] = []


class KnowledgeUnitListResponse(BaseModel):
    total: int
    items: list[KnowledgeUnitOut]


class KnowledgeUnitUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    summary: str | None = None
    category: str | None = None
    status: str | None = Field(None, description="draft / published / archived")


class KnowledgeUnitCreate(BaseModel):
    title: str = Field(..., description="标题")
    content: str = Field(..., description="正文内容")
    summary: str | None = None
    category: str | None = None
    source_file_name: str | None = None
    file_type: str | None = None
    file_size: int | None = None


class BatchDeleteRequest(BaseModel):
    unit_ids: list[int] = Field(..., description="待删除的知识单元 ID 列表")


# ===== 数据权限 =====


class UnitPermissionOut(BaseModel):
    id: int
    unit_id: int
    target_type: str
    target_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UnitPermissionItem(BaseModel):
    target_type: str = Field(..., description="global / department / role / user")
    target_id: int | None = Field(None, description="global 时为 null")


class ConfigPermissionsRequest(BaseModel):
    permissions: list[UnitPermissionItem] = Field(
        default_factory=list, description="权限实体列表"
    )
