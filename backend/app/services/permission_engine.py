"""数据权限引擎：校验用户对知识单元集合的访问权限。

四类权限实体：global / department / role / user，满足任意一种（OR 逻辑）即放行。
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UnitPermission
from app.services.org_service import org_service


class PermissionEngine:
    """数据权限计算引擎。"""

    async def check_units(
        self, db: AsyncSession, user_id: int, unit_ids: list[int]
    ) -> tuple[list[int], list[int]]:
        """校验用户对指定知识单元集合的访问权限。

        返回 (authorized_unit_ids, unauthorized_unit_ids)。
        """
        if not unit_ids:
            return [], []

        # 1. 获取用户所属部门（含祖先链）与角色
        dept_id = await org_service.get_department_id(db, user_id)
        dept_chain = await org_service.get_department_chain_ids(db, dept_id)
        role_ids = await org_service.get_role_ids(db, user_id)

        # 2. 查询这些知识单元的全部权限记录
        result = await db.execute(
            select(UnitPermission).where(UnitPermission.unit_id.in_(unit_ids))
        )
        perms = result.scalars().all()

        # 3. OR 逻辑匹配
        authorized: set[int] = set()
        for p in perms:
            hit = (
                p.target_type == "global"
                or (p.target_type == "department" and p.target_id in dept_chain)
                or (p.target_type == "role" and p.target_id in role_ids)
                or (p.target_type == "user" and p.target_id == user_id)
            )
            if hit:
                authorized.add(p.unit_id)

        unauthorized = [uid for uid in unit_ids if uid not in authorized]
        return list(authorized), unauthorized


permission_engine = PermissionEngine()
