import uuid
from datetime import datetime
from typing import Optional

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
    tool_call_id: Optional[str] = None  # role=tool 时必填（OpenAI Tool Calling 规范）

    def to_api_dict(self) -> dict:
        """序列化为 LLM API 消息格式，None 字段自动过滤"""
        d = {"role": self.role, "content": self.content}
        if self.tool_call_id is not None:
            d["tool_call_id"] = self.tool_call_id
        return d


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    workspace_id: str | None = None
    stream: bool = True
    use_rag: bool = True


# ── Session Schemas ───────────────────────────────────────────────

class SessionCreate(BaseModel):
    visitor_id: str
    title: str = "新会话"


class SessionOut(BaseModel):
    id: uuid.UUID
    visitor_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    sources: Optional[list[dict]] = None

    model_config = {"from_attributes": True}


class SessionChatRequest(BaseModel):
    visitor_id: str
    session_id: uuid.UUID
    message: str
    use_rag: bool = True
    workspace_id: str | None = None


# ── Chunk Schemas ─────────────────────────────────────────────────

class ChunkOut(BaseModel):
    id: uuid.UUID
    chunk_index: int
    content: str
    score: float | None = None
    file_name: Optional[str] = None

