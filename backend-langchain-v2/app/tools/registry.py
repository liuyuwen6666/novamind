"""
工具注册表
用于集中注册和获取标准 LangChain 工具实例
"""
from typing import Dict, List
from langchain_core.tools import BaseTool

from app.tools.weather import get_weather
from app.tools.geocode import get_city_geocode
from app.tools.datetime_tool import get_current_datetime


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}
        
        # 默认注册这三个内置标准工具
        self.register(get_weather)
        self.register(get_city_geocode)
        self.register(get_current_datetime)

    def register(self, tool_func: BaseTool) -> None:
        """注册一个工具"""
        self._tools[tool_func.name] = tool_func

    def get(self, name: str) -> BaseTool:
        """获取已注册的工具"""
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        """列出所有工具"""
        return list(self._tools.values())


# 全局工具管理器实例
tool_registry = ToolRegistry()
