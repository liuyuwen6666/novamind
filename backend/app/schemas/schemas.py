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


# ── Chunk Schemas ─────────────────────────────────────────────────

class ChunkOut(BaseModel):
    id: uuid.UUID
    chunk_index: int
    content: str
    score: float | None = None
