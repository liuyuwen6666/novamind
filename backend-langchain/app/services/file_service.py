import io
import hashlib
from typing import List
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document as LCDocument

from app.core.config import get_settings
from app.core.exceptions import DuplicateFileError
from app.core.logging import get_logger
from app.models.models import File, Document
from app.services.embedding_service import VolcEngineEmbeddings

logger = get_logger(__name__)

class FileService:
    """企业级文件管理与 PDF 切片服务"""

    def parse_pdf(self, file_content: bytes) -> str:
        """PDF 二进制流解析为纯文本"""
        with fitz.open(stream=io.BytesIO(file_content), filetype="pdf") as doc:
            return "\n".join(page.get_text() for page in doc)

    def split_text(self, text: str, chunk_size: int = 500, chunk_overlap: int = 100) -> List[LCDocument]:
        """使用 LangChain 递归文本分割器进行分段切片"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "，", " ", ""]
        )
        return splitter.create_documents([text])

    async def save_file_chunks(
        self,
        db: AsyncSession,
        file_name: str,
        file_content: bytes,
        embeddings_wrapper: VolcEngineEmbeddings,
        workspace_id: str = "default_workspace",
        tenant_id: str = "default_tenant"
    ) -> File:
        """解析文件，生成切片及向量，保存至 PostgreSQL 数据库"""
        file_hash = hashlib.md5(file_content).hexdigest()

        # 1. 查找是否存在已上传成功的相同文件
        stmt = select(File).where(File.file_hash == file_hash).where(File.workspace_id == workspace_id)
        result = await db.exec(stmt)
        existing_file = result.first()
        
        if existing_file:
            if existing_file.status == "completed":
                raise DuplicateFileError(file_hash)
            else:
                # 之前上传失败的记录，先删除再重新处理
                await db.delete(existing_file)
                await db.commit()

        # 2. 插入初始化 File 记录
        db_file = File(
            file_name=file_name,
            file_hash=file_hash,
            status="processing",
            workspace_id=workspace_id,
            tenant_id=tenant_id
        )
        db.add(db_file)
        await db.commit()
        await db.refresh(db_file)

        try:
            # 3. 解析文本内容
            raw_text = self.parse_pdf(file_content)

            # 4. 滑动切片
            settings = get_settings()
            lc_docs = self.split_text(
                raw_text,
                chunk_size=settings.CHUNK_SIZE,
                chunk_overlap=settings.CHUNK_OVERLAP
            )

            if not lc_docs:
                # 如果是空文件
                db_file.status = "completed"
                await db.commit()
                return db_file

            # 5. 并发批量调用 VolcEngine 向量化接口
            texts = [doc.page_content for doc in lc_docs]
            embeddings = await embeddings_wrapper.aembed_documents(texts)

            # 6. 构造 Document 数据集写入数据库
            db_docs = []
            for i, (doc, vector) in enumerate(zip(lc_docs, embeddings)):
                db_doc = Document(
                    file_id=db_file.id,
                    chunk_index=i,
                    content=doc.page_content,
                    embedding=vector,
                    meta_info={"chunk_index": i, "source": file_name}
                )
                db_docs.append(db_doc)

            db.add_all(db_docs)
            db_file.status = "completed"
            await db.commit()
            await db.refresh(db_file)
            logger.info("Successfully processed and stored file: %s (hash=%s, chunks=%d)", file_name, file_hash, len(db_docs))

        except Exception as e:
            # 标记失败并报错
            db_file.status = "failed"
            await db.commit()
            logger.error("Failed to parse/process file %s: %s", file_name, e)
            raise e

        return db_file
