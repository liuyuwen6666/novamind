from typing import List
from pydantic import ConfigDict
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document as LCDocument
from langchain_core.retrievers import BaseRetriever
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableMap

from app.core.config import get_settings
from app.models.models import Document as DBDocument, File
from app.services.embedding_service import VolcEngineEmbeddings, EmbeddingService

settings = get_settings()

class SQLModelRetriever(BaseRetriever):
    """基于 SQLModel pgvector 向量数据库的自定义 Retriever，提供 Workspace 多租户隔离"""
    session: AsyncSession
    embeddings: VolcEngineEmbeddings
    workspace_id: str
    top_k: int = 4

    model_config = ConfigDict(arbitrary_types_allowed=True)

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[LCDocument]:
        # 1. 提取 Query Embedding
        query_vector = await self.embeddings.aembed_query(query)
        
        # 2. 查询最相似的已解析成功的切片
        stmt = (
            select(DBDocument)
            .join(File)
            .where(File.workspace_id == self.workspace_id)
            .where(File.status == "completed")
            .order_by(DBDocument.embedding.l2_distance(query_vector))
            .limit(self.top_k)
        )
        
        result = await self.session.exec(stmt)
        db_docs = result.all()
        
        # 3. 封装为 LangChain LCDocument 格式
        return [
            LCDocument(
                page_content=doc.content,
                metadata={"file_id": str(doc.file_id), "chunk_index": doc.chunk_index, **(doc.meta_info or {})}
            )
            for doc in db_docs
        ]

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> List[LCDocument]:
        raise NotImplementedError("Use async aget_relevant_documents (ainvoke) instead")


def format_docs(docs: List[LCDocument]) -> str:
    """整合检索到的切片文本"""
    return "\n\n".join([f"[文档片段]:\n{doc.page_content}" for doc in docs])


async def build_rag_chain(session: AsyncSession, workspace_id: str):
    """构建用于 LCEL 的企业级异步问答链"""
    # 1. 声明大模型 (对接 LongCat API 兼容 OpenAI 端点)
    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        openai_api_key=settings.LLM_API_KEY,
        openai_api_base=settings.LLM_BASE_URL,
        streaming=True,
        temperature=0.2,
    )
    
    # 2. 初始化检索器与 Embedding
    embedding_service = EmbeddingService()
    embeddings = VolcEngineEmbeddings(embedding_service)
    retriever = SQLModelRetriever(
        session=session,
        embeddings=embeddings,
        workspace_id=workspace_id,
        top_k=settings.RAG_TOP_K
    )
    
    # 3. RAG 知识库问答 System Prompt
    prompt = ChatPromptTemplate.from_template("""你是一个专业的企业知识库助手。请根据以下已知信息，简明扼要且专业地回答用户的问题。如果已知信息中没有提及，请直接回答"知识库中未找到相关内容"。

已知信息:
{context}

用户问题:
{question}
""")
    
    # 4. 用 LCEL 编排链
    rag_chain = (
        RunnableMap({
            "context": retriever | format_docs,
            "question": RunnablePassthrough()
        })
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain
