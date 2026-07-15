import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class FileUploadResponse(BaseModel):
    id: uuid.UUID
    file_name: str
    file_hash: str
    status: str
    created_at: datetime


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system|tool)$")
    content: str
    tool_call_id: Optional[str] = None

    def to_api_dict(self) -> dict:
        d = {"role": self.role, "content": self.content}
        if self.tool_call_id is not None:
            d["tool_call_id"] = self.tool_call_id
        return d


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    workspace_id: Optional[str] = "default_workspace"
    stream: bool = True
    use_rag: bool = True
