import uuid
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from typing import Optional

from app.core.logging import get_logger
from app.schemas.schemas import ChatRequest, SessionChatRequest
from app.services.agent_service import run_agent_stream

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/", summary="智能体对话（支持 RAG + Tool Calling + SSE 流式）")
async def chat(
    request: ChatRequest,
    session_id: Optional[str] = None
):
    """
    兼容原端点：临时对话。
    如果不传 session_id，则生成一个随机的临时 UUID 作为 thread_id。
    """
    # 提取最后一条用户消息
    user_message = request.messages[-1].content if request.messages else ""
    
    # 产生或使用传入的 session_id
    active_session_id = session_id or str(uuid.uuid4())
    logger.info(f"Chat request received: use_rag={request.use_rag}, session_id={active_session_id}")

    return StreamingResponse(
        run_agent_stream(
            session_id=active_session_id,
            message=user_message,
            use_rag=request.use_rag,
            workspace_id=request.workspace_id
        ),
        media_type="text/event-stream"
    )


@router.post("/session", summary="会话式智能体对话（配合持久化会话列表）")
async def session_chat(request: SessionChatRequest):
    """
    会话式对话：传入前端通过 /sessions 接口建立的已存在的 session_id (thread_id)
    """
    logger.info(f"Session chat request: session_id={request.session_id}, use_rag={request.use_rag}")
    
    return StreamingResponse(
        run_agent_stream(
            session_id=str(request.session_id),
            message=request.message,
            use_rag=request.use_rag,
            workspace_id=request.workspace_id
        ),
        media_type="text/event-stream"
    )
