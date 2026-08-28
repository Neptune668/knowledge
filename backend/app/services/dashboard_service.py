"""数据看板服务：聚合问答日志，计算指标、排行榜与趋势。"""

from sqlalchemy import Integer, String, distinct, func, select
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

        用 PostgreSQL jsonb_array_elements 在数据库侧展开并聚合，
        通过 LATERAL 关联保证 FROM 子句作用域正确。
        """
        # 展开 JSONB 数组为行（LATERAL 关联主表）
        elem = func.jsonb_array_elements(QaAccessLog.authorized_unit_ids_json)
        unit_id_col = elem.column_valued("value").cast(Integer)

        result = await db.execute(
            select(unit_id_col.label("unit_id"), func.count().label("cnt"))
            .select_from(QaAccessLog)
            .where(QaAccessLog.authorized_unit_ids_json.isnot(None))
            .group_by(unit_id_col)
            .order_by(func.count().desc())
            .limit(top)
        )
        ranked = [(int(row[0]), int(row[1])) for row in result.all()]

        # 批量查询标题
        unit_ids = [uid for uid, _ in ranked]
        items: list[UnitRankingItem] = []
        if unit_ids:
            units = (
                await db.execute(
                    select(KnowledgeUnit.id, KnowledgeUnit.title).where(
                        KnowledgeUnit.id.in_(unit_ids)
                    )
                )
            ).all()
            title_map = {u[0]: u[1] for u in units}
            for unit_id, cnt in ranked:
                items.append(
                    UnitRankingItem(
                        unit_id=unit_id,
                        unit_title=title_map.get(unit_id),
                        hit_count=cnt,
                    )
                )
        return items

    async def get_token_trend(
        self, db: AsyncSession, days: int = 7, granularity: str = "day"
    ) -> list[TokenTrendItem]:
        """查询 Token 消耗与响应时间趋势（按日或按周）。"""
        if granularity == "week":
            # PostgreSQL 按周分组：ISO 年 + 周
            year_expr = func.extract("isoyear", QaAccessLog.created_at)
            week_expr = func.extract("week", QaAccessLog.created_at)
            group_expr = func.concat(year_expr, "-W", func.lpad(week_expr.cast(String), 2, "0"))
            order_expr = group_expr
            limit = max(days // 7, 4)  # 周维度时限制周数
        else:
            group_expr = func.date(QaAccessLog.created_at)
            order_expr = group_expr
            limit = days

        result = await db.execute(
            select(
                group_expr,
                func.coalesce(func.sum(QaAccessLog.total_tokens), 0),
                func.coalesce(func.avg(QaAccessLog.response_time_ms), 0),
            )
            .group_by(group_expr)
            .order_by(order_expr.desc())
            .limit(limit)
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
