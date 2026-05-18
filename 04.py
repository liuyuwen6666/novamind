from openai import OpenAI

client = OpenAI(
    api_key="ak_2kv4sp70L7Ey8DD7h61308un1TS62",
    base_url="https://api.longcat.chat/openai/v1"
)

messages = [

    {
        "role": "system",
        "content": "你是Python专家"
    }
]

while True:

    question = input("你：")

    # 用户消息
    messages.append({
        "role": "user",
        "content": question
    })

    response = client.chat.completions.create(
        model="longcat-flash-chat",
        messages=messages,
        temperature=1,
        stream=True
    )

    print("AI：", end="", flush=True)
    answer = ""
    for chunk in response:
        content = chunk.choices[0].delta.content
        if content:
            print(content, end="", flush=True)
            answer += content

    print()

    # AI消息
    messages.append({
        "role": "assistant",
        "content": answer
    })
