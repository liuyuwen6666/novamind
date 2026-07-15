import pytest
from app.tools.registry import tool_registry

def test_tool_registry_registration():
    # 1. 验证工具已经被注册进单例
    schemas = tool_registry.get_schemas_for_llm()
    
    assert isinstance(schemas, list)
    assert len(schemas) > 0
    
    # 查找是否有 get_current_weather
    weather_tool_schema = None
    for s in schemas:
        if s.get("function", {}).get("name") == "get_current_weather":
            weather_tool_schema = s
            break
            
    assert weather_tool_schema is not None
    assert "location" in weather_tool_schema["function"]["parameters"]["properties"]

@pytest.mark.asyncio
async def test_tool_execution():
    # 2. 验证异步分发执行天气工具
    res = await tool_registry.aexecute_tool("get_current_weather", {"location": "Beijing"})
    assert isinstance(res, str)
    assert "Beijing" in res
    assert "当前天气" in res
