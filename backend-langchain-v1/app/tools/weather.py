from app.tools.registry import tool_registry

@tool_registry.register_tool
def get_current_weather(location: str, unit: str = "celsius") -> str:
    """
    获取指定城市或地区的当前实时天气信息。
    
    Args:
        location: 城市或地区的名称，例如 '北京', '上海', 'Beijing'
        unit: 温度单位，'celsius' (摄氏度) 或 'fahrenheit' (华氏度)
    """
    import random
    # 模拟天气 API 返回数据
    temp = random.randint(15, 32)
    return f"{location}当前天气多云转晴，气温 {temp} 摄氏度，微风，环境舒适。"
