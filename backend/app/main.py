import os
import json
import asyncio
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from openai import AsyncOpenAI

from app.config import settings

# Initialize FastAPI App
app = FastAPI(
    title="Vue3-Python Chatbot API",
    description="FastAPI Backend for modern AI Chatbot with SSE streaming support",
    version="1.0.0"
)

# CORS Configuration
# Supports local development (Frontend on port 5173, backend on 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AsyncOpenAI client
# Using values configured in app/config.py
client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url
)

# Pydantic models for request validation
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    temperature: Optional[float] = 1.0
    system_prompt: Optional[str] = None

@app.get("/api/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "model": settings.model_name,
        "api_connected": True
    }

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Server-Sent Events (SSE) streaming endpoint for AI Chat completions.
    """
    # Prepend system prompt if provided
    api_messages = []
    if request.system_prompt:
        api_messages.append({
            "role": "system",
            "content": request.system_prompt
        })
        
    for msg in request.messages:
        api_messages.append({
            "role": msg.role,
            "content": msg.content
        })

    async def event_generator():
        try:
            response = await client.chat.completions.create(
                model=settings.model_name,
                messages=api_messages,
                temperature=request.temperature,
                stream=True
            )
            
            async for chunk in response:
                if len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "content") and delta.content:
                        # Standard SSE format: "data: {JSON}\n\n"
                        yield f"data: {json.dumps({'content': delta.content})}\n\n"
                        # Yield control to prevent event loop blocking
                        await asyncio.sleep(0.001)
                        
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            # Send error details via SSE stream before ending
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering in Nginx
        }
    )

# Serve Frontend Static files in Production
# Mount static files after API routes so it doesn't intercept API calls.
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
static_dir = os.path.join(current_dir, "static")

if os.path.exists(static_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(static_dir, "assets")), name="assets")
    
    @app.get("/")
    async def serve_home():
        return FileResponse(os.path.join(static_dir, "index.html"))
        
    @app.get("/{catchall:path}")
    async def serve_spa(catchall: str):
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"detail": "Not Found"}
