import contextlib
from typing import AsyncGenerator
from psycopg_pool import AsyncConnectionPool
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# 全局的 psycopg3 异步连接池，专门供 LangGraph PostgresSaver / 裸 SQL 驱动使用
# 优点：高并发直连、低开销，完全契合 langgraph-checkpoint-postgres 对原生 psycopg 的需求
_connection_pool: AsyncConnectionPool = None


def get_connection_pool() -> AsyncConnectionPool:
    """获取全局的 psycopg 异步连接池实例"""
    global _connection_pool
    if _connection_pool is None:
        logger.info("Initializing Postgres connection pool...")
        # 组装 psycopg 兼容的连接字符串 (同步/标准 postgresql:// 格式)
        connection_string = settings.DATABASE_URL_SYNC
        
        # 构造连接池
        _connection_pool = AsyncConnectionPool(
            conninfo=connection_string,
            min_size=2,
            max_size=20,
            open=False, # 延迟开启，在 lifespan 中启动
        )
    return _connection_pool


@contextlib.asynccontextmanager
async def get_db_connection() -> AsyncGenerator:
    """从连接池中借用一个异步数据库连接的上下文管理器"""
    pool = get_connection_pool()
    async with pool.connection() as conn:
        yield conn


async def init_database() -> None:
    """数据库初始化函数：确保 pgvector 扩展已被启用，并准备 LangGraph checkpointer 表"""
    logger.info("Verifying PostgreSQL database extensions...")
    pool = get_connection_pool()
    
    # 确保连接池已启动
    await pool.open()
    
    # 检查并开启 vector 扩展
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await conn.commit()
    logger.info("PostgreSQL pgvector extension verified.")
