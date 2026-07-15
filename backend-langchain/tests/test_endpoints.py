import pytest
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
