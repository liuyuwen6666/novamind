import httpx
import asyncio

from app.core.config import get_settings
from app.core.exceptions import EmbeddingError
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class EmbeddingService:
    """字节/火山 Embedding，可替换为 OpenAI / BGE / Jina"""

    def __init__(self) -> None:
        self.api_key = settings.EMBEDDING_API_KEY
        self.base_url = settings.EMBEDDING_BASE_URL
        self.model = settings.EMBEDDING_MODEL

    async def _embed_single_text(self, client: httpx.AsyncClient, text: str) -> list[float]:
        """向量化单个文本（适用于多模态/火山向量接口）"""
        if self.base_url.endswith("/embeddings/multimodal"):
            url = self.base_url
        elif self.base_url.endswith("/api/v3"):
            url = f"{self.base_url}/embeddings/multimodal"
        elif "/api/v3" in self.base_url:
            url = self.base_url.split("/api/v3")[0] + "/api/v3/embeddings/multimodal"
        else:
            url = f"{self.base_url}/embeddings/multimodal"
        
        payload = {
            "model": self.model,
            "input": [{"type": "text", "text": text}],
            "dimensions": settings.EMBEDDING_DIMENSION
        }
        
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
        )
        resp.raise_for_status()
        res_json = resp.json()
        data = res_json.get("data")
        if isinstance(data, dict):
            embedding = data.get("embedding")
            if embedding:
                return embedding
        elif isinstance(data, list) and len(data) > 0:
            if isinstance(data[0], dict):
                embedding = data[0].get("embedding")
                if embedding:
                    return embedding
        raise ValueError(f"Unexpected response format from multimodal embedding: {res_json}")

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """批量文本向量化"""
        if not texts:
            return []
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                # 判断是否是火山多模态模型 (如 doubao-embedding-vision...)
                is_multimodal = "vision" in self.model or "multimodal" in self.base_url
                
                if is_multimodal:
                    # 多模态向量化接口将 input 数组作为单一上下文合成一个向量，
                    # 故若需要批量获取多个文本各自的向量，需并发单独调用
                    tasks = [self._embed_single_text(client, text) for text in texts]
                    embeddings = await asyncio.gather(*tasks)
                    logger.info("Embedded %d texts in parallel via multimodal API", len(texts))
                    return list(embeddings)
                else:
                    # 标准 OpenAI 兼容 Embedding 接口（支持批量直接返回数组）
                    url = f"{self.base_url}/embeddings" if not self.base_url.endswith("/embeddings") else self.base_url
                    payload = {
                        "model": self.model,
                        "input": texts
                    }
                    resp = await client.post(
                        url,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=payload,
                    )
                    resp.raise_for_status()
                    res_json = resp.json()
                    data = res_json.get("data")
                    embeddings = [item["embedding"] for item in data]
                    logger.info("Embedded %d texts via standard API", len(texts))
                    return embeddings
        except Exception as e:
            logger.error("Embedding failed: %s", e)
            raise EmbeddingError(str(e)) from e

    async def embed_query(self, text: str) -> list[float]:
        results = await self.embed_texts([text])
        return results[0]
