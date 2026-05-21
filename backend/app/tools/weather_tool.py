import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.tools.registry import BaseTool

logger = get_logger(__name__)
settings = get_settings()


class WeatherTool(BaseTool):
    name = "get_weather"
    description = "获取指定城市的当前天气信息"
    parameters = {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名称，例如：北京"},
        },
        "required": ["city"],
    }

    async def execute(self, city: str) -> dict:
        logger.info("WeatherTool called: city=%s", city)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    "https://api.weatherapi.com/v1/current.json",
                    params={"key": settings.WEATHER_API_KEY, "q": city, "lang": "zh"},
                )
                resp.raise_for_status()
                data = resp.json()
                return {
                    "city": data["location"]["name"],
                    "temperature": data["current"]["temp_c"],
                    "condition": data["current"]["condition"]["text"],
                    "humidity": data["current"]["humidity"],
                }
        except Exception as e:
            logger.error("WeatherTool error: %s", e)
            return {"error": str(e)}
