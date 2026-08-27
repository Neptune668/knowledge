"""数据看板相关响应模型。"""

from pydantic import BaseModel


class MetricsResponse(BaseModel):
    """指标卡片数据。"""
    total_visits: int          # 访问总次数
    unique_users: int          # 独立访问人数（UV）
    total_units: int           # 知识单元总数
    total_tokens: int          # Token 总量
    avg_response_time_ms: int  # 平均响应时间（毫秒）


class QuestionRankingItem(BaseModel):
    question: str
    ask_count: int


class UnitRankingItem(BaseModel):
    unit_id: int
    unit_title: str | None = None
    hit_count: int


class TokenTrendItem(BaseModel):
    date: str
    total_tokens: int
    avg_response_time_ms: int
