import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.database import get_db
from app.memory.short_term import ShortTermMemory
from app.prompts.system import build_rag_system_prompt, NO_CONTEXT_SYSTEM_PROMPT
from app.rag.retriever import RAGRetriever
from app.repositories.document_repository import DocumentRepository
from app.schemas.schemas import ChatMessage, ChatRequest
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.tools.registry import tool_registry
from app.tools.weather_tool import WeatherTool

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])

# 注册 Tools
tool_registry.register(WeatherTool())

# 内存 Memory（V1 单实例，V2 改为 session 级）
_memory = ShortTermMemory()


@router.post("/", summary="AI 对话（支持 RAG + Tool Calling + Streaming）")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    user_message = request.messages[-1]
    _memory.add(user_message)

    # RAG 检索
    context = ""
    if request.use_rag:
        doc_repo = DocumentRepository(db)
        embedding_svc = EmbeddingService()
        retriever = RAGRetriever(doc_repo, embedding_svc)
        chunks = await retriever.retrieve(user_message.content, workspace_id=request.workspace_id)
        if chunks:
            context = retriever.build_context(chunks)

    # 构建 System Prompt
    system_prompt = build_rag_system_prompt(context) if context else NO_CONTEXT_SYSTEM_PROMPT
    system_msg = ChatMessage(role="system", content=system_prompt)
    messages = [system_msg] + _memory.get_messages()

    llm = LLMService()

    async def stream_generator():
        full_content = ""
        try:
            async for chunk_str in llm.chat(messages, stream=True, tools=tool_registry.list_tools()):
                try:
                    data = json.loads(chunk_str)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        full_content += content
                        yield f"data: {json.dumps({'content': content})}\n\n"
                    # Tool Call 处理
                    tool_calls = delta.get("tool_calls")
                    if tool_calls:
                        for tc in tool_calls:
                            fn = tc.get("function", {})
                            tool_name = fn.get("name")
                            tool_args = json.loads(fn.get("arguments", "{}"))
                            logger.info("Tool call: %s %s", tool_name, tool_args)
                            result = await tool_registry.execute(tool_name, **tool_args)
                            yield f"data: {json.dumps({'tool_call': tool_name, 'result': result})}\n\n"
                except Exception:
                    pass
        except Exception as e:
            logger.error("Stream error: %s", e)
            yield f"data: {json.dumps({'content': f'\\n\\n**AI 请求异常**：{str(e)}'})}\n\n"
        
        _memory.add(ChatMessage(role="assistant", content=full_content))
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")
