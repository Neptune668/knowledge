"""应用配置：基于 pydantic-settings 读取环境变量与 .env 文件。"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置项。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用
    app_name: str = "kami-backend"
    debug: bool = False
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 120
    algorithm: str = "HS256"

    # 数据库
    database_url: str = "postgresql+asyncpg://kami:kami@localhost:5432/kami"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # 向量化 API（暂用外部 API，OpenAI 调用方式）
    embedding_api_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 1024

    # Milvus（直接 url 访问，无需 token）
    milvus_url: str = ""
    milvus_collection: str = Field(
        default="kb_chunks", validation_alias="CHUNKS_COLLECTION"
    )

    # LLM API（OpenAI 兼容协议）
    llm_api_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    # 检索工作流
    recall_top_k: int = 8
    retrieve_min_score: float = 0.55
    max_retry: int = 2

    # 沉淀阈值
    faq_mine_threshold: int = 3
    faq_sim_threshold: float = 0.92
    gap_sim_threshold: float = 0.55


@lru_cache
def get_settings() -> Settings:
    """返回缓存的全局配置单例。"""
    return Settings()


settings = get_settings()
