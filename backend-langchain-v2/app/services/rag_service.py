import io
import uuid
import hashlib
import asyncio
from typing import List, Dict, Any, Optional

import fitz  # PyMuPDF
import httpx
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.pgvector import PGVector

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.exceptions import EmbeddingError, DuplicateFileError
from app.db.connection import get_db_connection

logger = get_logger(__name__)
settings = get_settings()


class VolcEngineEmbeddings(Embeddings):
    """
    自定义火山引擎多模态/大模型 Embedding 适配器，符合 LangChain 标准。
    针对火山多模态模型的批量生成需要并发请求的特性进行了特别优化。
    """
    def __init__(self) -> None:
        self.api_key = settings.EMBEDDING_API_KEY
        self.base_url = settings.EMBEDDING_BASE_URL
        self.model = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION

    async def _embed_single_text(self, client: httpx.AsyncClient, text: str) -> List[float]:
        # 构建火山多模态向量 API 路径
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
            "dimensions": self.dimension
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

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                is_multimodal = "vision" in self.model or "multimodal" in self.base_url
                if is_multimodal:
                    # 针对火山多模态接口的并发处理
                    tasks = [self._embed_single_text(client, text) for text in texts]
                    embeddings = await asyncio.gather(*tasks)
                    return list(embeddings)
                else:
                    # 标准 OpenAI 兼容接口批量调用
                    url = f"{self.base_url}/embeddings" if not self.base_url.endswith("/embeddings") else self.base_url
                    resp = await client.post(
                        url,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={"model": self.model, "input": texts},
                    )
                    resp.raise_for_status()
                    res_json = resp.json()
                    return [item["embedding"] for item in res_json.get("data", [])]
        except Exception as e:
            logger.error(f"Embedding aembed_documents failed: {e}")
            raise EmbeddingError(str(e)) from e

    async def aembed_query(self, text: str) -> List[float]:
        results = await self.aembed_documents([text])
        return results[0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # 在异步上下文，启动新的线程来运行同步阻塞
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.run(self.aembed_documents(texts))
        else:
            return asyncio.run(self.aembed_documents(texts))

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]


# 初始化标准 Embedding 实例
embeddings_model = VolcEngineEmbeddings()


def get_vector_store() -> PGVector:
    """初始化并获取全局 LangChain PGVector 向量引擎实例"""
    return PGVector(
        connection_string=settings.DATABASE_URL_SYNC,
        embedding_function=embeddings_model,
        collection_name="enterprise_knowledge",
    )


def parse_pdf(data: bytes) -> str:
    """解析 PDF 字节流，提取纯文本内容"""
    try:
        with fitz.open(stream=io.BytesIO(data), filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc)
    except Exception as e:
        logger.error(f"Failed to parse PDF bytes: {e}")
        raise ValueError(f"PDF 解析失败: {e}")


def split_text(text: str) -> List[str]:
    """使用 LangChain 文本切片器对文本进行规整切片"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        length_function=len,
    )
    return splitter.split_text(text)


async def add_document_to_vector_store(
    file_name: str,
    file_hash: str,
    file_size: int,
    content_bytes: bytes,
    workspace_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    处理文件逻辑：去重校验、提取文本、切片，写入 PGVector 向量数据库，并记录至 files 业务表
    """
    # 1. 查重
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT id FROM files WHERE file_hash = %s", (file_hash,))
            row = await cur.fetchone()
            if row:
                raise DuplicateFileError(file_hash)

    # 2. 解析与切片
    text = parse_pdf(content_bytes)
    chunks = split_text(text)
    if not chunks:
        raise ValueError("文档内容为空，解析失败")

    file_id = uuid.uuid4()
    
    # 3. 异步写入 PGVector 向量表 (LangChain 官方库底层会处理插入)
    vector_store = get_vector_store()
    
    # 组装 metadata 用于权限过滤和回溯
    metadatas = [
        {
            "file_id": str(file_id),
            "file_name": file_name,
            "workspace_id": workspace_id or "",
            "chunk_index": i
        }
        for i in range(len(chunks))
    ]
    
    logger.info(f"Adding {len(chunks)} chunks to PGVector store...")
    await vector_store.aadd_texts(chunks, metadatas=metadatas)

    # 4. 插入业务文件记录以便前端展示
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO files (id, workspace_id, file_name, file_hash, file_size, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                """,
                (str(file_id), workspace_id, file_name, file_hash, file_size, "done")
            )
            await conn.commit()

    logger.info(f"File {file_name} processed and indexed successfully. file_id={file_id}")
    return {
        "id": file_id,
        "file_name": file_name,
        "file_hash": file_hash,
        "status": "done",
        "created_at": None  # 后续从数据库读取或直接返回当前
    }


async def retrieve_kb(
    query: str,
    workspace_id: Optional[str] = None,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    通过 PGVector 检索与 Query 最相似的文档块列表
    """
    vector_store = get_vector_store()
    
    # 构建 metadata 过滤项 (以实现多工作空间/企业的数据隔离)
    filter_dict = {}
    if workspace_id:
        filter_dict["workspace_id"] = workspace_id
        
    logger.info(f"Retrieving from PGVector: query='{query}', filter={filter_dict}")
    
    # 执行带分数的向量检索
    results = await vector_store.asimilarity_search_with_score(
        query,
        k=top_k,
        filter=filter_dict if filter_dict else None
    )
    
    formatted_results = []
    for doc, score in results:
        # score 通常为 L2 距离，需要注意分值越高代表距离越远，还是余弦相似度
        formatted_results.append({
            "content": doc.page_content,
            "score": score,
            "file_id": doc.metadata.get("file_id"),
            "file_name": doc.metadata.get("file_name"),
            "chunk_index": doc.metadata.get("chunk_index")
        })
        
    return formatted_results
