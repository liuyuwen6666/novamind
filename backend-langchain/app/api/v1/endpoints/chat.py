import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from langchain_openai import ChatOpenAI

from app.db.session import get_db
from app.core.config import get_settings
from app.schemas.schemas import ChatRequest
from app.services.langchain_service import build_rag_chain
from app.tools.registry import tool_registry

router = APIRouter()
settings = get_settings()

@router.post("")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    RAG + Tool Calling 流式对话接口，返回 Server-Sent Events (SSE)
    """
    messages = request.messages
    if not messages:
        raise HTTPException(status_code=400, detail="对话历史不能为空")

    last_message = messages[-1].content
    workspace_id = request.workspace_id or "default_workspace"

    # 初始化大模型 (兼容 OpenAI Endpoint)
    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        openai_api_key=settings.LLM_API_KEY,
        openai_api_base=settings.LLM_BASE_URL,
        streaming=True,
        temperature=0.2,
    )

    # 1. 动态判断并触发工具执行
    tools_schema = tool_registry.get_schemas_for_llm()
    # 如果有注册工具，将模型和工具描述进行绑定
    llm_with_tools = llm.bind_tools(tools_schema) if tools_schema else llm
    
    try:
        response_msg = await llm_with_tools.ainvoke(last_message)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM 接口连接失败: {e}")

    # 如果模型指示需要调用工具
    if response_msg.tool_calls:
        async def sse_tool_generator():
            for tool_call in response_msg.tool_calls:
                name = tool_call["name"]
                args = tool_call["args"]
                call_id = tool_call["id"]

                # 发送工具调用中的微观状态给前端
                yield f"data: {json.dumps({'choices': [{'delta': {'content': f'🔧 *正在调用外部工具 {name}...*\\n\\n'}}]})}\n\n"
                
                try:
                    tool_result = await tool_registry.aexecute_tool(name, args)
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': f'**工具输出值**: {tool_result}\\n\\n'}}]})}\n\n"

                    # 构造完整的消息流，将结果反馈给模型，继续解答
                    from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
                    messages_for_llm = [
                        HumanMessage(content=last_message),
                        response_msg,
                        ToolMessage(content=str(tool_result), tool_call_id=call_id)
                    ]
                    
                    async for chunk in llm.astream(messages_for_llm):
                        yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk.content}}]})}\n\n"
                except Exception as ex:
                    yield f"data: {json.dumps({'choices': [{'delta': {'content': f'❌ 工具调用发生错误: {ex}'}}]})}\n\n"
            
            yield "data: [DONE]\n\n"

        return StreamingResponse(sse_tool_generator(), media_type="text/event-stream")

    # 2. RAG 知识库检索模式
    if request.use_rag:
        try:
            chain = await build_rag_chain(db, workspace_id)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"RAG 链构建失败: {e}")

        async def sse_rag_generator():
            async for chunk in chain.astream(last_message):
                # 兼容前端打字机 SSE 解析格式
                yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk}}]})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(sse_rag_generator(), media_type="text/event-stream")

    # 3. 普通问答模式 (不使用 RAG，直接与大模型对话)
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    lc_msgs = []
    for m in messages:
        if m.role == "system":
            lc_msgs.append(SystemMessage(content=m.content))
        elif m.role == "user":
            lc_msgs.append(HumanMessage(content=m.content))
        elif m.role == "assistant":
            lc_msgs.append(AIMessage(content=m.content))

    async def sse_normal_generator():
        async for chunk in llm.astream(lc_msgs):
            yield f"data: {json.dumps({'choices': [{'delta': {'content': chunk.content}}]})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse_normal_generator(), media_type="text/event-stream")
