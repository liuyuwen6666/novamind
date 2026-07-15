"""
城市经纬度查询工具
优先从本地获取，找不到回退到百度 Geocoding API
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
def _load_geocode_data() -> list[dict]:
    """从 district 文件加载数据"""
    records = []
    if not _DISTRICT_FILE.exists():
        logger.warning(f"District map file not found: {_DISTRICT_FILE}")
        return records
    with open(_DISTRICT_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return records


def _find_local_geocode(city_name: str) -> Optional[dict]:
    """从本地模糊搜索地理位置"""
    records = _load_geocode_data()
    name = city_name.replace("市", "").replace("省", "").replace("区", "").replace("县", "").strip()

    candidates = []
    for r in records:
        city_match = r["city"].replace("市", "") == name or r["city"] == city_name
        district_match = (
            r["district"].replace("市", "").replace("区", "").replace("县", "") == name
            or r["district"] == city_name
        )
        if city_match or district_match:
            candidates.append(r)

    # 优先返回城市级别
    for r in candidates:
        if r["district_id"] == r["city_geocode"]:
            return {
                "city": city_name,
                "province": r["province"],
                "city_name": r["city"],
                "district": r["district"],
                "longitude": float(r["lon"]),
                "latitude": float(r["lat"]),
                "source": "local",
            }

    if candidates:
        r = candidates[0]
        return {
            "city": city_name,
            "province": r["province"],
            "city_name": r["city"],
            "district": r["district"],
            "longitude": float(r["lon"]),
            "latitude": float(r["lat"]),
            "source": "local",
        }

    # 模糊匹配
    for r in records:
        if name in r["city"] or name in r["district"]:
            return {
                "city": city_name,
                "province": r["province"],
                "city_name": r["city"],
                "district": r["district"],
                "longitude": float(r["lon"]),
                "latitude": float(r["lat"]),
                "source": "local_fuzzy",
            }

    return None


@tool
async def get_city_geocode(city: str) -> dict:
    """查询指定城市的地理经纬度坐标（WGS84 坐标系）。
    
    Args:
        city: 城市或区县名称，例如：北京、上海浦东、成都武侯区
    """
    logger.info(f"LangChain GeocodeTool executed: city={city}")
    local = _find_local_geocode(city)
    if local:
        logger.info(f"Local matched geocode for {city}")
        return {"status": "success", "data": local}

    ak = settings.WEATHER_API_KEY or settings.BAIDU_MAP_AK
    if not ak:
        return {
            "status": "error",
            "message": "未找到城市经纬度，且百度地图 AK 未配置，请设置 WEATHER_API_KEY"
        }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.map.baidu.com/geocoding/v3/",
                params={
                    "address": city,
                    "output": "json",
                    "ak": ak,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != 0:
            return {
                "status": "error",
                "message": f"百度 Geocoding API 错误: {data.get('msg', '未知错误')}"
            }

        loc = data["result"]["location"]
        return {
            "status": "success",
            "data": {
                "city": city,
                "province": None,
                "city_name": None,
                "district": None,
                "longitude": loc["lng"],
                "latitude": loc["lat"],
                "source": "baidu_geocoding",
            }
        }
    except httpx.HTTPError as e:
        logger.error(f"Geocode HTTP error: {e}")
        return {"status": "error", "message": f"网络请求失败: {e}"}
    except Exception as e:
        logger.error(f"Geocode error: {e}")
        return {"status": "error", "message": str(e)}
