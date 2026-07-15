import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.tools import create_retriever_tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from app.db.session import get_db
from app.core.config import get_settings
from app.schemas.schemas import ChatRequest
from app.services.langchain_service import SQLModelRetriever
from app.services.embedding_service import VolcEngineEmbeddings, EmbeddingService
from app.tools.registry import tool_registry

router = APIRouter()
settings = get_settings()

@router.post("")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    使用新版 LangChain v1.2+ 的 create_agent 机制的问答接口。
    将知识库和天气服务作为统一工具链传入 Agent Graph，由底层的 StateGraph 自动循环分发并支持 SSE 流。
    """
    messages = request.messages
    if not messages:
        raise HTTPException(status_code=400, detail="对话历史不能为空")

    workspace_id = request.workspace_id or "default_workspace"

    # 1. 实例化 ChatOpenAI 基础大模型
    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        openai_api_key=settings.LLM_API_KEY,
        openai_api_base=settings.LLM_BASE_URL,
        streaming=True,
        temperature=0.2,
    )

    # 2. 构造工具链
    tools = []
    
    # 知识库检索工具
    if request.use_rag:
        embedding_service = EmbeddingService()
        embeddings_wrapper = VolcEngineEmbeddings(embedding_service)
        retriever = SQLModelRetriever(
            session=db,
            embeddings=embeddings_wrapper,
            workspace_id=workspace_id,
            top_k=settings.RAG_TOP_K
        )
        
        retriever_tool = create_retriever_tool(
            retriever,
            "knowledge_search",
            "用于在公司内部知识库中搜索关于系统政策、产品开发、业务细节及已知背景文件。若用户的问题与业务手册、背景背景或内部文档有关，必须调用此工具。"
        )
        tools.append(retriever_tool)

    # 其他天气/辅助工具
    tools.extend(tool_registry.get_all_tools())

    # 3. 设定系统 prompt 引导 Agent 决策行为
    system_prompt = (
        "你是一个专业、礼貌的企业知识库助手。你可以自主选择调用工具来查阅内部知识库、查询天气，或凭自身能力回答。"
        "当且仅当调用了 knowledge_search 工具却未检索到相关内容时，请明确回答'知识库中未找到相关内容'。"
    )

    # 4. 创建先进的智能体工作流图 (Agent Graph)
    # 它在内部自动串接 model 节点与 tools 执行环路，直到给出完整解答
    agent_graph = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt
    )

    # 5. 映射并拼接对话历史
    lc_messages = []
    for m in messages:
        if m.role == "system":
            lc_messages.append(SystemMessage(content=m.content))
        elif m.role == "user":
            lc_messages.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            lc_messages.append(AIMessage(content=m.content))

    inputs = {"messages": lc_messages}

    # 6. SSE 异步流式生成器
    async def sse_agent_generator():
        try:
            # 捕获图运行时的细微节点事件
            async for event in agent_graph.astream_events(inputs, version="v2"):
                kind = event["event"]
                
                # 工具调用开始
                if kind == "on_tool_start":
                    tool_name = event["name"]
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': f'🔧 *正在调用外部工具 `{tool_name}`...*\\n\\n'}}]})}\n\n"
                
                # 工具调用成功
                elif kind == "on_tool_end":
                    tool_name = event["name"]
                    tool_output = event["data"].get("output", "")
                    if tool_name == "knowledge_search":
                        yield f"data: {json.dumps({'choices': [{'delta': {'content': f'📖 *已完成企业知识库检索*\\n\\n'}}]})}\n\n"
                    else:
                        yield f"data: {json.dumps({'choices': [{'delta': {'content': f'📊 *工具运行结果*: {tool_output}\\n\\n'}}]})}\n\n"
                
                # 大模型流式输出
                elif kind == "on_chat_model_stream":
                    content = event["data"]["chunk"].content
                    if content:
                        yield f"data: {json.dumps({'choices': [{'delta': {'content': content}}]})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'choices': [{'delta': {'content': f'❌ Agent 运行阶段发生异常: {e}'}}]})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_agent_generator(), media_type="text/event-stream")
