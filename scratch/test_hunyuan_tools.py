import asyncio
import httpx
import json

api_key = "sk-twKMgW0wCWk55Ugkzde1esHK8HR7yqzKBrL9tWdVTWmkaruM"
base_url = "https://tokenhub.tencentmaas.com/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

payload = {
    "model": "hunyuan-2.0-instruct-20251111",
    "messages": [
        {"role": "system", "content": "你拥有系统工具 get_current_datetime。涉及今天日期或时间的问题，你必须调用此工具。"},
        {"role": "user", "content": "今天日期是多少？"}
    ],
    "stream": False,
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "get_current_datetime",
                "description": "获取系统当前最新的日期、时间、星期几和时区信息。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "timezone_offset": {
                            "type": "integer",
                            "description": "时区偏移量（小时数），例如：8 表示东八区（北京时间）",
                            "default": 8
                        }
                    }
                }
            }
        }
    ]
}

async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(base_url, headers=headers, json=payload)
        print("Status code:", resp.status_code)
        print("Response body:")
        print(json.dumps(resp.json(), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
