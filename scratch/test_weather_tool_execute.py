import os
import sys

# 获取当前脚本所在目录并计算项目根目录及 backend 路径
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")

sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, PROJECT_ROOT)

import asyncio
import json
from backend.app.tools.weather_tool import WeatherTool

async def main():
    tool = WeatherTool()
    print("Tool properties:")
    print("Name:", tool.name)
    print("Description:", tool.description)
    print("Parameters schema:", json.dumps(tool.parameters, indent=2, ensure_ascii=False))
    
    print("\nExecuting tool for Beijing...")
    result = await tool.execute(city="北京")
    print("Execution Status:", result.get("status"))
    if result.get("status") == "success":
        data = result.get("data", {})
        print("\nNow temperature:", data.get("now", {}).get("temperature"), "°C")
        print("Now weather:", data.get("now", {}).get("weather"))
        print("Forecasts count:", len(data.get("forecasts", [])))
        print("Forecast Hours count:", len(data.get("forecast_hours", [])))
        if data.get("forecast_hours"):
            print("First hourly item:", data["forecast_hours"][0])
        if data.get("forecasts"):
            print("First forecast item:", data["forecasts"][0])
    else:
        print("Error message:", result.get("message"))

if __name__ == "__main__":
    asyncio.run(main())
