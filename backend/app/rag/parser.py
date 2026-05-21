import io
import uuid

import fitz  # PyMuPDF

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.models import DocumentChunk

logger = get_logger(__name__)
settings = get_settings()


def parse_pdf(data: bytes) -> str:
    """PDF → 纯文本"""
    with fitz.open(stream=io.BytesIO(data), filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)


def split_text(text: str, chunk_size: int = None, chunk_overlap: int = None) -> list[str]:
    """滑动窗口分块"""
    size = chunk_size or settings.CHUNK_SIZE
    overlap = chunk_overlap or settings.CHUNK_OVERLAP
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return [c.strip() for c in chunks if c.strip()]


def build_chunks(text: str, file_id: uuid.UUID) -> list[DocumentChunk]:
    """文本 → DocumentChunk 列表（未含向量）"""
    raw_chunks = split_text(text)
    chunks = [
        DocumentChunk(
            file_id=file_id,
            chunk_index=i,
            content=chunk,
            meta={"chunk_index": i},
        )
        for i, chunk in enumerate(raw_chunks)
    ]
    logger.info("Built %d chunks for file %s", len(chunks), file_id)
    return chunks
