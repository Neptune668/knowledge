"""组织架构服务：部门、角色、用户与权限查询。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Role, RolePermission, User, UserRole


class OrgService:
    """组织架构业务逻辑。"""

    async def has_permission(
        self, db: AsyncSession, user_id: int, permission_code: str
    ) -> bool:
        """判断用户是否拥有指定权限码。"""
        result = await db.execute(
            select(RolePermission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(
                UserRole.user_id == user_id,
                RolePermission.permission_code == permission_code,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_department_id(self, db: AsyncSession, user_id: int) -> int | None:
        """获取用户所属部门 ID。"""
        user = await db.get(User, user_id)
        return user.department_id if user else None

    async def get_role_ids(self, db: AsyncSession, user_id: int) -> list[int]:
        """获取用户角色 ID 列表。"""
        result = await db.execute(
            select(UserRole.role_id).where(UserRole.user_id == user_id)
        )
        return [row[0] for row in result.all()]

    async def get_department_chain_ids(
        self, db: AsyncSession, department_id: int | None
    ) -> list[int]:
        """获取部门自身及所有祖先部门 ID 列表（部门继承）。"""
        from app.models import Department

        chain: list[int] = []
        current_id = department_id
        while current_id is not None:
            chain.append(current_id)
            dept = await db.get(Department, current_id)
            current_id = dept.parent_id if dept else None
        return chain


org_service = OrgService()
