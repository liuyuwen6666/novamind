"""
城市经纬度查询工具
优先从本地 weather_district_id.txt 获取经纬度（无需网络），
找不到时回退到百度地图 Geocoding API。
"""
from functools import lru_cache
from pathlib import Path
from typing import Optional

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.tools.registry import BaseTool

logger = get_logger(__name__)
settings = get_settings()

_DISTRICT_FILE = Path(__file__).parent.parent.parent / "data" / "weather_district_id.csv"


@lru_cache(maxsize=1)
def _load_geocode_data() -> list[dict]:
    """从 district 文件加载经纬度数据（复用 weather_tool 中的 CSV，避免重复 IO）"""
    import csv

    records = []
    if not _DISTRICT_FILE.exists():
        logger.warning("district 文件未找到: %s", _DISTRICT_FILE)
        return records
    with open(_DISTRICT_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return records


def _find_local_geocode(city_name: str) -> Optional[dict]:
    """从本地数据中查找城市经纬度"""
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

    # 优先返回 city 级别（district_id == city_geocode 的那条）
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


class GeocodeQueryTool(BaseTool):
    name = "get_city_geocode"
    description = (
        "查询指定城市的地理经纬度坐标（WGS84 坐标系）。"
        "返回城市名称、所在省份、经度（longitude）和纬度（latitude）。"
        "适用于需要地图定位、距离计算、周边查询等场景。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "城市或区县名称，例如：北京、上海浦东、成都武侯区",
            },
        },
        "required": ["city"],
    }

    async def execute(self, city: str) -> dict:
        logger.info("GeocodeQueryTool called: city=%s", city)

        # 优先本地查询
        local = _find_local_geocode(city)
        if local:
            logger.info("本地匹配经纬度成功: city=%s, lon=%s, lat=%s", city, local["longitude"], local["latitude"])
            return {
                "status": "success",
                "data": local
            }

        # 回退到百度地图 Geocoding API
        ak = settings.WEATHER_API_KEY or settings.BAIDU_MAP_AK
        if not ak:
            return {
                "status": "error",
                "message": "未找到城市经纬度，且百度地图 AK 未配置，请检查 .env 中的 WEATHER_API_KEY"
            }

        logger.info("本地未匹配，调用百度 Geocoding API: city=%s", city)
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
                    "message": f"百度 Geocoding API 返回错误: {data.get('msg', '未知错误')}"
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
            logger.error("GeocodeQueryTool HTTP error: %s", e)
            return {
                "status": "error",
                "message": f"网络请求失败: {str(e)}"
            }
        except Exception as e:
            logger.error("GeocodeQueryTool error: %s", e)
            return {
                "status": "error",
                "message": str(e)
            }
