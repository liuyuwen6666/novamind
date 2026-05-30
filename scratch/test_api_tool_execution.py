import asyncio
import httpx
import json
import sys

url = "http://localhost:8000/api/v1/chat/"

payload = {
    "messages": [
        {"role": "user", "content": "现在的日期是多少？"}
    ],
    "use_rag": False,
    "stream": True
}

async def main():
    try:
        # Force stdout encoding to UTF-8
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            async with client.stream("POST", url, json=payload) as resp:
                print("Status code:", resp.status_code)
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            content = data.get("content", "")
                            # Print by encoding to UTF-8 and writing directly to buffer
                            sys.stdout.buffer.write(content.encode('utf-8'))
                            sys.stdout.buffer.flush()
                        except Exception as e:
                            print(f"\nError printing chunk: {e}")
                print()
    except Exception as e:
        print("\nRequest failed:", e)

if __name__ == "__main__":
    asyncio.run(main())
