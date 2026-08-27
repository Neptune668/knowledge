"""数据看板服务：聚合问答日志，计算指标、排行榜与趋势。"""

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeUnit, QaAccessLog
from app.schemas.dashboard import (
    MetricsResponse,
    QuestionRankingItem,
    TokenTrendItem,
    UnitRankingItem,
)


class DashboardService:
    """看板统计逻辑。"""

    async def get_metrics(self, db: AsyncSession) -> MetricsResponse:
        """查询访问总次数、独立用户数、知识单元数、Token 总量与平均耗时。"""
        total_visits = (
            await db.execute(select(func.count()).select_from(QaAccessLog))
        ).scalar_one()

        unique_users = (
            await db.execute(
                select(func.count(distinct(QaAccessLog.user_id))).where(
                    QaAccessLog.user_id.isnot(None)
                )
            )
        ).scalar_one()

        total_units = (
            await db.execute(select(func.count()).select_from(KnowledgeUnit))
        ).scalar_one()

        token_stats = (
            await db.execute(
                select(
                    func.coalesce(func.sum(QaAccessLog.total_tokens), 0),
                    func.coalesce(func.avg(QaAccessLog.response_time_ms), 0),
                )
            )
        ).one()
        total_tokens = int(token_stats[0])
        avg_response_time_ms = int(token_stats[1])

        return MetricsResponse(
            total_visits=total_visits,
            unique_users=unique_users,
            total_units=total_units,
            total_tokens=total_tokens,
            avg_response_time_ms=avg_response_time_ms,
        )

    async def get_question_rankings(
        self, db: AsyncSession, top: int = 10
    ) -> list[QuestionRankingItem]:
        """查询常见问题 TOP 榜。"""
        result = await db.execute(
            select(QaAccessLog.question, func.count().label("cnt"))
            .group_by(QaAccessLog.question)
            .order_by(func.count().desc())
            .limit(top)
        )
        return [
            QuestionRankingItem(question=row[0], ask_count=row[1])
            for row in result.all()
        ]

    async def get_unit_rankings(
        self, db: AsyncSession, top: int = 10
    ) -> list[UnitRankingItem]:
        """查询最常访问知识单元 TOP 榜。

        基于日志中 authorized_unit_ids_json 展开统计。
        """
        # 拉取所有日志的授权单元 ID 列表，在内存中聚合（数据量大时可改 SQL）
        result = await db.execute(
            select(QaAccessLog.authorized_unit_ids_json)
        )
        counter: dict[int, int] = {}
        for (ids_json,) in result.all():
            for uid in ids_json or []:
                counter[uid] = counter.get(uid, 0) + 1

        sorted_ids = sorted(counter.items(), key=lambda x: x[1], reverse=True)[:top]

        # 查询标题
        items: list[UnitRankingItem] = []
        for unit_id, cnt in sorted_ids:
            unit = await db.get(KnowledgeUnit, unit_id)
            items.append(
                UnitRankingItem(
                    unit_id=unit_id,
                    unit_title=unit.title if unit else None,
                    hit_count=cnt,
                )
            )
        return items

    async def get_token_trend(
        self, db: AsyncSession, days: int = 7
    ) -> list[TokenTrendItem]:
        """查询 Token 消耗与响应时间趋势（按日）。"""
        # PostgreSQL 按日期分组
        date_expr = func.date(QaAccessLog.created_at)
        result = await db.execute(
            select(
                date_expr,
                func.coalesce(func.sum(QaAccessLog.total_tokens), 0),
                func.coalesce(func.avg(QaAccessLog.response_time_ms), 0),
            )
            .group_by(date_expr)
            .order_by(date_expr.desc())
            .limit(days)
        )
        items = [
            TokenTrendItem(
                date=str(row[0]),
                total_tokens=int(row[1]),
                avg_response_time_ms=int(row[2]),
            )
            for row in result.all()
        ]
        # 升序返回，便于前端画趋势图
        items.reverse()
        return items


dashboard_service = DashboardService()
