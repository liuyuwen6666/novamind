# LangChain 1.2 企业级 Agent 渐进式实战开发指南

本项目旨在指导如何将原 `backend` 的简单 RAG 与手工工具调用逻辑，升级重构为基于 **LangChain 1.2** 与 **LangGraph** 的企业级智能体平台。

## 🚀 项目目录与骨架说明

```text
backend-langchain-v2/
├── app/
│   ├── api/                  # API 路由层 (FastAPI Endpoints)
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── chat.py   # 支持 Streaming 流式的对话 API 
│   │   │   │   ├── files.py  # 知识库文档上传与向量化 API
│   │   │   │   └── sessions.py # 统一会话管理 API (直接对接 LangGraph Saver)
│   ├── core/                 # 核心配置与日志
│   │   ├── config.py         # Pydantic-settings 环境变量配置
│   │   └── exceptions.py     # 全局异常捕获
│   ├── db/                   # 数据库与向量库适配器
│   │   └── connection.py     # Postgres / pgvector 连接池
│   ├── services/             # 核心服务逻辑 (LangChain 封装)
│   │   ├── rag_service.py    # PGVector 的文档切片与检索服务
│   │   └── agent_service.py  # LangChain Agent / LangGraph 编译与运行服务
│   ├── tools/                # 自定义智能体工具库
│   │   ├── registry.py       # 工具全局注册管理
│   │   ├── weather.py        # 天气查询工具 (@tool 规范)
│   │   └── geocode.py        # 物理地址定位工具 (@tool 规范)
│   └── main.py               # FastAPI 服务启动入口
├── .env.example              # 环境变量配置模板
└── requirements.txt          # Python 依赖清单
```

---

## 🛠️ 环境准备与安装

1. 激活已配置的 conda 虚拟环境：
   ```bash
   conda activate langchain1.2
   ```
2. 安装项目依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 本地开发运行：
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

---

## 📖 渐进式开发三部曲

为了帮助您从 LangChain 快速过渡到 LangGraph，整个开发分为以下三个关键阶段：

### 阶段 1：LCEL RAG 构建 (夯实 LangChain 1.2 检索基底)
*   **开发目标**：将原 backend 中手写的复杂 SQL 检索和 Prompt 手工拼接，替换为 LangChain 1.2 官方标准的 LCEL (LangChain Expression Language) Chain 和 `PGVector`。
*   **实现步骤**：
    1.  **向量库迁移**：在 `app/services/rag_service.py` 中，使用 `langchain_community.vectorstores.pgvector.PGVector` 构建向量引擎：
        ```python
        from langchain_community.vectorstores.pgvector import PGVector
        
        # 初始化 PGVector 向量引擎
        vector_store = PGVector(
            connection_string=settings.DATABASE_URL,
            embedding_function=my_embeddings_model,
            collection_name="enterprise_kb",
        )
        ```
    2.  **LCEL Chain 构建**：在 `app/services/agent_service.py` 中，使用 LCEL 组装 RAG 检索链：
        ```python
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.runnables import RunnablePassthrough
        
        rag_chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | qa_prompt
            | llm
            | StrOutputParser()
        )
        ```

### 阶段 2：Tool-Calling Agent 落地 (掌握 Agent 与工具路由)
*   **开发目标**：使用 LangChain 标准的工具定义，让模型（LongCat-2.0）自主识别并路由工具调用（如天气工具、定位工具、本地知识库 RAG 工具）。
*   **实现步骤**：
    1.  **工具标准定义**：在 `app/tools/weather.py` 中，使用 `@tool` 重新装饰工具：
        ```python
        from langchain_core.tools import tool
        
        @tool
        def query_weather(city: str) -> str:
            """查询指定城市的实时天气数据。"""
            # 执行原有天气查询业务逻辑...
            return f"{city}天气晴朗，气温25度。"
        ```
    2.  **构建 AgentExecutor**：在 `app/services/agent_service.py` 中，利用 `create_tool_calling_agent` 生成路由智能体：
        ```python
        from langchain.agents import AgentExecutor, create_tool_calling_agent
        
        tools = [query_weather, query_geocode, kb_search_tool]
        agent = create_tool_calling_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
        ```

### 阶段 3：LangGraph 状态机与 Postgres 持久化 (企业级 Agent 终极形态)
*   **开发目标**：全面拥抱 LangGraph 状态图，替换原有的 `AgentExecutor`；将对话的短时记忆和长时记忆完全托管在 PostgreSQL 中，实现不需要手工建表的企业级会话持久化。
*   **实现步骤**：
    1.  **定义图状态**：
        ```python
        from typing import Annotated
        from typing_extensions import TypedDict
        from langgraph.graph.message import add_messages
        
        class AgentState(TypedDict):
            messages: Annotated[list, add_messages]
            documents: list[str]  # 暂存 RAG 检索结果
        ```
    2.  **定义图节点与构建状态图**：在 `app/services/agent_service.py` 中定义 Graph 节点并编译：
        ```python
        from langgraph.graph import StateGraph, START, END
        from langgraph.prebuilt import ToolNode
        
        workflow = StateGraph(AgentState)
        
        # 注册节点
        workflow.add_node("agent", call_model_node)
        workflow.add_node("tools", ToolNode(tools))
        workflow.add_node("retrieve", retrieve_kb_node)
        
        # 构建控制流边
        workflow.add_edge(START, "retrieve")
        workflow.add_edge("retrieve", "agent")
        workflow.add_conditional_edges("agent", should_continue_edge)
        workflow.add_edge("tools", "agent")
        
        # 挂载 PostgreSQL 状态保存器
        from langgraph.checkpoint.postgres import PostgresSaver
        memory = PostgresSaver(conn_pool)
        
        # 编译获得 Runnable Graph
        app_graph = workflow.compile(checkpointer=memory)
        ```
    3.  **统一会话管理路由**：
        在 `app/api/v1/endpoints/sessions.py` 中，使用 `app_graph.get_state(config)` 和 `app_graph.get_state_history(config)` 替换传统数据库 SQL 查询，实现统一状态管理。

---

> [!NOTE]
> 祝您的 LangChain 与 LangGraph 探索开发旅程圆满顺利！任何在开发过程中遇到的问题，随时可以召唤 AI 进行辅助与 Systematic Debugging。
