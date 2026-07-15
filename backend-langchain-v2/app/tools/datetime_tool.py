"""
系统当前日期和时间获取工具
符合 LangChain 标准自定义工具定义
"""
from datetime import datetime, timezone, timedelta
from langchain_core.tools import tool
from app.core.logging import get_logger

logger = get_logger(__name__)


@tool
async def get_current_datetime(timezone_offset: int = 8) -> dict:
    """获取系统当前最新的日期、时间、星期几和时区信息。
    每当需要获取当前准确日期、判断时间先后、计算时间差、计算今天是星期几、
    或者在需要回答关于“今天”、“现在”等与当前实时时间相关的问题时，必须调用此工具。
    
    Args:
        timezone_offset: 时区偏移量（小时数），例如：8 表示东八区（北京时间），0 表示 UTC，默认为 8
    """
    logger.info(f"LangChain DateTimeTool executed: timezone_offset={timezone_offset}")
    try:
        tz = timezone(timedelta(hours=timezone_offset))
    except Exception as e:
        logger.error(f"Invalid timezone offset {timezone_offset}, falling back to UTC+8: {e}")
        tz = timezone(timedelta(hours=8))
        timezone_offset = 8

    now = datetime.now(tz)
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
