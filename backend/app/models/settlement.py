"""知识沉淀模型：FAQ 与知识缺口。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Faq(Base):
    """FAQ 问答对表。"""

    __tablename__ = "faqs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    related_unit_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("knowledge_units.id"), nullable=True
    )
    source_type: Mapped[str] = mapped_column(String(16), default="manual", nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="pending_review", nullable=False
    )
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reviewer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class KnowledgeGap(Base):
    """知识缺口表。"""

    __tablename__ = "knowledge_gaps"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    question_pattern: Mapped[str] = mapped_column(String(255), nullable=False)
    sample_questions_json: Mapped[list | None] = mapped_column(
        JSONB, default=list, nullable=True
    )
    ask_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_asked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), default="unresolved", nullable=False)
    resolved_unit_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("knowledge_units.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
