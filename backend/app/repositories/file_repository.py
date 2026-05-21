import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import FileRecord


class FileRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_hash(self, file_hash: str) -> FileRecord | None:
        result = await self.db.execute(select(FileRecord).where(FileRecord.file_hash == file_hash))
        return result.scalar_one_or_none()

    async def create(self, file_name: str, file_hash: str, file_size: int, workspace_id: str | None = None) -> FileRecord:
        record = FileRecord(
            file_name=file_name,
            file_hash=file_hash,
            file_size=file_size,
            workspace_id=workspace_id,
            status="pending",
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def update_status(self, file_id: uuid.UUID, status: str) -> None:
        result = await self.db.execute(select(FileRecord).where(FileRecord.id == file_id))
        record = result.scalar_one_or_none()
        if record:
            record.status = status
            await self.db.commit()

    async def list_all(self, workspace_id: str | None = None) -> Sequence[FileRecord]:
        stmt = select(FileRecord).order_by(FileRecord.created_at.desc())
        if workspace_id:
            stmt = stmt.where(FileRecord.workspace_id == workspace_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete(self, file_id: uuid.UUID) -> None:
        result = await self.db.execute(select(FileRecord).where(FileRecord.id == file_id))
        record = result.scalar_one_or_none()
        if record:
            await self.db.delete(record)
            await self.db.commit()
