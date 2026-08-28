"""数据库连接检查脚本（entrypoint 用于等待 PostgreSQL 就绪）。"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


async def check() -> None:
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        print("PostgreSQL 连接成功")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check())
