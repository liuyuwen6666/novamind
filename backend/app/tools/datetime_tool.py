"""
系统当前日期和时间获取工具
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.logging import get_logger
from app.tools.registry import BaseTool

logger = get_logger(__name__)


class DateTimeTool(BaseTool):
    name = "get_current_datetime"
    description = (
        "获取系统当前最新的日期、时间、星期几和时区信息。"
        "每当需要获取当前准确日期、判断时间先后、计算时间差、计算今天是星期几、"
        "回答关于‘今天’、‘现在’等与实时时间相关的问题时，必须首先调用此工具获取准确时间。"
    )
    parameters = {
        "type": "object",
        "properties": {
            "timezone_offset": {
                "type": "integer",
                "description": "时区偏移量（小时数），例如：8 表示东八区（北京时间），0 表示 UTC，-5 表示东部标准时间，默认为 8",
                "default": 8,
            }
        },
    }

    async def execute(self, timezone_offset: int = 8) -> dict:
        logger.info("DateTimeTool called with timezone_offset=%d", timezone_offset)
        try:
            tz = timezone(timedelta(hours=timezone_offset))
        except Exception as e:
            logger.error("Invalid timezone offset %s, falling back to UTC+8. Error: %s", timezone_offset, e)
            tz = timezone(timedelta(hours=8))
            timezone_offset = 8

        now = datetime.now(tz)
        
        # 中文星期
        weekdays_cn = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        weekday_cn = weekdays_cn[now.weekday()]
        
        return {
            "status": "success",
            "data": {
                "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                "date": now.strftime("%Y-%m-%d"),
                "time": now.strftime("%H:%M:%S"),
                "timezone": f"UTC{'+' if timezone_offset >= 0 else ''}{timezone_offset}",
                "weekday": weekday_cn,
                "timestamp": int(now.timestamp()),
            }
        }
