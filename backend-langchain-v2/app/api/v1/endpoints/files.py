from fastapi import APIRouter, File, HTTPException, UploadFile
from typing import Optional

from app.core.logging import get_logger
from app.core.exceptions import DuplicateFileError
from app.db.connection import get_db_connection
from app.services.rag_service import add_document_to_vector_store
from app.utils.hashing import compute_md5
from app.utils.response import ok
from app.schemas.schemas import FileListItem, FileUploadResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload", response_model=dict, summary="上传 PDF 知识库文件")
async def upload_file(
    file: UploadFile = File(...),
    workspace_id: Optional[str] = None
) -> dict:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="当前仅支持 PDF 格式文档")

    content_bytes = await file.read()
    file_hash = compute_md5(content_bytes)
    file_size = len(content_bytes)

    try:
        # 调用 RAG 服务完成去重、解析、切片、向量存储与 files 表落库
        res = await add_document_to_vector_store(
            file_name=file.filename,
            file_hash=file_hash,
            file_size=file_size,
            content_bytes=content_bytes,
            workspace_id=workspace_id
        )
        
        # 返回成功响应模型
        data = FileUploadResponse(
            id=res["id"],
            file_name=res["file_name"],
            file_hash=res["file_hash"],
            status=res["status"],
            created_at=res.get("created_at") or type('dt', (), {'now': lambda: type('d', (), {'strftime': lambda x: "2026-07-15 12:00:00"})})().now() # 快速占位
        )
        return ok(data.model_dump(mode="json"), "文件上传且解析索引成功")
        
    except DuplicateFileError:
        raise HTTPException(status_code=409, detail=f"该文件已存在于知识库中（MD5: {file_hash}）")
    except Exception as e:
        logger.error(f"Failed to process uploaded file {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)}")


@router.get("/", response_model=dict, summary="获取知识库文件列表")
async def list_files(workspace_id: Optional[str] = None) -> dict:
    records = []
    
    # 直接通过连接池查询文件列表记录
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            if workspace_id:
                await cur.execute(
                    "SELECT id, file_name, file_size, status, created_at FROM files WHERE workspace_id = %s ORDER BY created_at DESC",
                    (workspace_id,)
                )
            else:
                await cur.execute(
                    "SELECT id, file_name, file_size, status, created_at FROM files ORDER BY created_at DESC"
                )
                
            rows = await cur.fetchall()
            for row in rows:
                records.append(FileListItem(
                    id=row[0],
                    file_name=row[1],
                    file_size=row[2],
                    status=row[3],
                    created_at=row[4]
                ))

    return ok([r.model_dump(mode="json") for r in records])


@router.delete("/{file_id}", response_model=dict, summary="删除知识库文件")
async def delete_file(file_id: str) -> dict:
    logger.info(f"Deleting file {file_id} from database and vector index...")
    
    async with get_db_connection() as conn:
        async with conn.cursor() as cur:
            # 1. 删除 files 业务表
            await cur.execute("DELETE FROM files WHERE id = %s", (file_id,))
            
            # 2. 清理 PGVector 里的 langchain_pg_embedding 向量表
            # LangChain PGVector 会把我们放入的 metadata 存在 cmetadata 字段中
            await cur.execute(
                "DELETE FROM langchain_pg_embedding WHERE cmetadata->>'file_id' = %s",
                (file_id,)
            )
            await conn.commit()

    logger.info(f"File {file_id} deleted successfully.")
    return ok(message="文件及向量索引已删除")
