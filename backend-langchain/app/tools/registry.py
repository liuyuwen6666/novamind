import inspect
from typing import Callable, Dict, Any, List
from langchain_core.tools import BaseTool, tool
from langchain_core.utils.function_calling import convert_to_openai_tool

class ToolRegistry:
    """企业级工具动态注册与分发中心"""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register_tool(self, tool_func: Callable) -> BaseTool:
        """
        注册工具。
        若传入普通 Python 函数，将利用 LangChain @tool 包装器自动转化为 BaseTool，
        包装器会自动提取函数的 docstring 和类型标注作为大模型的参数描述。
        """
        if isinstance(tool_func, BaseTool):
            t = tool_func
        else:
            t = tool(tool_func)
            
        self._tools[t.name] = t
        return t

    def get_tool(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def get_all_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def get_schemas_for_llm(self) -> List[dict]:
        """将全部已注册的工具一键转化为兼容 OpenAI/LongCat 的 API json schema"""
        return [convert_to_openai_tool(t) for t in self._tools.values()]

    async def aexecute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """异步路由与执行工具函数"""
        tool_obj = self.get_tool(name)
        if not tool_obj:
            raise ValueError(f"未注册的工具: {name}")
        # LangChain BaseTool 的 ainvoke 可以同时运行同步和异步实现的工具
        return await tool_obj.ainvoke(args)

# 工具单例中心
tool_registry = ToolRegistry()
