"""
百度地图天气工具
符合 LangChain 标准自定义工具定义
"""
import csv
from functools import lru_cache
from pathlib import Path
from typing import Optional

import httpx
from langchain_core.tools import tool

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

_DISTRICT_FILE = Path(__file__).parent.parent.parent / "data" / "weather_district_id.csv"


@lru_cache(maxsize=1)
def _load_district_data() -> list[dict]:
    """加载 district_id 映射表"""
    records = []
    if not _DISTRICT_FILE.exists():
        logger.warning(f"District map file not found: {_DISTRICT_FILE}")
        return records
    with open(_DISTRICT_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    logger.info(f"Loaded {len(records)} district rows from csv")
    return records


def _find_district_id(city_name: str) -> Optional[str]:
    """模糊匹配 district_id"""
    records = _load_district_data()
    name = city_name.replace("市", "").replace("省", "").replace("区", "").replace("县", "").strip()

    # 精确匹配 city
    for r in records:
        if r["city"].replace("市", "") == name or r["city"] == city_name:
            return r["district_id"]

    # 精确匹配 district
    for r in records:
        if r["district"].replace("市", "").replace("区", "").replace("县", "") == name:
            return r["district_id"]

    # 模糊匹配 city
    for r in records:
        if name in r["city"]:
            return r["district_id"]

    # 模糊匹配 district
    for r in records:
        if name in r["district"]:
            return r["district_id"]

    return None


@tool
async def get_weather(city: str, data_type: str = "now") -> dict:
    """获取指定城市的实时天气和未来几天的天气预报信息。
    
    Args:
        city: 城市或区县名称，例如：北京、上海、广州、深圳、成都、武侯区
        data_type: 查询类型，固定为 now
    """
    logger.info(f"LangChain WeatherTool executed: city={city}, data_type={data_type}")
    district_id = _find_district_id(city)
    if not district_id:
        return {
            "status": "error",
            "message": f"未找到城市 '{city}' 对应的区域 ID，请尝试更精确的城市名称"
        }

    ak = settings.WEATHER_API_KEY or settings.BAIDU_MAP_AK
    if not ak:
        return {
            "status": "error",
            "message": "百度地图 AK 未配置，请设置 WEATHER_API_KEY 环境变量"
        }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.map.baidu.com/weather/v1/",
                params={
                    "district_id": district_id,
                    "data_type": "all",
                    "ak": ak,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != 0:
            return {
                "status": "error",
                "message": f"百度天气 API 错误: {data.get('message', '未知错误')}"
            }

        result = data.get("result", {})
        location = result.get("location", {})
        now = result.get("now", {})
        forecasts = result.get("forecasts", [])
        forecast_hours = result.get("forecast_hours", [])
        alerts = result.get("alerts", [])
        indexes = result.get("indexes", [])

        output = {
            "city": city,
            "district_id": district_id,
            "location": {
                "province": location.get("province"),
                "city": location.get("city"),
                "district": location.get("name"),
            },
            "now": None,
            "forecasts": [],
            "forecast_hours": [],
            "alerts": [],
            "life_indexes": []
        }

        if now:
            output["now"] = {
                "temperature": now.get("temp"),
                "feels_like": now.get("feels_like"),
                "humidity": now.get("rh"),
                "wind_class": now.get("wind_class"),
                "wind_dir": now.get("wind_dir"),
                "weather": now.get("text"),
                "aqi": now.get("aqi"),
                "pm25": now.get("pm25"),
                "update_time": now.get("uptime"),
            }

        if forecasts:
            output["forecasts"] = [
                {
                    "date": f.get("date"),
                    "week": f.get("week"),
                    "high": f.get("high"),
                    "low": f.get("low"),
                    "weather_day": f.get("text_day"),
                    "weather_night": f.get("text_night"),
                    "wind_day": f.get("wd_day"),
                    "wind_night": f.get("wind_night"),
                    "aqi": f.get("aqi"),
                }
                for f in forecasts
            ]

        if forecast_hours:
            output["forecast_hours"] = [
                {
                    "time": fh.get("data_time"),
                    "temperature": fh.get("temp_fc"),
                    "weather": fh.get("text"),
                    "humidity": fh.get("rh"),
                    "wind_class": fh.get("wind_class"),
                    "wind_dir": fh.get("wind_dir"),
                    "precipitation_1h": fh.get("prec_1h"),
                    "clouds": fh.get("clouds"),
                }
                for fh in forecast_hours
            ]

        if alerts:
            output["alerts"] = [
                {
                    "type": a.get("type"),
                    "level": a.get("level"),
                    "title": a.get("title"),
                }
                for a in alerts
            ]

        if indexes:
            output["life_indexes"] = [
                {
                    "name": idx.get("name"),
                    "brief": idx.get("brief"),
                    "detail": idx.get("detail"),
                }
                for idx in indexes
            ]

        return {
            "status": "success",
            "data": output
        }

    except httpx.HTTPError as e:
        logger.error(f"Weather HTTP error: {e}")
        return {"status": "error", "message": f"网络请求失败: {e}"}
    except Exception as e:
        logger.error(f"Weather error: {e}")
        return {"status": "error", "message": str(e)}
