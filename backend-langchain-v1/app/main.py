from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlmodel import SQLModel, text

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import NovaMindException
from app.core.logging import get_logger, setup_logging
from app.db.session import engine

settings = get_settings()
setup_logging(debug=settings.DEBUG)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("NovaMind-LangChain API starting up...")
    
    # 自动创建 PostgreSQL 表并确保 pgvector 扩展已开启
    async with engine.begin() as conn:
        logger.info("Ensuring pgvector extension is enabled...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        logger.info("Creating SQLModel database tables...")
        await conn.run_sync(SQLModel.metadata.create_all)
        
    yield
    logger.info("NovaMind-LangChain API shutting down.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# 挂载 CORS 跨域请求中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局业务异常处理器
@app.exception_handler(NovaMindException)
async def novamind_exception_handler(request: Request, exc: NovaMindException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.message, "data": None},
    )

# 全局未捕获异常拦截器
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误，请联系管理员", "data": None},
    )

# 挂载汇总的 API 路由，保留 /api/v1 前缀
app.include_router(api_router, prefix="/api/v1")

@app.get("/health", tags=["Health"])
async def health():
    """提供应用健康状态与版本检测"""
    return {"status": "ok", "version": settings.APP_VERSION}
