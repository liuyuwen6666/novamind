import pytest
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["status"] == "ok"
    assert "version" in res_json

def test_chat_endpoint_schema():
    # 测试 chat 接口的数据结构验证失败情况（入参缺失）
    response = client.post("/api/v1/chat", json={})
    assert response.status_code == 422 # Pydantic 参数校验失败

def test_chat_agent_flow():
    # 测试普通的聊天模式和工具映射
    # 构造请求体，包含对话历史
    payload = {
        "messages": [
            {"role": "user", "content": "北京天气怎么样？"}
        ],
        "workspace_id": "test_workspace",
        "stream": True,
        "use_rag": False
    }
    
    # 运行测试，以 streaming 方式发送请求
    with client.stream("POST", "/api/v1/chat", json=payload) as response:
        assert response.status_code == 200
        # 收集 SSE 字节流
        content = ""
        for line in response.iter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    data_json = json.loads(data_str)
                    delta = data_json["choices"][0]["delta"].get("content", "")
                    content += delta
                except Exception:
                    pass
        
        # 验证是否触发了天气工具并返回
        assert "北京" in content
        assert "天气" in content
