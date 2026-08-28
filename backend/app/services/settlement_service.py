"""知识沉淀服务：FAQ 挖掘、审核发布、知识缺口识别与建档。"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BizError
from app.models import Faq, KnowledgeGap, KnowledgeUnit, QaAccessLog
from app.schemas.settlement import (
    FaqOut,
    FaqReviewRequest,
    KnowledgeGapOut,
    ResolveGapRequest,
    UpdateGapStatusRequest,
)
from app.services.faq_cache_service import faq_cache_service


class SettlementService:
    """知识沉淀业务逻辑。"""

    # ===== FAQ 挖掘 =====

    async def mine_faqs(self, db: AsyncSession) -> int:
        """从问答日志挖掘高频问题，生成待审核 FAQ。

        语义去重在本阶段简化为「问题文本精确分组」，后续接入向量聚类。
        返回本次生成的 FAQ 数量。
        """
        result = await db.execute(
            select(QaAccessLog.question, func.count().label("cnt"))
            .group_by(QaAccessLog.question)
            .having(func.count() >= settings.faq_mine_threshold)
            .order_by(func.count().desc())
        )
        created = 0
        for question, cnt in result.all():
            # 跳过已存在相同问题的 FAQ
            exists = (
                await db.execute(
                    select(Faq.id).where(Faq.question == question)
                )
            ).scalar_one_or_none()
            if exists is not None:
                continue
            db.add(
                Faq(
                    question=question,
                    answer="",
                    source_type="auto_mined",
                    status="pending_review",
                    hit_count=cnt,
                )
            )
            created += 1
        await db.commit()
        return created

    async def list_recommendations(self, db: AsyncSession) -> list[FaqOut]:
        """查询待审核 FAQ 推荐列表。"""
        result = await db.execute(
            select(Faq)
            .where(Faq.status == "pending_review")
            .order_by(Faq.hit_count.desc())
        )
        return [FaqOut.model_validate(f) for f in result.scalars().all()]

    async def list_published(self, db: AsyncSession) -> list[FaqOut]:
        """查询已发布 FAQ 库。"""
        result = await db.execute(
            select(Faq).where(Faq.status == "published").order_by(Faq.id.desc())
        )
        return [FaqOut.model_validate(f) for f in result.scalars().all()]

    async def review_faq(
        self, db: AsyncSession, faq_id: int, req: FaqReviewRequest, reviewer_id: int
    ) -> FaqOut:
        """审核 FAQ（approve / reject）。"""
        faq = await db.get(Faq, faq_id)
        if faq is None:
            raise BizError(404, 40401, "FAQ 不存在")

        if req.action == "approve":
            if req.edited_answer:
                faq.answer = req.edited_answer
            if not faq.answer:
                raise BizError(400, 40010, "审核通过必须提供答案")
            faq.status = "published"
            faq.reviewer_id = reviewer_id
            faq.reviewed_at = datetime.now(timezone.utc)
            await db.commit()
            # 写入缓存
            await faq_cache_service.set_faq(faq.question, faq.answer)
        elif req.action == "reject":
            faq.status = "rejected"
            faq.reviewer_id = reviewer_id
            faq.reviewed_at = datetime.now(timezone.utc)
            await db.commit()
        else:
            raise BizError(400, 40011, "非法 action 值")

        await db.refresh(faq)
        return FaqOut.model_validate(faq)

    # ===== 知识缺口 =====

    async def mine_gaps(self, db: AsyncSession) -> int:
        """识别知识缺口。

        判据（满足任一）：
        1. 召回为空（无任何召回记录）
        2. 授权为空（召回但无权限/低置信度，等效于无可用知识支撑）
        返回本次生成的缺口数量。
        """
        # 查询无召回（recalled 为空数组）或无授权（authorized 为空数组）的提问
        result = await db.execute(
            select(QaAccessLog.question, func.count().label("cnt"))
            .where(
                (QaAccessLog.recalled_unit_ids_json == "[]")
                | (QaAccessLog.authorized_unit_ids_json == "[]")
            )
            .group_by(QaAccessLog.question)
            .order_by(func.count().desc())
        )
        created = 0
        for question, cnt in result.all():
            exists = (
                await db.execute(
                    select(KnowledgeGap.id).where(
                        KnowledgeGap.question_pattern == question
                    )
                )
            ).scalar_one_or_none()
            if exists is not None:
                continue
            db.add(
                KnowledgeGap(
                    question_pattern=question,
                    sample_questions_json=[question],
                    ask_count=cnt,
                    last_asked_at=datetime.now(timezone.utc),
                    status="unresolved",
                )
            )
            created += 1
        await db.commit()
        return created

    async def list_gaps(self, db: AsyncSession) -> list[KnowledgeGapOut]:
        """查询知识缺口列表。"""
        result = await db.execute(
            select(KnowledgeGap).order_by(KnowledgeGap.ask_count.desc())
        )
        return [KnowledgeGapOut.model_validate(g) for g in result.scalars().all()]

    async def resolve_gap(
        self, db: AsyncSession, gap_id: int, req: ResolveGapRequest
    ) -> KnowledgeGapOut:
        """处理知识缺口：关联已有单元或创建新单元。"""
        gap = await db.get(KnowledgeGap, gap_id)
        if gap is None:
            raise BizError(404, 40401, "知识缺口不存在")

        if req.create_new:
            if not req.title or not req.content:
                raise BizError(400, 40012, "新建知识单元需提供标题与内容")
            unit = KnowledgeUnit(
                unit_code=self._gen_unit_code(),
                title=req.title,
                content=req.content,
                category=req.category,
                status="draft",
            )
            db.add(unit)
            await db.flush()
            gap.resolved_unit_id = unit.id
        elif req.resolved_unit_id is not None:
            unit = await db.get(KnowledgeUnit, req.resolved_unit_id)
            if unit is None:
                raise BizError(404, 40401, "关联知识单元不存在")
            gap.resolved_unit_id = req.resolved_unit_id
        else:
            raise BizError(400, 40013, "需提供关联单元或选择创建新单元")

        gap.status = "resolved"
        await db.commit()
        await db.refresh(gap)
        return KnowledgeGapOut.model_validate(gap)

    async def update_gap_status(
        self, db: AsyncSession, gap_id: int, req: UpdateGapStatusRequest
    ) -> KnowledgeGapOut:
        """变更知识缺口状态。"""
        if req.status not in ("unresolved", "resolved", "ignored"):
            raise BizError(400, 40014, "非法状态值")
        gap = await db.get(KnowledgeGap, gap_id)
        if gap is None:
            raise BizError(404, 40401, "知识缺口不存在")
        gap.status = req.status
        await db.commit()
        await db.refresh(gap)
        return KnowledgeGapOut.model_validate(gap)

    @staticmethod
    def _gen_unit_code() -> str:
        import uuid

        return "KU-" + uuid.uuid4().hex[:12].upper()


settlement_service = SettlementService()
