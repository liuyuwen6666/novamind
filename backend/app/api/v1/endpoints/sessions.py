import json
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
    if body.use_rag:
        doc_repo = DocumentRepository(db)
        retriever = RAGRetriever(doc_repo, EmbeddingService())
        chunks = await retriever.retrieve(body.message, workspace_id=body.workspace_id)
        if chunks:
            context = retriever.build_context(chunks)

    # 5. 构建 system prompt
    system_prompt = build_rag_system_prompt(context) if context else NO_CONTEXT_SYSTEM_PROMPT
    system_msg = ChatMessage(role="system", content=system_prompt)
    messages = [system_msg] + history

    llm = LLMService()
    full_content = ""

    async def stream_generator():
        nonlocal full_content
        accumulated_tools: dict[int, dict] = {}

        try:
            async for chunk_str in llm.chat(messages, stream=True, tools=tool_registry.list_tools()):
                try:
                    data = json.loads(chunk_str)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        full_content += content
                        yield f"data: {json.dumps({'content': content})}\n\n"

                    # 累积 tool_calls
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
                        for idx in sorted(accumulated_tools.keys()):
                            tc_info = accumulated_tools[idx]
                            tool_name = tc_info["name"]
                            try:
                                tool_args = json.loads(tc_info["arguments"] or "{}")
                            except json.JSONDecodeError:
                                tool_args = {}
                            result = await tool_registry.execute(tool_name, **tool_args)
                            yield f"data: {json.dumps({'tool_call': tool_name, 'result': result})}\n\n"
                        accumulated_tools.clear()

                except Exception:
                    pass

            # 流结束兜底执行
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
                    result = await tool_registry.execute(tool_name, **tool_args)
                    yield f"data: {json.dumps({'tool_call': tool_name, 'result': result})}\n\n"

        except Exception as e:
            logger.error("Stream error: %s", e)
            yield f"data: {json.dumps({'content': f'\\n\\n**请求异常**：{str(e)}'})}\n\n"

        # 6. 保存 AI 回复 + 更新 updated_at
        if full_content:
            await repo.add_message(body.session_id, role="assistant", content=full_content)
        await repo.touch_session(body.session_id)
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")
