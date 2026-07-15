from sqlmodel import create_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings

settings = get_settings()

# 使用 create_async_engine 创建异步引擎
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# 绑定异步 Session 生成器
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db():
    """FastAPI 依赖注入 DB Session 生成器"""
    async with async_session() as session:
        yield session
