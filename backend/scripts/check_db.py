"""数据库连接检查脚本（entrypoint 用于等待 PostgreSQL 就绪）。"""

import asyncio
import sys
from pathlib import Path

# 确保 app 包可被导入（无论以何种方式运行本脚本）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app.core.config import settings  # noqa: E402


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
