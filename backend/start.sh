#!/bin/bash
# ============================================================
# NovaMind Backend 启动脚本
# 职责：等待 PostgreSQL 就绪 → 初始化 DB → 启动 uvicorn
# ============================================================
set -e

echo "========================================"
echo "  NovaMind Backend Starting..."
echo "========================================"

# ── 等待 PostgreSQL 就绪 ──────────────────────────────────
echo "[1/3] 等待 PostgreSQL 就绪..."

MAX_RETRIES=30
COUNT=0

until python -c "
import asyncio, asyncpg, os, sys

async def check():
    url = os.environ.get('DATABASE_URL', '')
    # asyncpg 使用 postgresql:// 而不是 postgresql+asyncpg://
    url = url.replace('postgresql+asyncpg://', 'postgresql://')
    try:
        conn = await asyncpg.connect(url, timeout=5)
        await conn.close()
        print('PostgreSQL 已就绪!')
    except Exception as e:
        print(f'PostgreSQL 未就绪: {e}')
        sys.exit(1)

asyncio.run(check())
" 2>/dev/null; do
    COUNT=$((COUNT + 1))
    if [ $COUNT -ge $MAX_RETRIES ]; then
        echo "PostgreSQL 连接超时，退出"
        exit 1
    fi
    echo "  等待中... ($COUNT/$MAX_RETRIES)"
    sleep 2
done

# ── 数据库初始化 ─────────────────────────────────────────
echo "[2/3] 初始化数据库（创建表 + pgvector 扩展）..."

python -c "
import asyncio
import sys

async def init():
    try:
        from app.db.database import init_db
        await init_db()
        print('数据库初始化完成!')
    except Exception as e:
        print(f'数据库初始化失败: {e}')
        sys.exit(1)

asyncio.run(init())
"

# ── 启动 FastAPI ─────────────────────────────────────────
echo "[3/3] 启动 FastAPI 服务..."
echo "  访问地址: http://0.0.0.0:8000"
echo "  API 文档: http://0.0.0.0:8000/docs"
echo "========================================"

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 1 \
    --log-level info
