import pytest
from app.services.embedding_service import EmbeddingService, VolcEngineEmbeddings

@pytest.mark.asyncio
async def test_volc_embeddings():
    # 1. 初始化底层的 Embedding 交互服务
    service = EmbeddingService()
    
    # 2. 包装为 LangChain 兼容的 Embeddings 类
    embeddings = VolcEngineEmbeddings(service)
    
    # 3. 校验 embed_query 向量生成
    query = "测试企业级 LangChain 检索"
    vector = await embeddings.aembed_query(query)
    
    assert isinstance(vector, list)
    assert len(vector) == 1024
    assert all(isinstance(val, float) for val in vector)
