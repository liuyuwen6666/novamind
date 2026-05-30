import sys
sys.path.insert(0, "e:/ai_study/06 NovaMind/backend")

import asyncio
import json
from app.tools.weather_tool import WeatherTool

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
