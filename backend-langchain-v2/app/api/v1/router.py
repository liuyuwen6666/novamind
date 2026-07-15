from fastapi import APIRouter

from app.api.v1.endpoints import chat, files, sessions

api_router = APIRouter()

# 挂载核心 API 控制器
api_router.include_router(chat.router, tags=["Chat"])
api_router.include_router(files.router, tags=["Files"])
api_router.include_router(sessions.router, tags=["Sessions"])
