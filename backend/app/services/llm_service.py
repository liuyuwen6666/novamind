from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from app.core.config import LLMProvider, get_settings
from app.core.exceptions import LLMError
from app.core.logging import get_logger
from app.schemas.schemas import ChatMessage

logger = get_logger(__name__)
settings = get_settings()


PROVIDER_TIPS = {
    LLMProvider.LONGCAT: "请检查 LLM_API_KEY 是否正确（LongCat 密钥以 ak_ 开头）",
    LLMProvider.TENCENT_HUNYUAN: (
        "请检查 LLM_API_KEY 是否正确（腾讯混元需从 https://console.cloud.tencent.com/ 获取有效密钥）\n"
        "提示：当前密钥可能为其他服务商的密钥，请替换为腾讯混元专用的 API Key"
    ),
    LLMProvider.OPENAI_COMPATIBLE: "请检查 LLM_API_KEY 和 LLM_BASE_URL 是否正确",
}


def _provider_error_tip(provider: LLMProvider, status_code: int) -> str:
    base_tip = PROVIDER_TIPS.get(provider, "请检查 LLM 配置是否正确")
    if status_code == 401:
        return f"身份认证失败（401）。{base_tip}。如需切换回 LongCat，请修改 .env 中的 LLM_BASE_URL"
    if status_code == 403:
        return f"权限不足（403）。请确认 API Key 有访问该模型的权限"
    if status_code == 429:
        return f"请求过于频繁（429）。请稍后重试"
    if status_code == 404:
        return f"接口地址不正确（404）。请确认 LLM_BASE_URL 和 LLM_MODEL 是否正确"
    return ""


class LLMService:
    """多模型 LLM 服务，支持 streaming，自动适配不同提供商"""

    def __init__(self) -> None:
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL.rstrip("/")
        self.model = settings.LLM_MODEL
        self.provider = settings.provider

    async def chat(
        self,
        messages: list[ChatMessage],
        stream: bool = True,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict = {
            "model": self.model,
            "messages": [m.to_api_dict() for m in messages],
        }

        if stream and self.provider == LLMProvider.TENCENT_HUNYUAN:
            payload["stream"] = False
            stream = False
            logger.info("腾讯混元模型使用非 streaming 模式")
        else:
            payload["stream"] = stream

        if tools:
            payload["tools"] = tools

        url = f"{self.base_url}/chat/completions"

        try:
            if stream:
                async for chunk in self._stream_chat(url, headers, payload):
                    yield chunk
            else:
                chunk = await self._non_stream_chat(url, headers, payload)
                if chunk:
                    yield chunk
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                body = e.response.text
            except Exception:
                body = ""
            tip = _provider_error_tip(self.provider, status_code)
            msg = f"HTTP {status_code}"
            if body:
                msg += f" - {body[:300]}"
            if tip:
                msg += f"\n💡 {tip}"
            logger.error("LLM request failed [%s]: %s", self.provider.value, msg)
            raise LLMError(msg) from e
        except httpx.RequestError as e:
            msg = f"无法连接到 LLM 服务（{self.base_url}）：{e}"
            logger.error(msg)
            raise LLMError(msg) from e
        except Exception as e:
            logger.error("LLM request failed [%s]: %s", self.provider.value, e)
            raise LLMError(str(e)) from e

    async def _stream_chat(
        self,
        url: str,
        headers: dict,
        payload: dict,
    ) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                url,
                headers=headers,
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        chunk = line[6:]
                        if chunk == "[DONE]":
                            break
                        yield chunk

    async def _non_stream_chat(
        self,
        url: str,
        headers: dict,
        payload: dict,
    ) -> str | None:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            return None
        delta = choices[0].get("message", {})
        return json.dumps({
            "choices": [{
                "delta": delta,
                "finish_reason": choices[0].get("finish_reason"),
            }]
        })
