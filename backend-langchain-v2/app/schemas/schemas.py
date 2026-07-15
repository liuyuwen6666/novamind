import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ── File Schemas ──────────────────────────────────────────────────

class FileUploadResponse(BaseModel):
    id: uuid.UUID
    file_name: str
    file_hash: str
    status: str
    created_at: datetime


class FileListItem(BaseModel):
    id: uuid.UUID
    file_name: str
    file_size: int
    status: str
    created_at: datetime


# ── Chat Schemas ──────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system|tool)$")
    content: str
    tool_call_id: Optional[str] = None  # role=tool 时必填（OpenAI/LangChain Tool Calling 规范）

    def to_api_dict(self) -> dict:
        """序列化为 LLM API 消息格式，None 字段自动过滤"""
        d = {"role": self.role, "content": self.content}
        if self.tool_call_id is not None:
            d["tool_call_id"] = self.tool_call_id
        return d


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    workspace_id: Optional[str] = None
    stream: bool = True
    use_rag: bool = True


# ── Session Schemas ───────────────────────────────────────────────

class SessionCreate(BaseModel):
    visitor_id: str
    title: str = "新会话"


class SessionOut(BaseModel):
    id: str  # 配合 LangGraph Checkpoint 的 thread_id（可以是 UUID 或普通 string）
    visitor_id: Optional[str] = None
    title: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    created_at: Optional[datetime] = None
    sources: Optional[List[Dict[str, Any]]] = None

    model_config = {"from_attributes": True}


class SessionChatRequest(BaseModel):
    visitor_id: str
    session_id: str  # 对应 LangGraph 的 thread_id
    message: str
    use_rag: bool = True
    workspace_id: Optional[str] = None


# ── Chunk Schemas ─────────────────────────────────────────────────

class ChunkOut(BaseModel):
    id: uuid.UUID
    chunk_index: int
    content: str
    score: Optional[float] = None
    file_name: Optional[str] = None
