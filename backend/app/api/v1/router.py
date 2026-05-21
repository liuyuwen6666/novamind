from fastapi import APIRouter

from app.api.v1.endpoints import chat, files

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(chat.router)
api_router.include_router(files.router)
