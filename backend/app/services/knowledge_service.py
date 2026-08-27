"""知识单元服务：CRUD、状态管理、数据权限配置。"""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizError
from app.models import KnowledgeUnit, UnitPermission
from app.schemas.knowledge import (
    ConfigPermissionsRequest,
    KnowledgeUnitCreate,
    KnowledgeUnitDetail,
    KnowledgeUnitListResponse,
    KnowledgeUnitOut,
    KnowledgeUnitUpdate,
    UnitPermissionOut,
)

VALID_TARGET_TYPES = {"global", "department", "role", "user"}
VALID_STATUS = {"draft", "published", "archived"}


class KnowledgeService:
    """知识单元业务逻辑。"""

    async def list_units(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        title: str | None = None,
        category: str | None = None,
        status: str | None = None,
    ) -> KnowledgeUnitListResponse:
        """分页查询知识单元。"""
        query = select(KnowledgeUnit)
        count_query = select(func.count()).select_from(KnowledgeUnit)

        if title:
            query = query.where(KnowledgeUnit.title.ilike(f"%{title}%"))
            count_query = count_query.where(KnowledgeUnit.title.ilike(f"%{title}%"))
        if category:
            query = query.where(KnowledgeUnit.category == category)
            count_query = count_query.where(KnowledgeUnit.category == category)
        if status:
            query = query.where(KnowledgeUnit.status == status)
            count_query = count_query.where(KnowledgeUnit.status == status)

        total = (await db.execute(count_query)).scalar_one()
        result = await db.execute(
            query.order_by(KnowledgeUnit.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = [KnowledgeUnitOut.model_validate(u) for u in result.scalars().all()]
        return KnowledgeUnitListResponse(total=total, items=items)

    async def get_unit(self, db: AsyncSession, unit_id: int) -> KnowledgeUnitDetail:
        """查询知识单元详情与已配置权限列表。"""
        unit = await db.get(KnowledgeUnit, unit_id)
        if unit is None:
            raise BizError(404, 40401, "知识单元不存在")
        perms = await self._list_permissions(db, unit_id)
        detail = KnowledgeUnitDetail.model_validate(unit)
        detail.permissions = perms
        return detail

    async def create_unit(
        self, db: AsyncSession, req: KnowledgeUnitCreate, creator_id: int | None = None
    ) -> KnowledgeUnitOut:
        """创建知识单元（不含导入，用于缺口一键建档等场景）。"""
        unit = KnowledgeUnit(
            unit_code=self._gen_unit_code(),
            title=req.title,
            content=req.content,
            summary=req.summary,
            category=req.category,
            source_file_name=req.source_file_name,
            file_type=req.file_type,
            file_size=req.file_size,
            status="draft",
            creator_id=creator_id,
        )
        db.add(unit)
        await db.commit()
        await db.refresh(unit)
        return KnowledgeUnitOut.model_validate(unit)

    async def update_unit(
        self, db: AsyncSession, unit_id: int, req: KnowledgeUnitUpdate
    ) -> KnowledgeUnitOut:
        """更新知识单元。"""
        unit = await db.get(KnowledgeUnit, unit_id)
        if unit is None:
            raise BizError(404, 40401, "知识单元不存在")
        data = req.model_dump(exclude_unset=True)
        if "status" in data and data["status"] not in VALID_STATUS:
            raise BizError(400, 40006, "非法状态值")
        for key, value in data.items():
            setattr(unit, key, value)
        await db.commit()
        await db.refresh(unit)
        return KnowledgeUnitOut.model_validate(unit)

    async def delete_units(self, db: AsyncSession, unit_ids: list[int]) -> None:
        """批量删除知识单元。"""
        if not unit_ids:
            return
        # 级联删除权限记录（外键 ondelete CASCADE）
        await db.execute(
            delete(KnowledgeUnit).where(KnowledgeUnit.id.in_(unit_ids))
        )
        await db.commit()

    async def config_permissions(
        self, db: AsyncSession, unit_id: int, req: ConfigPermissionsRequest
    ) -> list[UnitPermissionOut]:
        """批量配置知识单元数据权限（覆盖式写入）。"""
        unit = await db.get(KnowledgeUnit, unit_id)
        if unit is None:
            raise BizError(404, 40401, "知识单元不存在")

        # 校验 target_type
        for item in req.permissions:
            if item.target_type not in VALID_TARGET_TYPES:
                raise BizError(400, 40007, f"非法权限实体类型：{item.target_type}")
            if item.target_type == "global" and item.target_id is not None:
                raise BizError(400, 40008, "global 类型权限 target_id 必须为 null")
            if item.target_type != "global" and item.target_id is None:
                raise BizError(400, 40009, f"{item.target_type} 类型权限必须指定 target_id")

        # 覆盖式：先删后插
        await db.execute(
            delete(UnitPermission).where(UnitPermission.unit_id == unit_id)
        )
        for item in req.permissions:
            db.add(
                UnitPermission(
                    unit_id=unit_id,
                    target_type=item.target_type,
                    target_id=item.target_id,
                )
            )
        await db.commit()
        return await self._list_permissions(db, unit_id)

    async def _list_permissions(
        self, db: AsyncSession, unit_id: int
    ) -> list[UnitPermissionOut]:
        """查询知识单元已配置的权限列表。"""
        result = await db.execute(
            select(UnitPermission)
            .where(UnitPermission.unit_id == unit_id)
            .order_by(UnitPermission.id)
        )
        return [
            UnitPermissionOut.model_validate(p) for p in result.scalars().all()
        ]

    @staticmethod
    def _gen_unit_code() -> str:
        """生成知识单元唯一编码。"""
        return "KU-" + uuid.uuid4().hex[:12].upper()


knowledge_service = KnowledgeService()
