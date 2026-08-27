"""组织架构服务：部门、角色、用户与权限的查询与维护。"""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BizError
from app.core.security import hash_password
from app.models import (
    Department,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.schemas.org import (
    AssignPermissionRequest,
    DepartmentCreate,
    DepartmentOut,
    DepartmentTreeNode,
    DepartmentUpdate,
    RoleCreate,
    RoleOut,
    RoleUpdate,
    UserCreate,
    UserListResponse,
    UserOut,
    UserUpdate,
)


class OrgService:
    """组织架构业务逻辑。"""

    # ===== 权限查询 =====

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
        chain: list[int] = []
        current_id = department_id
        while current_id is not None:
            chain.append(current_id)
            dept = await db.get(Department, current_id)
            current_id = dept.parent_id if dept else None
        return chain

    # ===== 部门管理 =====

    async def get_department_tree(self, db: AsyncSession) -> list[DepartmentTreeNode]:
        """获取部门树形列表。"""
        result = await db.execute(select(Department).order_by(Department.sort_order))
        depts = list(result.scalars().all())
        node_map: dict[int, DepartmentTreeNode] = {
            d.id: DepartmentTreeNode.model_validate(d) for d in depts
        }
        roots: list[DepartmentTreeNode] = []
        for d in depts:
            node = node_map[d.id]
            if d.parent_id is not None and d.parent_id in node_map:
                node_map[d.parent_id].children.append(node)
            else:
                roots.append(node)
        return roots

    async def create_department(
        self, db: AsyncSession, req: DepartmentCreate
    ) -> DepartmentOut:
        """新增部门。"""
        dept = Department(**req.model_dump())
        db.add(dept)
        await db.commit()
        await db.refresh(dept)
        return DepartmentOut.model_validate(dept)

    async def update_department(
        self, db: AsyncSession, dept_id: int, req: DepartmentUpdate
    ) -> DepartmentOut:
        """编辑部门。"""
        dept = await db.get(Department, dept_id)
        if dept is None:
            raise BizError(404, 40401, "部门不存在")
        data = req.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(dept, key, value)
        await db.commit()
        await db.refresh(dept)
        return DepartmentOut.model_validate(dept)

    async def delete_department(self, db: AsyncSession, dept_id: int) -> None:
        """删除部门（需无子部门与成员）。"""
        dept = await db.get(Department, dept_id)
        if dept is None:
            raise BizError(404, 40401, "部门不存在")
        # 检查子部门
        child_count = (
            await db.execute(
                select(func.count()).select_from(Department).where(
                    Department.parent_id == dept_id
                )
            )
        ).scalar_one()
        if child_count > 0:
            raise BizError(400, 40001, "存在子部门，无法删除")
        # 检查成员
        member_count = (
            await db.execute(
                select(func.count()).select_from(User).where(
                    User.department_id == dept_id
                )
            )
        ).scalar_one()
        if member_count > 0:
            raise BizError(400, 40002, "部门下存在成员，无法删除")
        await db.delete(dept)
        await db.commit()

    # ===== 用户管理 =====

    async def list_users(
        self,
        db: AsyncSession,
        page: int = 1,
        page_size: int = 20,
        department_id: int | None = None,
        role_id: int | None = None,
        status: str | None = None,
        keyword: str | None = None,
    ) -> UserListResponse:
        """用户分页列表。"""
        query = select(User)
        count_query = select(func.count()).select_from(User)

        if department_id is not None:
            query = query.where(User.department_id == department_id)
            count_query = count_query.where(User.department_id == department_id)
        if status is not None:
            query = query.where(User.status == status)
            count_query = count_query.where(User.status == status)
        if keyword:
            query = query.where(
                User.username.ilike(f"%{keyword}%")
                | User.display_name.ilike(f"%{keyword}%")
            )
            count_query = count_query.where(
                User.username.ilike(f"%{keyword}%")
                | User.display_name.ilike(f"%{keyword}%")
            )
        if role_id is not None:
            query = query.join(UserRole, UserRole.user_id == User.id).where(
                UserRole.role_id == role_id
            )
            count_query = count_query.join(
                UserRole, UserRole.user_id == User.id
            ).where(UserRole.role_id == role_id)

        total = (await db.execute(count_query)).scalar_one()
        result = await db.execute(
            query.order_by(User.id).offset((page - 1) * page_size).limit(page_size)
        )
        users = list(result.scalars().all())
        items = [await self._to_user_out(db, u) for u in users]
        return UserListResponse(total=total, items=items)

    async def create_user(self, db: AsyncSession, req: UserCreate) -> UserOut:
        """新增用户。"""
        # 检查用户名唯一
        exists = (
            await db.execute(select(User.id).where(User.username == req.username))
        ).scalar_one_or_none()
        if exists is not None:
            raise BizError(400, 40003, "用户名已存在")

        user = User(
            username=req.username,
            display_name=req.display_name,
            password_hash=hash_password(req.password),
            department_id=req.department_id,
            status="active",
        )
        db.add(user)
        await db.flush()
        # 关联角色
        for role_id in req.role_ids:
            db.add(UserRole(user_id=user.id, role_id=role_id))
        await db.commit()
        await db.refresh(user)
        return await self._to_user_out(db, user)

    async def update_user(
        self, db: AsyncSession, user_id: int, req: UserUpdate
    ) -> UserOut:
        """编辑用户。"""
        user = await db.get(User, user_id)
        if user is None:
            raise BizError(404, 40401, "用户不存在")

        data = req.model_dump(exclude_unset=True)
        role_ids = data.pop("role_ids", None)
        for key, value in data.items():
            setattr(user, key, value)

        # 更新角色关联（覆盖式）
        if role_ids is not None:
            await db.execute(delete(UserRole).where(UserRole.user_id == user_id))
            for role_id in role_ids:
                db.add(UserRole(user_id=user_id, role_id=role_id))

        await db.commit()
        await db.refresh(user)
        return await self._to_user_out(db, user)

    async def reset_password(
        self, db: AsyncSession, user_id: int, new_password: str
    ) -> None:
        """重置用户密码。"""
        user = await db.get(User, user_id)
        if user is None:
            raise BizError(404, 40401, "用户不存在")
        user.password_hash = hash_password(new_password)
        await db.commit()

    async def update_status(
        self, db: AsyncSession, user_id: int, status: str
    ) -> UserOut:
        """启用/停用用户。"""
        if status not in ("active", "disabled"):
            raise BizError(400, 40004, "非法状态值")
        user = await db.get(User, user_id)
        if user is None:
            raise BizError(404, 40401, "用户不存在")
        user.status = status
        await db.commit()
        await db.refresh(user)
        return await self._to_user_out(db, user)

    # ===== 角色管理 =====

    async def list_roles(self, db: AsyncSession) -> list[RoleOut]:
        """角色列表。"""
        result = await db.execute(select(Role).order_by(Role.id))
        return [RoleOut.model_validate(r) for r in result.scalars().all()]

    async def create_role(self, db: AsyncSession, req: RoleCreate) -> RoleOut:
        """新增角色。"""
        exists = (
            await db.execute(select(Role.id).where(Role.role_code == req.role_code))
        ).scalar_one_or_none()
        if exists is not None:
            raise BizError(400, 40005, "角色编码已存在")
        role = Role(**req.model_dump())
        db.add(role)
        await db.commit()
        await db.refresh(role)
        return RoleOut.model_validate(role)

    async def update_role(
        self, db: AsyncSession, role_id: int, req: RoleUpdate
    ) -> RoleOut:
        """编辑角色。"""
        role = await db.get(Role, role_id)
        if role is None:
            raise BizError(404, 40401, "角色不存在")
        data = req.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(role, key, value)
        await db.commit()
        await db.refresh(role)
        return RoleOut.model_validate(role)

    async def assign_permissions(
        self, db: AsyncSession, role_id: int, req: AssignPermissionRequest
    ) -> None:
        """角色权限分配（覆盖式写入）。"""
        role = await db.get(Role, role_id)
        if role is None:
            raise BizError(404, 40401, "角色不存在")
        await db.execute(
            delete(RolePermission).where(RolePermission.role_id == role_id)
        )
        for perm in req.permissions:
            db.add(
                RolePermission(
                    role_id=role_id,
                    permission_code=perm["permission_code"],
                    permission_type=perm.get("permission_type", "operation"),
                )
            )
        await db.commit()

    # ===== 内部工具 =====

    async def _to_user_out(self, db: AsyncSession, user: User) -> UserOut:
        """将 User 模型转为 UserOut（附部门名、角色）。"""
        department_name = None
        if user.department_id is not None:
            dept = await db.get(Department, user.department_id)
            department_name = dept.name if dept else None

        role_ids = await self.get_role_ids(db, user.id)
        role_codes: list[str] = []
        for role_id in role_ids:
            role = await db.get(Role, role_id)
            if role:
                role_codes.append(role.role_code)

        return UserOut(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            department_id=user.department_id,
            department_name=department_name,
            status=user.status,
            role_ids=role_ids,
            role_codes=role_codes,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


org_service = OrgService()
