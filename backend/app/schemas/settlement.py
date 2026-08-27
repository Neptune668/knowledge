"""知识沉淀相关请求/响应模型。"""

from datetime import datetime

from pydantic import BaseModel, Field


class FaqOut(BaseModel):
    id: int
    question: str
    answer: str
    category: str | None = None
    related_unit_id: int | None = None
    source_type: str
    status: str
    hit_count: int
    reviewer_id: int | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FaqReviewRequest(BaseModel):
    action: str = Field(..., description="approve / reject")
    edited_answer: str | None = Field(None, description="编辑后的标准答案（approve 时可选）")


class KnowledgeGapOut(BaseModel):
    id: int
    question_pattern: str
    sample_questions_json: list = []
    ask_count: int
    last_asked_at: datetime | None = None
    status: str
    resolved_unit_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResolveGapRequest(BaseModel):
    """处理知识缺口：可直接关联已有单元，或创建新单元。"""
    resolved_unit_id: int | None = Field(None, description="关联已有知识单元 ID")
    create_new: bool = Field(False, description="是否创建新知识单元")
    title: str | None = Field(None, description="新建单元标题（create_new=true 时必填）")
    content: str | None = Field(None, description="新建单元正文")
    category: str | None = None


class UpdateGapStatusRequest(BaseModel):
    status: str = Field(..., description="unresolved / resolved / ignored")
