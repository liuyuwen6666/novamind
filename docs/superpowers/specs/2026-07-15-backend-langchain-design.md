# 企业级 backend-langchain 设计规格书 (V1)

本设计文档旨在指导将 backend 重构为基于 LangChain (LCEL) 与 SQLModel 的企业级后端系统，整体系统被命名为 `backend-langchain`。

---

## 1. 架构目标
- **工程化分层**：基于 FastAPI 实现经典的 API Router、Service、Repository、Model、Schema 分层，保证系统解耦与可维护性。
- **自定义向量表**：舍弃 LangChain 默认生成的黑盒向量表，使用 SQLModel 直接定义包含外键与租户隔离的 `files` 和 `documents` 表，通过 `pgvector` 进行高效向量运算。
- **纯粹的 LCEL 问答流**：核心 RAG 链与 Agent 工具链采用 LangChain 表达式语言 (LCEL) 编写，保持逻辑的直观与高度工程化，原生支持 Token 流式输出。
- **工具注册中心 (Tool Registry)**：基于 Python @decorator 机制和规范化 Type hint/Docstring 开发高扩展性的工具系统。

---

## 2. 核心技术栈
- **语言框架**：Python 3.10+, FastAPI
- **ORM 与数据库**：SQLModel (集成 Pydantic v2 & SQLAlchemy 2.0), PostgreSQL + pgvector 向量扩展
- **AI 编排**：LangChain Core v0.2+, LangChain OpenAI
- **文档处理**：PyMuPDF (fitz) 用于 PDF 文本提取，LangChain RecursiveCharacterTextSplitter 用于切片。

---

## 3. 物理目录结构
```text
backend-langchain/
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/   # API 路由接口（chat, upload, files, settings）
│   │   │   └── router.py    # 路由汇总
│   │   └── deps.py          # 依赖注入（如 db session, 各种 service）
│   ├── core/
│   │   ├── config.py        # 环境变量与配置（pydantic-settings）
│   │   ├── exceptions.py    # 全局异常定义
│   │   └── logging.py       # 结构化日志配置
│   ├── db/
│   │   ├── session.py       # 异步数据库引擎与 Session 生成器
│   │   └── init_db.py       # 数据库模型初始化逻辑
│   ├── models/
│   │   └── models.py        # SQLModel 数据库表实体模型（File, Document）
│   ├── schemas/
│   │   └── schemas.py       # API 请求与响应的纯 Pydantic 模型
│   ├── services/
│   │   ├── file_service.py  # 文件解析与切片服务
│   │   └── langchain_service.py # LangChain LCEL 核心链组装与大模型服务
│   ├── tools/
│   │   ├── registry.py      # 工具注册中心（Tool Registry）
│   │   └── weather.py       # 天气 API 工具实现
│   ├── utils/
│   │   └── helpers.py       # 通用工具函数（如 md5 计算等）
│   └── main.py              # 应用程序入口与 Lifespan 管理
├── requirements.txt         # 依赖声明文件
└── Dockerfile               # 容器化配置文件
```

---

## 4. 数据库实体设计 (SQLModel)
在 `app/models/models.py` 中定义以下两个核心表实体：

```python
import uuid
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, Relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Text
from pgvector.sqlalchemy import Vector

EMBEDDING_DIMENSION = 1024  # 对应字节/火山 Embedding 模型维度

class File(SQLModel, table=True):
    """文件表：记录上传的 PDF 文件状态及其元数据"""
    __tablename__ = "files"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: str = Field(default="default_tenant", index=True)
    workspace_id: str = Field(default="default_workspace", index=True)
    file_name: str = Field(max_length=255)
    file_hash: str = Field(max_length=32, index=True)
    status: str = Field(default="pending", max_length=20)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # 级联删除：文件被删，其对应的切片向量自动级联清理
    documents: list["Document"] = Relationship(
        back_populates="file",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

class Document(SQLModel, table=True):
    """文档切片表：存储具体的文本内容及其 pgvector 向量"""
    __tablename__ = "documents"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    file_id: uuid.UUID = Field(foreign_key="files.id", index=True)
    chunk_index: int = Field()
    content: str = Field(sa_column=Column(Text, nullable=False))
    
    # pgvector 向量扩展定义
    embedding: list[float] = Field(
        sa_column=Column(Vector(EMBEDDING_DIMENSION), nullable=False)
    )
    
    # 元数据，如 pdf 中的页码等，使用 PostgreSQL 的 JSONB 格式
    meta_info: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    file: File = Relationship(back_populates="documents")
```

---

## 5. LangChain 核心扩展与 LCEL 链设计
### 5.1 自定义 Embedding (`VolcEngineEmbeddings`)
继承 LangChain 的 `Embeddings` 基类，接入底层的 `EmbeddingService`：
```python
from langchain_core.embeddings import Embeddings
from app.services.embedding_service import EmbeddingService

class VolcEngineEmbeddings(Embeddings):
    """火山引擎 Embedding 包装器，兼容 LangChain 标准"""
    def __init__(self, service: EmbeddingService):
        self.service = service

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.service.embed_texts(texts))

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self.service.embed_texts(texts)

    def embed_query(self, text: str) -> list[float]:
        import asyncio
        return asyncio.run(self.service.embed_query(text))

    async def aembed_query(self, text: str) -> list[float]:
        return await self.service.embed_query(text)
```

### 5.2 自定义多租户检索器 (`SQLModelRetriever`)
继承 `BaseRetriever`，实现在 `workspace_id` 物理隔离下的 L2 距离向量相似度搜索：
```python
from typing import List
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document as LCDocument
from langchain_core.retrievers import BaseRetriever
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.models import Document as DBDocument, File

class SQLModelRetriever(BaseRetriever):
    """基于 SQLModel 和 pgvector 的企业级多租户检索器"""
    session: AsyncSession
    embeddings: VolcEngineEmbeddings
    workspace_id: str
    top_k: int = 4

    class Config:
        arbitrary_types_allowed = True

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[LCDocument]:
        query_vector = await self.embeddings.aembed_query(query)
        stmt = (
            select(DBDocument)
            .join(File)
            .where(File.workspace_id == self.workspace_id)
            .where(File.status == "completed")
            .order_by(DBDocument.embedding.l2_distance(query_vector))
            .limit(self.top_k)
        )
        result = await self.session.execute(stmt)
        db_docs = result.scalars().all()
        return [
            LCDocument(
                page_content=doc.content,
                metadata={"file_id": str(doc.file_id), **(doc.meta_info or {})}
            )
            for doc in db_docs
        ]

    def _get_relevant_documents(self, query: str, **kwargs) -> List[LCDocument]:
        raise NotImplementedError("Use async aget_relevant_documents instead")
```

### 5.3 LCEL RAG 问答链编排
使用 LCEL 管道把 Prompt 模板、LLM、Retriever 组合在一起。由于 LongCat 支持标准 OpenAI 接口，我们使用 `ChatOpenAI` 配合自定义 Endpoint：
```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableMap
from app.core.config import get_settings

settings = get_settings()

def format_docs(docs: list[LCDocument]) -> str:
    return "\n\n".join([f"[文档片段]:\n{doc.page_content}" for doc in docs])

async def build_rag_chain(session: AsyncSession, workspace_id: str):
    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        openai_api_key=settings.LLM_API_KEY,
        openai_api_base=settings.LLM_BASE_URL,
        streaming=True,
        temperature=0.2,
    )
    embedding_service = EmbeddingService()
    embeddings = VolcEngineEmbeddings(embedding_service)
    retriever = SQLModelRetriever(
        session=session,
        embeddings=embeddings,
        workspace_id=workspace_id
    )
    prompt = ChatPromptTemplate.from_template("""你是一个专业的企业知识库助手。请根据以下已知信息，简明扼要且专业地回答用户的问题。如果已知信息中没有提及，请直接回答"知识库中未找到相关内容"。

已知信息:
{context}

用户问题:
{question}
""")
    return (
        RunnableMap({
            "context": retriever | format_docs,
            "question": RunnablePassthrough()
        })
        | prompt
        | llm
        | StrOutputParser()
    )
```

---

## 6. 工具注册中心设计 (Tool Registry)
定义 `ToolRegistry` 单例，管理全部函数式工具。支持一键导出为符合大模型 API 调用格式的 Schema，并在大模型触发 Tool Calls 时执行路由。

```python
import inspect
from typing import Callable, Dict, Any, List
from langchain_core.tools import BaseTool, tool

class ToolRegistry:
    """企业级工具注册与执行中心"""
    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register_tool(self, tool_func: Callable) -> BaseTool:
        if isinstance(tool_func, BaseTool):
            t = tool_func
        else:
            t = tool(tool_func)
        self._tools[t.name] = t
        return t

    def get_tool(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def get_all_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def get_schemas_for_llm(self) -> List[dict]:
        from langchain_core.utils.function_calling import convert_to_openai_tool
        return [convert_to_openai_tool(t) for t in self._tools.values()]

    async def aexecute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        t = self.get_tool(name)
        if not t:
            raise ValueError(f"Tool '{name}' is not registered.")
        if inspect.iscoroutinefunction(t._run):
            return await t.ainvoke(args)
        else:
            return t.invoke(args)

tool_registry = ToolRegistry()
```

---

## 7. 质量保证与错误处理
- **统一响应格式**：在异常处理器中统一包装返回 `{"code": int, "message": str, "data": Any}`，拦截 AI 抛出的内部 `LLMError` 或 `EmbeddingError`，防止向客户端暴露敏感连接信息。
- **类型提示强制**：全站代码严格采用 Type Hint 标注，开启 mypy 静态类型验证。
- **隔离级别校验**：在每一处数据库检索与更新中强制带有 `workspace_id` 与 `tenant_id`，杜绝横向越权问题。
