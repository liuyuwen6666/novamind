from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateFileError
from app.core.logging import get_logger
from app.db.database import get_db
from app.models.models import DocumentChunk
from app.rag.parser import build_chunks, parse_pdf
from app.repositories.document_repository import DocumentRepository
from app.repositories.file_repository import FileRepository
from app.schemas.schemas import FileListItem, FileUploadResponse
from app.services.embedding_service import EmbeddingService
from app.utils.hashing import compute_md5
from app.utils.response import ok

logger = get_logger(__name__)
router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload", response_model=dict, summary="上传 PDF 文件")
async def upload_file(
    file: UploadFile = File(...),
    workspace_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="当前仅支持 PDF 文件")

    data = await file.read()
    file_hash = compute_md5(data)
    file_repo = FileRepository(db)

    # 重复文件检测
    existing = await file_repo.get_by_hash(file_hash)
    if existing:
        raise HTTPException(status_code=409, detail=f"文件已存在（hash={file_hash}）")

    record = await file_repo.create(file.filename, file_hash, len(data), workspace_id)

    # 异步处理：解析 → 分块 → Embedding → 入库
    try:
        await file_repo.update_status(record.id, "processing")
        text = parse_pdf(data)
        chunks = build_chunks(text, record.id)

        embedding_svc = EmbeddingService()
        texts = [c.content for c in chunks]
        embeddings = await embedding_svc.embed_texts(texts)
        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb

        doc_repo = DocumentRepository(db)
        await doc_repo.bulk_insert(chunks)
        await file_repo.update_status(record.id, "done")
    except Exception as e:
        logger.error("File processing failed: %s", e)
        await file_repo.update_status(record.id, "failed")
        raise HTTPException(status_code=500, detail=f"文件处理失败: {e}")

    return ok(FileUploadResponse(
        id=record.id,
        file_name=record.file_name,
        file_hash=record.file_hash,
        status="done",
        created_at=record.created_at,
    ).model_dump(mode="json"), "文件上传成功")


@router.get("/", response_model=dict, summary="文件列表")
async def list_files(workspace_id: str | None = None, db: AsyncSession = Depends(get_db)) -> dict:
    file_repo = FileRepository(db)
    records = await file_repo.list_all(workspace_id)
    items = [
        FileListItem(
            id=r.id,
            file_name=r.file_name,
            file_size=r.file_size,
            status=r.status,
            created_at=r.created_at,
        )
        for r in records
    ]
    return ok([i.model_dump(mode="json") for i in items])


@router.delete("/{file_id}", response_model=dict, summary="删除文件")
async def delete_file(file_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    import uuid as _uuid
    file_repo = FileRepository(db)
    await file_repo.delete(_uuid.UUID(file_id))
    return ok(message="文件已删除")
