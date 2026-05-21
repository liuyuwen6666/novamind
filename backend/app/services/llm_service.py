from __future__ import annotations

import uuid
from typing import AsyncIterator

import httpx

from app.core.config import get_settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger
from app.schemas.schemas import ChatMessage

logger = get_logger(__name__)
settings = get_settings()


class LLMService:
    """LongCat LLM 服务，支持 streaming"""

    def __init__(self) -> None:
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL
        self.model = settings.LLM_MODEL

    async def chat(
        self,
        messages: list[ChatMessage],
        stream: bool = True,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        payload: dict = {
            "model": self.model,
            "messages": [m.model_dump() for m in messages],
            "stream": stream,
        }
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            chunk = line[6:]
                            if chunk == "[DONE]":
                                break
                            yield chunk
        except Exception as e:
            logger.error("LLM request failed: %s", e)
            raise LLMError(str(e)) from e
