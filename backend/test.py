import asyncio
from sqlalchemy import select
from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models import User, UserRole, Role

async def main():
    async with async_session_factory() as db:
        rid = (await db.execute(select(Role.id).where(Role.role_code=='admin'))).scalar_one()
        hash = hash_password('1234')
        print(hash)
        u = User(username='admin', display_name='系统管理员',
                 password_hash=hash, status='active')
        db.add(u); await db.flush()
        db.add(UserRole(user_id=u.id, role_id=rid))
        await db.commit()
        print('管理员创建成功')

asyncio.run(main())