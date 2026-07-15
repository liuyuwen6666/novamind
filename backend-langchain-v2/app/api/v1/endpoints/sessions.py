from fastapi import APIRouter, HTTPException
from typing import List

from app.core.logging import get_logger
from app.db.connection import get_db_connection
from app.schemas.schemas import SessionOut, MessageOut
from app.services.agent_service import get_agent_graph
from app.utils.response import ok

logger = get_logger(__name__)
router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get("/", response_model=dict, summary="获取会话列表")
async def list_sessions() -> dict:
    """直接查询 LangGraph 的 checkpoints 数据库获取所有活跃会话"""
    sessions = []
    try:
        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                # 依据 LangGraph PostgresSaver 生成的表结构，thread_id 是主键的一部分
                # 我们按创建时间先后分组排序取出所有的 thread_id
                await cur.execute(
                    """
                    SELECT thread_id, MIN(checkpoint_id) as created_at
                    FROM checkpoints
                    GROUP BY thread_id
                    ORDER BY created_at DESC
                    """
                )
                rows = await cur.fetchall()
                for row in rows:
                    thread_id = row[0]
                    # 给定一个默认会话 Title (可通过 thread_id 截断)
                    title = f"智能体对话 - {thread_id[:8]}"
                    sessions.append(SessionOut(
                        id=thread_id,
                        title=title,
                        created_at=None,
                        updated_at=None
                    ))
        return ok([s.model_dump(mode="json") for s in sessions])
    except Exception as e:
        logger.error(f"Failed to query LangGraph sessions: {e}", exc_info=True)
        return ok([]) # 降级返回空列表


@router.get("/{session_id}/messages", response_model=dict, summary="获取特定会话的历史消息")
async def get_session_messages(session_id: str) -> dict:
    """通过 LangGraph 编译图获取特定 thread_id 的所有历史状态消息"""
    try:
        graph = await get_agent_graph()
        
        # 加载特定会话线程的 State
        state = await graph.aget_state({"configurable": {"thread_id": session_id}})
        messages = state.values.get("messages", [])
        
        message_list = []
        for idx, msg in enumerate(messages):
            # 将 LangChain Message 映射为 API 格式的 role
            role = "user" if msg.type == "human" else ("assistant" if msg.type == "ai" else msg.type)
            
            # 过滤掉系统内部使用的 system 消息和工具消息本身以简化前端渲染，仅保留 user 和 assistant 的答复
            if role not in ("user", "assistant"):
                continue
                
            message_list.append(MessageOut(
                id=f"msg_{session_id}_{idx}",
                session_id=session_id,
                role=role,
                content=msg.content,
                created_at=None,
                sources=None
            ))
            
        return ok([m.model_dump(mode="json") for m in message_list])
    except Exception as e:
        logger.error(f"Failed to fetch messages for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取消息历史失败: {str(e)}")


@router.delete("/{session_id}", response_model=dict, summary="删除会话")
async def delete_session(session_id: str) -> dict:
    """物理清理特定 thread_id 的所有 LangGraph 状态"""
    logger.info(f"Deleting thread state checkpoints for thread_id={session_id}")
    try:
        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                # 清除所有的 checkpoint 数据
                await cur.execute("DELETE FROM checkpoints WHERE thread_id = %s", (session_id,))
                await cur.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (session_id,))
                await cur.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (session_id,))
                await conn.commit()
        return ok(message="会话已删除")
    except Exception as e:
        logger.error(f"Failed to delete thread state checkpoints: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除会话失败: {str(e)}")
