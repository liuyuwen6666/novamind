import pytest
import uuid
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.db.session import get_db, engine
from app.models.models import File, Document
from sqlmodel import SQLModel

@pytest.mark.asyncio
async def test_db_session_and_model():
    # 1. 尝试初始化数据库结构 (在内存或测试库中建表)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # 2. 从 Session 生成器获取 session
    session_generator = get_db()
    session = await anext(session_generator)
    try:
        assert isinstance(session, AsyncSession)

        # 3. 往 File 表插入测试记录
        test_file = File(
            file_name="test_doc.pdf",
            file_hash="d41d8cd98f00b204e9800998ecf8427e",
            status="completed",
            workspace_id="test_workspace",
            tenant_id="test_tenant"
        )
        session.add(test_file)
        await session.commit()
        await session.refresh(test_file)
        
        assert test_file.id is not None
        
        # 4. 往 Document 插入关联记录
        # 默认 1024 维的 mock vector
        mock_vector = [0.1] * 1024
        test_doc = Document(
            file_id=test_file.id,
            chunk_index=0,
            content="这是测试切片文本内容",
            embedding=mock_vector,
            meta_info={"page": 1}
        )
        session.add(test_doc)
        await session.commit()
        await session.refresh(test_doc)
        
        assert test_doc.id is not None
        
        # 5. 查询验证外键关联与级联删除
        stmt = select(Document).where(Document.file_id == test_file.id)
        result = await session.execute(stmt)
        docs = result.scalars().all()
        assert len(docs) == 1
        assert docs[0].content == "这是测试切片文本内容"
        
        # 删除 File 并 commit
        await session.delete(test_file)
        await session.commit()
        
        # 验证关联的 Document 已被级联清理
        result = await session.execute(stmt)
        docs = result.scalars().all()
        assert len(docs) == 0

    finally:
        await session.close()
        # 清理表
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
