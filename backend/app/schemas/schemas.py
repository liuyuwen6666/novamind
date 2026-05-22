import uuid
from datetime import datetime

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
