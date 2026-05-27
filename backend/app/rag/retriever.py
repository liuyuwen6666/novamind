from __future__ import annotations

from app.core.logging import get_logger
from app.repositories.document_repository import DocumentRepository
from app.schemas.schemas import ChunkOut
from app.services.embedding_service import EmbeddingService

logger = get_logger(__name__)


class RAGRetriever:
    """RAG 检索器：将 query 向量化后检索最相关 chunk"""

    def __init__(self, doc_repo: DocumentRepository, embedding_svc: EmbeddingService) -> None:
        self.doc_repo = doc_repo
        self.embedding_svc = embedding_svc

    async def retrieve(self, query: str, top_k: int = 5, workspace_id: str | None = None) -> list[ChunkOut]:
        query_embedding = await self.embedding_svc.embed_query(query)
        results = await self.doc_repo.similarity_search(query_embedding, top_k=top_k, workspace_id=workspace_id)
        chunks = [
            ChunkOut(
                id=chunk.id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=score,
                file_name=chunk.file.file_name if (hasattr(chunk, "file") and chunk.file) else None
            )
            for chunk, score in results
        ]
        logger.info("RAG retrieved %d chunks for query: %.50s", len(chunks), query)
        return chunks


    def build_context(self, chunks: list[ChunkOut]) -> str:
        return "\n\n".join(f"【文档片段 {i+1}】(来源: {c.file_name if c.file_name else '未知'}):\n{c.content}" for i, c in enumerate(chunks))

