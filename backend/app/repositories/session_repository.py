import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ChatMessage, ChatSession


class SessionRepository:
    """会话 & 消息数据库操作"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Session ──────────────────────────────────────────────────

    async def create_session(self, visitor_id: str, title: str = "新会话") -> ChatSession:
        session = ChatSession(visitor_id=visitor_id, title=title)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: uuid.UUID) -> ChatSession | None:
        result = await self.db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions(self, visitor_id: str) -> list[ChatSession]:
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.visitor_id == visitor_id)
            .order_by(ChatSession.updated_at.desc())
        )
        return list(result.scalars().all())

    async def touch_session(self, session_id: uuid.UUID) -> None:
        """更新 updated_at（每次发消息后调用）"""
        await self.db.execute(
            update(ChatSession)
            .where(ChatSession.id == session_id)
            .values(updated_at=datetime.now(timezone.utc))
        )
        await self.db.commit()

    # ── Messages ─────────────────────────────────────────────────

    async def add_message(self, session_id: uuid.UUID, role: str, content: str) -> ChatMessage:
        msg = ChatMessage(session_id=session_id, role=role, content=content)
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def get_messages(self, session_id: uuid.UUID) -> list[ChatMessage]:
        """获取会话所有消息，正序"""
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_recent_messages(self, session_id: uuid.UUID, limit: int = 20) -> list[ChatMessage]:
        """获取最近 N 条消息，发给 LLM 用"""
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        msgs = list(result.scalars().all())
        return list(reversed(msgs))  # 返回正序
