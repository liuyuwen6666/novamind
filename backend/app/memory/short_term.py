from app.schemas.schemas import ChatMessage
from app.core.config import get_settings

settings = get_settings()


class ShortTermMemory:
    """短期记忆：保留最近 N 条消息"""

    def __init__(self, max_messages: int = None) -> None:
        self.max_messages = max_messages or settings.MAX_MEMORY_MESSAGES
        self._messages: list[ChatMessage] = []

    def add(self, message: ChatMessage) -> None:
        self._messages.append(message)
        self._trim()

    def _trim(self) -> None:
        if len(self._messages) > self.max_messages:
            # 保留 system 消息（如果有），截断旧消息
            system = [m for m in self._messages if m.role == "system"]
            others = [m for m in self._messages if m.role != "system"]
            others = others[-(self.max_messages - len(system)):]
            self._messages = system + others

    def get_messages(self) -> list[ChatMessage]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()
