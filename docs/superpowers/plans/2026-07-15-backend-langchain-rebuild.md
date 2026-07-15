# backend-langchain 全新重构实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在 `backend-langchain` 目录中从零构建一个基于 SQLModel 和 LangChain (LCEL) 表达的企业级 RAG 与 Tool Calling 后端系统。

**架构：**
1. 采用 FastAPI 提供 Web 接口与 SSE Token 流。
2. 使用 SQLModel + pgvector 管理数据库表（支持 workspace 级安全隔离）。
3. 继承 `BaseRetriever` 与 `Embeddings` 自定义实现 RAG 数据检索。
4. 使用单例注册器 `ToolRegistry` 管理与分发 LLM 工具回调。

**技术栈：** Python 3.10, FastAPI, SQLModel, pgvector, langchain-core, langchain-openai, PyMuPDF (fitz)

---

## 文件职责划分
我们将要创建的文件列表及其核心职责如下：
- `backend-langchain/requirements.txt`：项目包依赖声明。
- `backend-langchain/app/core/config.py`：环境变量加载与校验模型。
- `backend-langchain/app/models/models.py`：SQLModel 的 `files` 和 `documents` 表结构定义。
- `backend-langchain/app/db/session.py`：异步数据库 Engine 与 Session 生成器。
- `backend-langchain/app/services/embedding_service.py`：封装火山 Embedding 的自定义包装器。
- `backend-langchain/app/services/file_service.py`：PDF 文件提取、RecursiveCharacterTextSplitter 切片及向量化存储。
- `backend-langchain/app/services/langchain_service.py`：自定义 `SQLModelRetriever` 与基于 LCEL 的流式问答链。
- `backend-langchain/app/tools/registry.py`：函数式工具的统一注册、调用映射与 schema 生成中心。
- `backend-langchain/app/tools/weather.py`：V1 专属天气 API 工具函数。
- `backend-langchain/app/api/v1/endpoints/chat.py`：暴露聊天接口，支持 stream SSE 输出。
- `backend-langchain/app/api/v1/endpoints/upload.py`：暴露文件上传与去重处理接口。
- `backend-langchain/app/main.py`：应用入口，提供全局异常拦截与 CORS 中间件。

---

## 详细任务列表

### 任务 1：初始化项目结构与配置文件

**文件：**
- 创建：`backend-langchain/requirements.txt`
- 创建：`backend-langchain/app/core/config.py`
- 创建：`backend-langchain/app/core/logging.py`

- [ ] **步骤 1：编写配置测试**
  在 `backend-langchain/tests/test_config.py` 中编写对 Pydantic 设置加载的测试：
  ```python
  from app.core.config import get_settings

  def test_settings_load():
      settings = get_settings()
      assert settings.APP_NAME == "NovaMind-LangChain"
      assert settings.DATABASE_URL is not None
  ```

- [ ] **步骤 2：运行测试验证失败**
  运行：`pytest backend-langchain/tests/test_config.py`
  预期：失败，报错 "ModuleNotFoundError: No module named 'app'"

- [ ] **步骤 3：编写最小实现代码**
  1. 写入 `backend-langchain/requirements.txt`：
     ```text
     fastapi>=0.115.0
     uvicorn[standard]>=0.30.0
     pydantic-settings>=2.3.0
     sqlmodel>=0.0.22
     asyncpg>=0.29.0
     pgvector>=0.3.0
     PyMuPDF>=1.24.0
     httpx>=0.27.0
     python-multipart>=0.0.9
     alembic>=1.13.0
     langchain-core>=0.2.0
     langchain-openai>=0.1.0
     pytest>=8.0.0
     pytest-asyncio>=0.23.0
     ```
  2. 写入 `backend-langchain/app/core/config.py`：
     ```python
     from pydantic_settings import BaseSettings

     class Settings(BaseSettings):
         APP_NAME: str = "NovaMind-LangChain"
         DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/novamind"
         EMBEDDING_API_KEY: str = "test_key"
         EMBEDDING_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
         EMBEDDING_MODEL: str = "doubao-embedding"
         EMBEDDING_DIMENSION: int = 1024
         LLM_API_KEY: str = "test_key"
         LLM_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
         LLM_MODEL: str = "doubao-pro"

         class Config:
             env_file = ".env"

     _settings = None

     def get_settings() -> Settings:
         global _settings
         if _settings is None:
             _settings = Settings()
         return _settings
     ```

- [ ] **步骤 4：运行测试验证通过**
  运行：`pytest backend-langchain/tests/test_config.py`
  预期：通过

- [ ] **步骤 5：Commit**
  运行：
  ```bash
  git add backend-langchain/requirements.txt backend-langchain/app/core/config.py
  git commit -m "feat: init project configurations"
  ```

---

### 任务 2：定义 SQLModel 表与数据库 Session

**文件：**
- 创建：`backend-langchain/app/models/models.py`
- 创建：`backend-langchain/app/db/session.py`

- [ ] **步骤 1：编写数据库测试**
  在 `backend-langchain/tests/test_db.py` 中编写模型与会话的异步连接测试：
  ```python
  import pytest
  from sqlmodel import select
  from app.db.session import get_db
  from app.models.models import File

  @pytest.mark.asyncio
  async def test_db_session_and_model():
      async for session in get_db():
          stmt = select(File)
          result = await session.execute(stmt)
          assert result is not None
  ```

- [ ] **步骤 2：运行测试验证失败**
  运行：`pytest backend-langchain/tests/test_db.py`
  预期：报错缺少模块或表不存在

- [ ] **步骤 3：编写最小实现代码**
  1. 写入 `backend-langchain/app/models/models.py`，完整声明 `File` 和 `Document` 两个 SQLModel（集成 pgvector.sqlalchemy.Vector 结构）。
  2. 写入 `backend-langchain/app/db/session.py`：
     ```python
     from sqlmodel import SQLModel, create_engine
     from sqlmodel.ext.asyncio.session import AsyncSession
     from sqlalchemy.ext.asyncio import create_async_engine
     from sqlalchemy.orm import sessionmaker
     from app.core.config import get_settings

     settings = get_settings()
     engine = create_async_engine(settings.DATABASE_URL, echo=True)
     async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

     async def get_db():
         async with async_session() as session:
             yield session
     ```

- [ ] **步骤 4：运行测试验证通过**
  运行：`pytest backend-langchain/tests/test_db.py`
  预期：通过

- [ ] **步骤 5：Commit**
  运行：
  ```bash
  git add backend-langchain/app/models/models.py backend-langchain/app/db/session.py
  git commit -m "feat: implement database connection and sqlmodels"
  ```

---

### 任务 3：实现自定义 VolcEngineEmbeddings

**文件：**
- 创建：`backend-langchain/app/services/embedding_service.py`

- [ ] **步骤 1：编写 Embedding 测试**
  在 `backend-langchain/tests/test_embeddings.py` 中验证自定义 LangChain Embedding 的文本向量化结果：
  ```python
  import pytest
  from app.services.embedding_service import EmbeddingService, VolcEngineEmbeddings

  @pytest.mark.asyncio
  async def test_volc_embeddings():
      service = EmbeddingService()
      embeddings = VolcEngineEmbeddings(service)
      # mock embed_texts or real test
      result = await embeddings.aembed_query("测试文本")
      assert len(result) == 1024
  ```

- [ ] **步骤 2：运行测试验证失败**
  运行：`pytest backend-langchain/tests/test_embeddings.py`
  预期：失败

- [ ] **步骤 3：编写最小实现代码**
  在 `backend-langchain/app/services/embedding_service.py` 里：
  1. 使用 `httpx` 发送请求到火山的 `/embeddings` 或者是多模态接口。
  2. 声明继承自 `langchain_core.embeddings.Embeddings` 的 `VolcEngineEmbeddings` 包装类。

- [ ] **步骤 4：运行测试验证通过**
  运行：`pytest backend-langchain/tests/test_embeddings.py`
  预期：通过

- [ ] **步骤 5：Commit**
  运行：
  ```bash
  git add backend-langchain/app/services/embedding_service.py
  git commit -m "feat: implement volcengine embeddings for langchain"
  ```

---

### 任务 4：实现文件上传、解析与切片服务

**文件：**
- 创建：`backend-langchain/app/services/file_service.py`

- [ ] **步骤 1：编写切片与解析测试**
  在 `backend-langchain/tests/test_file_service.py` 中测试解析虚构 PDF 或 Text 内容的切分：
  ```python
  from app.services.file_service import FileService

  def test_text_splitting():
      service = FileService()
      chunks = service.split_text("这是一个很长的段落，为了测试切片的正确性。", chunk_size=10, chunk_overlap=2)
      assert len(chunks) > 0
  ```

- [ ] **步骤 2：运行测试验证失败**
  运行：`pytest backend-langchain/tests/test_file_service.py`
  预期：失败

- [ ] **步骤 3：编写最小实现代码**
  1. 在 `backend-langchain/app/services/file_service.py` 中，使用 `fitz` (PyMuPDF) 读取上传的字节，提取文本。
  2. 导入 LangChain 的 `RecursiveCharacterTextSplitter` 进行段落切割。
  3. 实现批量向量生成并保存至 `Document` 表，确保带有 MD5 重复检查。

- [ ] **步骤 4：运行测试验证通过**
  运行：`pytest backend-langchain/tests/test_file_service.py`
  预期：通过

- [ ] **步骤 5：Commit**
  运行：
  ```bash
  git add backend-langchain/app/services/file_service.py
  git commit -m "feat: implement file text extraction and slicing service"
  ```

---

### 任务 5：自定义 SQLModelRetriever 检索器

**文件：**
- 创建：`backend-langchain/app/services/langchain_service.py`

- [ ] **步骤 1：编写检索测试**
  在 `backend-langchain/tests/test_retriever.py` 中检验自定义检索器在不同 `workspace_id` 下的检索隔离：
  ```python
  import pytest
  from app.services.langchain_service import SQLModelRetriever

  @pytest.mark.asyncio
  async def test_retriever_isolation():
      # 检查传入不存在的 workspace_id 是否无内容返回
      pass
  ```

- [ ] **步骤 2：运行测试验证失败**
  运行：`pytest backend-langchain/tests/test_retriever.py`
  预期：失败

- [ ] **步骤 3：编写最小实现代码**
  在 `backend-langchain/app/services/langchain_service.py` 中：
  1. 编写自定义的 `SQLModelRetriever`，继承 `BaseRetriever`。
  2. 使用 pgvector 结合 SQLModel 执行 `l2_distance` 计算与 Workspace 过滤。

- [ ] **步骤 4：运行测试验证通过**
  运行：`pytest backend-langchain/tests/test_retriever.py`
  预期：通过

- [ ] **步骤 5：Commit**
  运行：
  ```bash
  git add backend-langchain/app/services/langchain_service.py
  git commit -m "feat: implement custom SQLModelRetriever for LCEL"
  ```

---

### 任务 6：实现 Tool Registry 系统

**文件：**
- 创建：`backend-langchain/app/tools/registry.py`
- 创建：`backend-langchain/app/tools/weather.py`

- [ ] **步骤 1：编写工具反射注册测试**
  在 `backend-langchain/tests/test_tool_registry.py` 验证工具的自动注册与反射调用：
  ```python
  from app.tools.registry import tool_registry

  def test_tool_registration():
      schemas = tool_registry.get_schemas_for_llm()
      assert any(s["function"]["name"] == "get_current_weather" for s in schemas)
  ```

- [ ] **步骤 2：运行测试验证失败**
  运行：`pytest backend-langchain/tests/test_tool_registry.py`
  预期：失败

- [ ] **步骤 3：编写最小实现代码**
  1. 编写 `backend-langchain/app/tools/registry.py` 实现 `ToolRegistry` 单例，使用 `convert_to_openai_tool` 导出接口。
  2. 编写 `backend-langchain/app/tools/weather.py` 定义具体的天气工具。

- [ ] **步骤 4：运行测试验证通过**
  运行：`pytest backend-langchain/tests/test_tool_registry.py`
  预期：通过

- [ ] **步骤 5：Commit**
  运行：
  ```bash
  git add backend-langchain/app/tools/registry.py backend-langchain/app/tools/weather.py
  git commit -m "feat: implement tool registry and weather tool"
  ```

---

### 任务 7：构建 Chat/Upload API 接口与主程序整合

**文件：**
- 创建：`backend-langchain/app/api/v1/endpoints/chat.py`
- 创建：`backend-langchain/app/api/v1/endpoints/upload.py`
- 创建：`backend-langchain/app/main.py`

- [ ] **步骤 1：编写集成 HTTP 测试**
  在 `backend-langchain/tests/test_endpoints.py` 中，使用 FastAPI TestClient 连调 `/health` 与对话接口：
  ```python
  from fastapi.testclient import TestClient
  from app.main import app

  client = TestClient(app)

  def test_health():
      response = client.get("/health")
      assert response.status_code == 200
  ```

- [ ] **步骤 2：运行测试验证失败**
  运行：`pytest backend-langchain/tests/test_endpoints.py`
  预期：失败

- [ ] **步骤 3：编写最小实现代码**
  1. 编写 `chat.py` 路由，调用 LCEL 链并返回 SSE。
  2. 编写 `upload.py` 路由实现文件的暂存解析入库。
  3. 组装 `main.py` 并整合全局 CORS 与异常代理。

- [ ] **步骤 4：运行测试验证通过**
  运行：`pytest backend-langchain/tests/test_endpoints.py`
  预期：通过

- [ ] **步骤 5：Commit**
  运行：
  ```bash
  git add backend-langchain/app/api/backend-langchain/app/main.py
  git commit -m "feat: finalize endpoints and integration"
  ```

---

## 验证计划

### 自动化集成测试
在终端中执行测试目录下的所有用例验证接口健康：
```bash
pytest backend-langchain/tests -v
```

### 手动验证
1. 启动本地 Postgres pgvector 容器（确保对应 schema 存在且开启 vector 扩展）。
2. 在新项目根目录下通过 Uvicorn 启动：
   ```bash
   cd backend-langchain && uvicorn app.main:app --reload --port 8000
   ```
3. 上传一份 PDF 测试文件，验证切分后 `documents` 表中产生了 1024 维的向量特征。
4. 调用对话 API 接口验证流式回答输出。
