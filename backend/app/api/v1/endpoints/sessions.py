import json
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.database import get_db
from app.prompts.system import build_rag_system_prompt, NO_CONTEXT_SYSTEM_PROMPT
from app.rag.retriever import RAGRetriever
from app.repositories.document_repository import DocumentRepository
from app.repositories.session_repository import SessionRepository
from app.schemas.schemas import (
    ChatMessage,
    MessageOut,
    SessionChatRequest,
    SessionCreate,
    SessionOut,
)
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.tools.registry import tool_registry

logger = get_logger(__name__)
router = APIRouter(prefix="/chat/sessions", tags=["Sessions"])
settings = get_settings()


def _check_ownership(session, visitor_id: str) -> None:
    """校验会话归属，不属于当前 visitor 则抛 403"""
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在")
    if session.visitor_id != visitor_id:
        raise HTTPException(status_code=403, detail="无权访问此会话")


# ── 创建会话 ──────────────────────────────────────────────────────

@router.post("/", response_model=SessionOut, summary="创建新会话")
async def create_session(body: SessionCreate, db: AsyncSession = Depends(get_db)):
    repo = SessionRepository(db)
    session = await repo.create_session(visitor_id=body.visitor_id, title=body.title)
    return session


# ── 会话列表 ──────────────────────────────────────────────────────

@router.get("/", response_model=list[SessionOut], summary="获取会话列表")
async def list_sessions(visitor_id: str, db: AsyncSession = Depends(get_db)):
    repo = SessionRepository(db)
    return await repo.list_sessions(visitor_id=visitor_id)


# ── 消息历史 ──────────────────────────────────────────────────────

@router.get("/{session_id}/messages", response_model=list[MessageOut], summary="获取消息历史")
async def get_messages(
    session_id: uuid.UUID,
    visitor_id: str,
    db: AsyncSession = Depends(get_db),
):
    repo = SessionRepository(db)
    session = await repo.get_session(session_id)
    _check_ownership(session, visitor_id)
    return await repo.get_messages(session_id)


# ── 会话内发送消息（SSE 流式） ───────────────────────────────────

@router.post("/chat", summary="会话内流式对话")
async def session_chat(body: SessionChatRequest, db: AsyncSession = Depends(get_db)):
    repo = SessionRepository(db)

    # 1. 校验 session 归属
    session = await repo.get_session(body.session_id)
    _check_ownership(session, body.visitor_id)

    # 2. 保存用户消息
    await repo.add_message(body.session_id, role="user", content=body.message)

    # 3. 读取最近 N 条历史（含刚保存的这条）
    recent = await repo.get_recent_messages(body.session_id, limit=settings.MAX_MEMORY_MESSAGES)
    history = [ChatMessage(role=m.role, content=m.content) for m in recent]

    # 4. RAG 检索
    context = ""
    sources_data = []
    if body.use_rag:
        doc_repo = DocumentRepository(db)
        retriever = RAGRetriever(doc_repo, EmbeddingService())
        chunks = await retriever.retrieve(body.message, workspace_id=body.workspace_id)
        if chunks:
            context = retriever.build_context(chunks)
            sources_data = [
                {
                    "file_name": c.file_name or "未知文档",
                    "chunk_index": c.chunk_index,
                    "score": round(c.score, 4) if c.score is not None else 0.0
                }
                for c in chunks
            ]


    # 5. 构建 system prompt
    system_prompt = build_rag_system_prompt(context) if context else NO_CONTEXT_SYSTEM_PROMPT
    system_msg = ChatMessage(role="system", content=system_prompt)
    messages = [system_msg] + history

    llm = LLMService()
    supports_tools = settings.supports_tool_calling
    full_content = ""

    async def stream_generator():
        nonlocal full_content
        assistant_content = ""

        try:
            if supports_tools:
                accumulated_tools: dict[int, dict] = {}
                async for chunk_str in llm.chat(messages, stream=True, tools=tool_registry.list_tools()):
                    try:
                        data = json.loads(chunk_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})

                        content = delta.get("content", "")
                        if content:
                            assistant_content += content
                            full_content += content
                            yield f"data: {json.dumps({'content': content})}\n\n"

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

                        finish_reason = data.get("choices", [{}])[0].get("finish_reason")
                        if finish_reason == "tool_calls" and accumulated_tools:
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

                                tool_desc = ""
                                tool_obj = tool_registry.get(tool_name)
                                if tool_obj:
                                    tool_desc = getattr(tool_obj, "description", "")
                                args_str = json.dumps(tool_args, ensure_ascii=False)

                                start_md = f"\n\n> 🔧 **正在调用系统工具**：`{tool_name}`"
                                if tool_desc:
                                    start_md += f" ({tool_desc})"
                                start_md += "\n"
                                if tool_args:
                                    start_md += f"> 📥 **输入参数**：`{args_str}`\n"

                                assistant_content += start_md
                                full_content += start_md
                                yield f"data: {json.dumps({'content': start_md})}\n\n"

                                try:
                                    result = await tool_registry.execute(tool_name, **tool_args)
                                    result_json_str = (
                                        json.dumps(result, ensure_ascii=False, indent=2)
                                        if not isinstance(result, (str, int, float, bool))
                                        else str(result)
                                    )
                                    formatted_result = "\n".join(f"> {line}" for line in result_json_str.split("\n"))
                                    result_md = (
                                        f"> 📤 **工具返回结果**：\n"
                                        f"> ```json\n"
                                        f"{formatted_result}\n"
                                        f"> ```\n\n"
                                    )
                                except Exception as te:
                                    result = f"Error: {str(te)}"
                                    result_md = f"> ❌ **工具执行失败**：`{str(te)}`\n\n"

                                assistant_content += result_md
                                full_content += result_md
                                yield f"data: {json.dumps({'content': result_md})}\n\n"

                                tool_results.append({
                                    "tool_id": tool_id,
                                    "tool_name": tool_name,
                                    "result": result,
                                })

                            accumulated_tools.clear()

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
                                        full_content += content2
                                        yield f"data: {json.dumps({'content': content2})}\n\n"
                                except Exception:
                                    pass

                    except Exception:
                        pass

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

                        tool_desc = ""
                        tool_obj = tool_registry.get(tool_name)
                        if tool_obj:
                            tool_desc = getattr(tool_obj, "description", "")
                        args_str = json.dumps(tool_args, ensure_ascii=False)

                        start_md = f"\n\n> 🔧 **正在调用系统工具**：`{tool_name}`"
                        if tool_desc:
                            start_md += f" ({tool_desc})"
                        start_md += "\n"
                        if tool_args:
                            start_md += f"> 📥 **输入参数**：`{args_str}`\n"

                        assistant_content += start_md
                        full_content += start_md
                        yield f"data: {json.dumps({'content': start_md})}\n\n"

                        try:
                            result = await tool_registry.execute(tool_name, **tool_args)
                            result_json_str = (
                                json.dumps(result, ensure_ascii=False, indent=2)
                                if not isinstance(result, (str, int, float, bool))
                                else str(result)
                            )
                            formatted_result = "\n".join(f"> {line}" for line in result_json_str.split("\n"))
                            result_md = (
                                f"> 📤 **工具返回结果**：\n"
                                f"> ```json\n"
                                f"{formatted_result}\n"
                                f"> ```\n\n"
                            )
                        except Exception as te:
                            result = f"Error: {str(te)}"
                            result_md = f"> ❌ **工具执行失败**：`{str(te)}`\n\n"

                        assistant_content += result_md
                        full_content += result_md
                        yield f"data: {json.dumps({'content': result_md})}\n\n"

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
                                    full_content += content2
                                    yield f"data: {json.dumps({'content': content2})}\n\n"
                            except Exception:
                                pass
            else:
                async for chunk_str in llm.chat(messages, stream=True, tools=None):
                    try:
                        data = json.loads(chunk_str)
                        delta = data.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            assistant_content += content
                            full_content += content
                            yield f"data: {json.dumps({'content': content})}\n\n"
                    except Exception:
                        pass

        except Exception as e:
            logger.error("Stream error: %s", e)
            error_msg = f"\n\n❌ **请求异常**：{str(e)}"
            full_content += error_msg
            yield f"data: {json.dumps({'content': error_msg})}\n\n"

        # 过滤 sources_data，只保留在 full_content 中出现过角标 [i] 的 chunks
        final_sources = []
        if sources_data and full_content:
            ref_indices = [int(x) for x in re.findall(r"\[([1-9][0-9]*)\]", full_content)]
            ref_indices = sorted(list(set(ref_indices)))
            for idx in ref_indices:
                list_idx = idx - 1
                if 0 <= list_idx < len(sources_data):
                    final_sources.append(sources_data[list_idx])

        # 降级兜底：如果模型由于偶发原因没有使用角标，但开启了 RAG，我们默认取最相关的 top 2 来源展现给用户，避免全部展现干扰视线
        if not final_sources and sources_data:
            final_sources = sources_data[:2]

        # 6. 保存 AI 回复 + 更新 updated_at
        if full_content:
            await repo.add_message(body.session_id, role="assistant", content=full_content, sources=final_sources)

        await repo.touch_session(body.session_id)

        if final_sources:
            yield f"data: {json.dumps({'sources': final_sources})}\n\n"

        yield "data: [DONE]\n\n"


    return StreamingResponse(stream_generator(), media_type="text/event-stream")

