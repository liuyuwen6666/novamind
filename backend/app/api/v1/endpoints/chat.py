import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.database import get_db
from app.prompts.system import build_rag_system_prompt, NO_CONTEXT_SYSTEM_PROMPT
from app.rag.retriever import RAGRetriever
from app.repositories.document_repository import DocumentRepository
from app.schemas.schemas import ChatMessage, ChatRequest
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.tools.registry import tool_registry
from app.tools.weather_tool import WeatherTool
from app.tools.geocode_tool import GeocodeQueryTool

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])

# 注册 Tools
tool_registry.register(WeatherTool())
tool_registry.register(GeocodeQueryTool())


@router.post("/", summary="AI 对话（支持 RAG + Tool Calling + Streaming）")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    user_message = request.messages[-1]

    # RAG 检索（仅当 use_rag=True 时执行）
    context = ""
    if request.use_rag:
        doc_repo = DocumentRepository(db)
        embedding_svc = EmbeddingService()
        retriever = RAGRetriever(doc_repo, embedding_svc)
        chunks = await retriever.retrieve(user_message.content, workspace_id=request.workspace_id)
        if chunks:
            context = retriever.build_context(chunks)

    # 构建 System Prompt
    # use_rag=True 且有检索结果 → RAG prompt（注入知识库上下文）
    # use_rag=False 或无检索结果 → 纯 AI prompt（明确禁止使用文档内容）
    system_prompt = build_rag_system_prompt(context) if context else NO_CONTEXT_SYSTEM_PROMPT
    system_msg = ChatMessage(role="system", content=system_prompt)

    # 使用前端传来的完整对话历史，限制最大消息数防止 token 溢出
    # 保留最近 MAX_MEMORY_MESSAGES 条，确保 user/assistant 成对（偶数）
    from app.core.config import get_settings
    _settings = get_settings()
    history = list(request.messages)
    max_msgs = _settings.MAX_MEMORY_MESSAGES  # 默认 20
    if len(history) > max_msgs:
        # 从尾部截取，保证 user/assistant 成对
        history = history[-max_msgs:]
        # 确保第一条是 user（不能以 assistant 开头）
        while history and history[0].role != "user":
            history = history[1:]
    messages = [system_msg] + history

    llm = LLMService()

    async def stream_generator():
        full_content = ""
        # tool_calls 累积字典: index → {id, name, arguments_str}
        accumulated_tools: dict[int, dict] = {}

        try:
            async for chunk_str in llm.chat(messages, stream=True, tools=tool_registry.list_tools()):
                try:
                    data = json.loads(chunk_str)
                    delta = data.get("choices", [{}])[0].get("delta", {})

                    # 普通文本内容
                    content = delta.get("content", "")
                    if content:
                        full_content += content
                        yield f"data: {json.dumps({'content': content})}\n\n"

                    # 累积 tool_calls（LLM 会把 name 和 arguments 分散在多个 chunk）
                    tool_calls = delta.get("tool_calls")
                    if tool_calls:
                        for tc in tool_calls:
                            idx = tc.get("index", 0)
                            fn = tc.get("function", {})
                            if idx not in accumulated_tools:
                                accumulated_tools[idx] = {"id": tc.get("id"), "name": "", "arguments": ""}
                            if tc.get("id"):
                                accumulated_tools[idx]["id"] = tc["id"]
                            if fn.get("name"):
                                accumulated_tools[idx]["name"] = fn["name"]
                            if fn.get("arguments"):
                                accumulated_tools[idx]["arguments"] += fn["arguments"]

                    # 检查是否流式结束（finish_reason）
                    finish_reason = data.get("choices", [{}])[0].get("finish_reason")
                    if finish_reason == "tool_calls" and accumulated_tools:
                        # 执行所有累积完成的工具调用
                        for idx in sorted(accumulated_tools.keys()):
                            tc_info = accumulated_tools[idx]
                            tool_name = tc_info["name"]
                            try:
                                tool_args = json.loads(tc_info["arguments"] or "{}")
                            except json.JSONDecodeError:
                                tool_args = {}
                            logger.info("Tool call: %s %s", tool_name, tool_args)
                            result = await tool_registry.execute(tool_name, **tool_args)
                            yield f"data: {json.dumps({'tool_call': tool_name, 'result': result})}\n\n"
                        accumulated_tools.clear()

                except Exception:
                    pass

            # 流结束时若仍有未执行的 tool_calls（部分模型不返回 finish_reason）
            if accumulated_tools:
                for idx in sorted(accumulated_tools.keys()):
                    tc_info = accumulated_tools[idx]
                    tool_name = tc_info["name"]
                    if not tool_name:
                        continue
                    try:
                        tool_args = json.loads(tc_info["arguments"] or "{}")
                    except json.JSONDecodeError:
                        tool_args = {}
                    logger.info("Tool call (fallback): %s %s", tool_name, tool_args)
                    result = await tool_registry.execute(tool_name, **tool_args)
                    yield f"data: {json.dumps({'tool_call': tool_name, 'result': result})}\n\n"

        except Exception as e:
            logger.error("Stream error: %s", e)
            yield f"data: {json.dumps({'content': f'\\n\\n**AI 请求异常**：{str(e)}'})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")

