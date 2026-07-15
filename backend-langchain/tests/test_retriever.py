import pytest
import uuid
from sqlmodel import select, SQLModel
from app.db.session import engine, get_db
from app.models.models import File, Document
from app.services.embedding_service import VolcEngineEmbeddings
from app.services.langchain_service import SQLModelRetriever

class MockEmbeddings(VolcEngineEmbeddings):
    """Mock 向量生成器，固定输出特定向量"""
    def __init__(self):
        pass
    async def aembed_query(self, text: str):
        return [0.1] * 1024
    async def aembed_documents(self, texts: list[str]):
        return [[0.1] * 1024 for _ in texts]

@pytest.mark.asyncio
async def test_sqlmodel_retriever():
    # 1. 建表
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    session_generator = get_db()
    session = await anext(session_generator)
    try:
        # 2. 插入 workspace_A 的文件和切片 (距离近)
        file_a = File(
            file_name="doc_a.pdf",
            file_hash="hash_a",
            status="completed",
            workspace_id="workspace_A"
        )
        session.add(file_a)
        await session.commit()
        await session.refresh(file_a)
        
        doc_a1 = Document(
            file_id=file_a.id,
            chunk_index=0,
            content="这是 workspace_A 的最近切片",
            embedding=[0.1] * 1024, # 距离为 0
        )
        doc_a2 = Document(
            file_id=file_a.id,
            chunk_index=1,
            content="这是 workspace_A 的较远切片",
            embedding=[0.5] * 1024, # 距离较远
        )
        session.add_all([doc_a1, doc_a2])
        
        # 3. 插入 workspace_B 的文件和切片 (距离为 0，但 workspace 不同)
        file_b = File(
            file_name="doc_b.pdf",
            file_hash="hash_b",
            status="completed",
            workspace_id="workspace_B"
        )
        session.add(file_b)
        await session.commit()
        await session.refresh(file_b)
        
        doc_b = Document(
            file_id=file_b.id,
            chunk_index=0,
            content="这是 workspace_B 的切片",
            embedding=[0.1] * 1024,
        )
        session.add(doc_b)
        await session.commit()

        # 4. 实例化检索器进行查询 (指定 workspace_A)
        retriever = SQLModelRetriever(
            session=session,
            embeddings=MockEmbeddings(),
            workspace_id="workspace_A",
            top_k=2
        )
        
        results = await retriever.ainvoke("任意查询")
        
        # 5. 断言验证隔离和 L2 排序
        # 结果应只包含 workspace_A 的内容，且 doc_a1 应该因为距离更近排在第一位
        assert len(results) == 2
        assert results[0].page_content == "这是 workspace_A 的最近切片"
        assert results[1].page_content == "这是 workspace_A 的较远切片"
        assert all(res.metadata["file_id"] == str(file_a.id) for res in results)
        
    finally:
        await session.close()
        # 清理表
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
        # 显式释放引擎连接池以避开 Windows 异步 Proactor 循环已关闭的 AttributeError
        await engine.dispose()
