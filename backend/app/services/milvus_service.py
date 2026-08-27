"""Milvus 服务：collection 设计与管理、向量写入与检索。

M7 负责设计并创建 collection，M8 在此基础上做检索。
"""

from pymilvus import DataType, MilvusClient

from app.core.config import settings


class MilvusService:
    """Milvus 向量库封装。"""

    def __init__(self) -> None:
        self._client: MilvusClient | None = None

    @property
    def client(self) -> MilvusClient:
        """惰性获取 Milvus 客户端（token 认证）。"""
        if self._client is None:
            if not settings.milvus_url:
                raise RuntimeError("MILVUS_URL 未配置")
            kwargs = {"uri": settings.milvus_url}
            if settings.milvus_token:
                kwargs["token"] = settings.milvus_token
            self._client = MilvusClient(**kwargs)
        return self._client

    def ensure_collection(self) -> None:
        """M7 核心：设计并创建 collection（不存在时）。"""
        collection_name = settings.milvus_collection
        if self.client.has_collection(collection_name):
            return

        schema = self.client.create_schema(
            auto_id=True, enable_dynamic_field=False
        )
        # 主键（自增）
        schema.add_field(
            field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True
        )
        # 切片 ID（对应 PostgreSQL knowledge_chunks.id）
        schema.add_field(field_name="chunk_id", datatype=DataType.INT64)
        # 知识单元 ID（M8 权限过滤关键字段）
        schema.add_field(field_name="unit_id", datatype=DataType.INT64)
        # 切片文本
        schema.add_field(
            field_name="content", datatype=DataType.VARCHAR, max_length=65535
        )
        # 稠密向量（维度由 embedding 模型决定）
        schema.add_field(
            field_name="dense_vector",
            datatype=DataType.FLOAT_VECTOR,
            dim=settings.embedding_dim,
        )

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="dense_vector",
            index_type="AUTOINDEX",
            metric_type="COSINE",
        )

        self.client.create_collection(
            collection_name=collection_name,
            schema=schema,
            index_params=index_params,
        )

    def insert(self, rows: list[dict]) -> list[int]:
        """批量插入向量，返回 Milvus 主键列表。

        :param rows: [{chunk_id, unit_id, content, dense_vector}]
        :return: Milvus 主键 ID 列表
        """
        if not rows:
            return []
        self.ensure_collection()
        result = self.client.insert(
            collection_name=settings.milvus_collection, data=rows
        )
        return list(result.get("ids", []))

    def delete_by_unit(self, unit_id: int) -> None:
        """按知识单元删除向量（单元更新/删除时清理）。"""
        if not self.client.has_collection(settings.milvus_collection):
            return
        self.client.delete(
            collection_name=settings.milvus_collection,
            filter=f"unit_id == {unit_id}",
        )

    def search(
        self, query_vector: list[float], top_k: int, filter_expr: str | None = None
    ) -> list[dict]:
        """向量检索（M8 使用）。

        :return: [{chunk_id, unit_id, content, score}]
        """
        self.ensure_collection()
        kwargs = {
            "collection_name": settings.milvus_collection,
            "data": [query_vector],
            "limit": top_k,
            "output_fields": ["chunk_id", "unit_id", "content"],
        }
        if filter_expr:
            kwargs["filter"] = filter_expr
        result = self.client.search(**kwargs)
        if not result:
            return []
        return [dict(hit.get("entity", {})) for hit in result[0]]


milvus_service = MilvusService()
