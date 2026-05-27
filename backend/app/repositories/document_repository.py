import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import DocumentChunk


class DocumentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def bulk_insert(self, chunks: list[DocumentChunk]) -> None:
        self.db.add_all(chunks)
        await self.db.commit()

    async def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        workspace_id: str | None = None,
        file_id: uuid.UUID | None = None,
    ) -> Sequence[tuple[DocumentChunk, float]]:
        """余弦相似度向量检索（使用 pgvector <=> 操作符）"""
        from sqlalchemy.orm import joinedload
        stmt = (
            select(DocumentChunk, DocumentChunk.embedding.cosine_distance(query_embedding).label("distance"))
            .options(joinedload(DocumentChunk.file))
            .order_by("distance")
            .limit(top_k)
        )
        if file_id:
            stmt = stmt.where(DocumentChunk.file_id == file_id)
        result = await self.db.execute(stmt)
        rows = result.all()
        return [(row[0], 1.0 - row[1]) for row in rows]  # distance → similarity

