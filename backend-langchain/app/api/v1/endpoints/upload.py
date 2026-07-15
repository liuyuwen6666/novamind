from fastapi import APIRouter, UploadFile, File as FastAPIFile, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.db.session import get_db
from app.services.file_service import FileService
from app.services.embedding_service import VolcEngineEmbeddings, EmbeddingService
from app.schemas.schemas import FileUploadResponse

router = APIRouter()

@router.post("", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = FastAPIFile(...),
    workspace_id: str = "default_workspace",
    db: AsyncSession = Depends(get_db)
):
    """上传 PDF 文档，解析并将其写入向量数据库"""
    file_content = await file.read()
    file_service = FileService()
    
    # 初始化向量包装器
    embedding_service = EmbeddingService()
    embeddings_wrapper = VolcEngineEmbeddings(embedding_service)
    
    # 调用服务层批量处理并写入向量库
    db_file = await file_service.save_file_chunks(
        db=db,
        file_name=file.filename,
        file_content=file_content,
        embeddings_wrapper=embeddings_wrapper,
        workspace_id=workspace_id
    )
    return db_file
