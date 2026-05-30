import sys
sys.path.insert(0, "e:/ai_study/06 NovaMind/backend")

import asyncio
import json
from app.services.llm_service import LLMService
from app.schemas.schemas import ChatMessage

async def main():
    llm = LLMService()
    
    # Simulate first round
    messages = [
        ChatMessage(role="system", content="涉及时间日期的问题，你必须使用 get_current_datetime 工具获取时间日期"),
        ChatMessage(role="user", content="现在的日期是多少？")
    ]
    
    print("--- ROUND 1 ---")
    tool_call_info = None
    async for chunk_str in llm.chat(messages, stream=True, tools=[
        {
            "type": "function",
            "function": {
                "name": "get_current_datetime",
                "description": "获取系统当前最新的日期、时间、星期几和时区信息。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timezone_offset": {"type": "integer", "default": 8}
                    }
                }
            }
        }
    ]):
        print("Round 1 Chunk:", chunk_str)
        data = json.loads(chunk_str)
        delta = data.get("choices", [{}])[0].get("delta", {})
        if delta.get("tool_calls"):
            tool_call_info = delta["tool_calls"][0]

    if not tool_call_info:
        print("No tool call triggered!")
        return

    # Simulate second round
    print("\n--- ROUND 2 ---")
    assistant_msg = ChatMessage(role="assistant", content="我来为您获取当前的日期和时间信息。")
    tool_msg = ChatMessage(role="tool", content=json.dumps({
        "status": "success",
        "data": {
            "datetime": "2026-05-30 10:18:45",
            "date": "2026-05-30",
            "time": "10:18:45",
            "timezone": "UTC+8",
            "weekday": "星期六",
            "timestamp": 1780107525
        }
    }), tool_call_id=tool_call_info["id"])

    second_messages = messages + [assistant_msg, tool_msg]
    
    try:
        async for chunk_str in llm.chat(second_messages, stream=True, tools=None):
            print("Round 2 Chunk:", chunk_str)
    except Exception as e:
        print("Error during Round 2 chat:", e)

if __name__ == "__main__":
    asyncio.run(main())
