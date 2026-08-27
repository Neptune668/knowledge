"""认证服务：登录校验与用户信息组装。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models import Department, Role, User, UserRole
from app.schemas.auth import LoginRequest, LoginResponse, UserInfo


class AuthService:
    """认证业务逻辑。"""

    async def authenticate(
        self, db: AsyncSession, req: LoginRequest
    ) -> LoginResponse:
        """校验用户名密码并返回令牌与用户信息。"""
        result = await db.execute(select(User).where(User.username == req.username))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(req.password, user.password_hash):
            from app.core.exceptions import BizError

            raise BizError(401, 40101, "用户名或密码错误")
        if user.status != "active":
            from app.core.exceptions import BizError

            raise BizError(403, 40301, "用户已被停用")

        # 获取部门与角色
        department_name = None
        if user.department_id is not None:
            dept = await db.get(Department, user.department_id)
            department_name = dept.name if dept else None

        roles = await self._get_roles(db, user.id)
        permissions = await self._get_permissions(db, user.id)

        user_info = UserInfo(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            department_id=user.department_id,
            department_name=department_name,
            roles=roles,
        )

        from app.core.security import create_access_token

        return LoginResponse(
            access_token=create_access_token(user.id),
            user_info=user_info,
            permissions=permissions,
        )

    async def _get_roles(self, db: AsyncSession, user_id: int) -> list[str]:
        result = await db.execute(
            select(Role.role_code)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user_id)
        )
        return [row[0] for row in result.all()]

    async def _get_permissions(self, db: AsyncSession, user_id: int) -> list[str]:
        from app.models import RolePermission

        result = await db.execute(
            select(RolePermission.permission_code)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == user_id)
            .distinct()
        )
        return [row[0] for row in result.all()]


auth_service = AuthService()
