"""知识沉淀定时任务：FAQ 挖掘与知识缺口聚合。"""

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.database import async_session_factory
from app.services.settlement_service import settlement_service


async def run_faq_mining() -> None:
    """定时挖掘高频问题生成候选 FAQ。"""
    async with async_session_factory() as db:
        count = await settlement_service.mine_faqs(db)
        print(f"[job] FAQ 挖掘完成，生成 {count} 条候选")


async def run_gap_mining() -> None:
    """定时识别知识缺口。"""
    async with async_session_factory() as db:
        count = await settlement_service.mine_gaps(db)
        print(f"[job] 知识缺口识别完成，生成 {count} 条缺口")


scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    """启动定时任务调度器（应用启动时调用）。"""
    # 每天凌晨 2 点挖掘 FAQ，凌晨 3 点识别知识缺口
    scheduler.add_job(
        run_faq_mining, "cron", hour=2, minute=0, id="faq_mining"
    )
    scheduler.add_job(
        run_gap_mining, "cron", hour=3, minute=0, id="gap_mining"
    )
    scheduler.start()
    print("[job] 定时任务调度器已启动")


def shutdown_scheduler() -> None:
    """停止调度器（应用关闭时调用）。"""
    scheduler.shutdown(wait=False)
