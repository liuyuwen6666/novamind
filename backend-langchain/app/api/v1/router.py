from fastapi import APIRouter
from app.api.v1.endpoints import chat, upload

api_router = APIRouter()

# 聚合注册 endpoints
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(upload.router, prefix="/upload", tags=["Upload"])
