import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Column, Relationship
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Text
from pgvector.sqlalchemy import Vector

# 火山引擎 Embedding 维度默认通常为 1024
EMBEDDING_DIMENSION = 1024

class File(SQLModel, table=True):
    """文件表：记录上传的 PDF 文件状态及其元数据"""
    __tablename__ = "files"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: str = Field(default="default_tenant", index=True)      # 预留多租户
    workspace_id: str = Field(default="default_workspace", index=True) # 预留工作空间
    file_name: str = Field(max_length=255)
    file_hash: str = Field(max_length=32, index=True)                 # 用于去重的 MD5
    status: str = Field(default="pending", max_length=20)             # pending, processing, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # 级联删除：文件被删，其对应的切片向量自动删除
    documents: list["Document"] = Relationship(
        back_populates="file",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

class Document(SQLModel, table=True):
    """文档切片表：存储具体的文本内容及其 pgvector 向量"""
    __tablename__ = "documents"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    file_id: uuid.UUID = Field(foreign_key="files.id", index=True)
    chunk_index: int = Field()
    content: str = Field(sa_column=Column(Text, nullable=False))      # 长文本存储
    
    # 使用 pgvector 的 Vector 类型定义向量字段
    embedding: list[float] = Field(
        sa_column=Column(Vector(EMBEDDING_DIMENSION), nullable=False)
    )
    
    # 元数据，如 pdf 中的页码等，使用 PostgreSQL 的 JSONB 格式以提高过滤效率
    meta_info: dict = Field(default_factory=dict, sa_column=Column(JSONB))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    file: Optional[File] = Relationship(back_populates="documents")
