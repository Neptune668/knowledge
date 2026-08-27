"""数据库初始化脚本：建表 + 三角色与权限码种子数据。

用法：
    python -m scripts.init_db
"""

import asyncio
import sys
from pathlib import Path

# 将项目根目录加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.database import Base, async_session_factory, engine
from app.models import Role, RolePermission  # noqa: F401 确保模型已注册
from app.models import Department, Faq, KnowledgeGap, KnowledgeUnit, QaAccessLog  # noqa
from app.models import UnitPermission, User, UserRole  # noqa


# 三角色定义
ROLES = [
    {"role_name": "系统管理员", "role_code": "admin", "description": "系统管理员"},
    {"role_name": "知识管理员", "role_code": "knowledge_admin", "description": "知识管理员"},
    {"role_name": "普通用户", "role_code": "user", "description": "普通用户/提问者"},
]

# 权限码清单
ALL_PERMISSIONS = [
    "user:create", "user:update", "user:reset_pwd", "user:status", "user:view",
    "role:create", "role:update", "role:assign_perm",
    "dept:create", "dept:update", "dept:delete",
    "knowledge:create", "knowledge:update", "knowledge:delete",
    "knowledge:view", "knowledge:import", "knowledge:perm_config",
    "ai:chat",
    "dashboard:view",
    "faq:review", "faq:view",
    "gap:view", "gap:resolve",
]

# 三角色初始权限映射
ROLE_PERMISSIONS = {
    "admin": ALL_PERMISSIONS,
    "knowledge_admin": [
        "knowledge:create", "knowledge:update", "knowledge:delete",
        "knowledge:view", "knowledge:import", "knowledge:perm_config",
        "ai:chat", "dashboard:view",
        "faq:review", "faq:view",
        "gap:view", "gap:resolve",
    ],
    "user": ["ai:chat"],
}


async def init_db() -> None:
    """建表并写入种子数据。"""
    # 建表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("数据表创建完成")

    # 写入三角色
    async with async_session_factory() as db:
        existing = (await db.execute(select(Role.id))).scalars().all()
        if existing:
            print("角色已存在，跳过种子数据")
            return

        role_map: dict[str, int] = {}
        for role_data in ROLES:
            role = Role(**role_data)
            db.add(role)
            await db.flush()
            role_map[role.role_code] = role.id

        # 写入权限
        for role_code, perms in ROLE_PERMISSIONS.items():
            role_id = role_map[role_code]
            for code in perms:
                db.add(
                    RolePermission(
                        role_id=role_id,
                        permission_code=code,
                        permission_type="operation",
                    )
                )

        await db.commit()
        print("三角色与权限码种子数据写入完成")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
