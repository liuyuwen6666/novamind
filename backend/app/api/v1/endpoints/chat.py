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
        # ── 第一轮：让 LLM 决定是否调用工具 ──────────────────────────
        accumulated_tools: dict[int, dict] = {}
        assistant_content = ""

        try:
            async for chunk_str in llm.chat(messages, stream=True, tools=tool_registry.list_tools()):
                try:
                    data = json.loads(chunk_str)
                    delta = data.get("choices", [{}])[0].get("delta", {})

                    # 普通文本内容（非工具调用时直接流给前端）
                    content = delta.get("content", "")
                    if content:
                        assistant_content += content
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

                    # 检查 finish_reason
                    finish_reason = data.get("choices", [{}])[0].get("finish_reason")
                    if finish_reason == "tool_calls" and accumulated_tools:
                        # ── 执行所有工具，收集结果 ──────────────────────
                        tool_results = []
                        for idx in sorted(accumulated_tools.keys()):
                            tc_info = accumulated_tools[idx]
                            tool_name = tc_info["name"]
                            tool_id = tc_info["id"] or f"call_{idx}"
                            try:
                                tool_args = json.loads(tc_info["arguments"] or "{}")
                            except json.JSONDecodeError:
                                tool_args = {}
                            logger.info("Tool call: %s %s", tool_name, tool_args)

                            # 通知前端正在调用工具（进度提示，可选）
                            yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name})}\n\n"

                            result = await tool_registry.execute(tool_name, **tool_args)
                            tool_results.append({
                                "tool_id": tool_id,
                                "tool_name": tool_name,
                                "result": result,
                            })

                        accumulated_tools.clear()

                        # ── 第二轮：将工具结果注入对话，让 LLM 生成自然语言回答 ──
                        second_round_messages = list(messages)

                        # 追加 assistant 消息（占位，保持对话连续性）
                        second_round_messages.append(
                            ChatMessage(role="assistant", content=assistant_content or "")
                        )

                        # 追加每个工具的结果消息（role=tool）
                        for tr in tool_results:
                            result_str = (
                                json.dumps(tr["result"], ensure_ascii=False)
                                if not isinstance(tr["result"], str)
                                else tr["result"]
                            )
                            second_round_messages.append(
                                ChatMessage(role="tool", content=result_str, tool_call_id=tr["tool_id"])
                            )

                        # 第二轮流式输出 LLM 自然语言回答给前端
                        async for chunk_str2 in llm.chat(second_round_messages, stream=True, tools=None):
                            try:
                                data2 = json.loads(chunk_str2)
                                delta2 = data2.get("choices", [{}])[0].get("delta", {})
                                content2 = delta2.get("content", "")
                                if content2:
                                    yield f"data: {json.dumps({'content': content2})}\n\n"
                            except Exception:
                                pass

                except Exception:
                    pass

            # 流结束后若仍有未处理的 tool_calls（部分模型不返回 finish_reason）
            if accumulated_tools:
                tool_results = []
                for idx in sorted(accumulated_tools.keys()):
                    tc_info = accumulated_tools[idx]
                    tool_name = tc_info["name"]
                    tool_id = tc_info["id"] or f"call_{idx}"
                    if not tool_name:
                        continue
                    try:
                        tool_args = json.loads(tc_info["arguments"] or "{}")
                    except json.JSONDecodeError:
                        tool_args = {}
                    logger.info("Tool call (fallback): %s %s", tool_name, tool_args)

                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': tool_name})}\n\n"
                    result = await tool_registry.execute(tool_name, **tool_args)
                    tool_results.append({
                        "tool_id": tool_id,
                        "tool_name": tool_name,
                        "result": result,
                    })

                if tool_results:
                    second_round_messages = list(messages)
                    second_round_messages.append(
                        ChatMessage(role="assistant", content=assistant_content or "")
                    )
                    for tr in tool_results:
                        result_str = (
                            json.dumps(tr["result"], ensure_ascii=False)
                            if not isinstance(tr["result"], str)
                            else tr["result"]
                        )
                        second_round_messages.append(
                            ChatMessage(role="tool", content=result_str, tool_call_id=tr["tool_id"])
                        )

                    async for chunk_str2 in llm.chat(second_round_messages, stream=True, tools=None):
                        try:
                            data2 = json.loads(chunk_str2)
                            delta2 = data2.get("choices", [{}])[0].get("delta", {})
                            content2 = delta2.get("content", "")
                            if content2:
                                yield f"data: {json.dumps({'content': content2})}\n\n"
                        except Exception:
                            pass

        except Exception as e:
            logger.error("Stream error: %s", e)
            yield f"data: {json.dumps({'content': f'\\n\\n**AI 请求异常**：{str(e)}'})}\\n\\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")
