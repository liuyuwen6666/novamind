import json
from typing import Annotated, List, Dict, Any, Optional, AsyncGenerator
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.postgres import PostgresSaver

from app.core.config import get_settings
from app.core.logging import get_logger
from app.prompts.system import build_rag_system_prompt, NO_CONTEXT_SYSTEM_PROMPT
from app.tools.registry import tool_registry
from app.services.rag_service import retrieve_kb
from app.db.connection import get_connection_pool

logger = get_logger(__name__)
settings = get_settings()

# 1. 初始化 ChatOpenAI 客户端
llm = ChatOpenAI(
    openai_api_key=settings.LLM_API_KEY,
    openai_api_base=settings.LLM_BASE_URL,
    model_name=settings.LLM_MODEL,
    temperature=0.7,
    streaming=True,
)


# 2. 定义智能体图的状态 State
class AgentState(TypedDict):
    # 消息记录列表（由 add_messages 自动更新与合并）
    messages: Annotated[List[BaseMessage], add_messages]
    # RAG 检索上下文
    context: str
    # 文档来源列表（用于最终展示给前端）
    sources: List[Dict[str, Any]]
    # 是否启用 RAG
    use_rag: bool
    # 多租户/工作区隔离 ID
    workspace_id: Optional[str]


# 3. 定义图的各个节点逻辑

async def retrieve_node(state: AgentState) -> Dict[str, Any]:
    """RAG 知识库检索节点"""
    if not state.get("use_rag"):
        return {"context": "", "sources": []}

    messages = state.get("messages", [])
    if not messages:
        return {"context": "", "sources": []}

    # 提取最后一条 Human 消息作为 RAG 检索词
    user_query = ""
    for msg in reversed(messages):
        if msg.type == "human":
            user_query = msg.content
            break

    if not user_query:
        return {"context": "", "sources": []}

    try:
        # 调用 RAG 服务进行检索
        chunks = await retrieve_kb(user_query, workspace_id=state.get("workspace_id"))
        
        context_parts = []
        sources_list = []
        for idx, chunk in enumerate(chunks):
            context_parts.append(f"【文档片段 {idx + 1}】\n{chunk['content']}\n")
            sources_list.append({
                "file_name": chunk["file_name"] or "未知文档",
                "chunk_index": chunk["chunk_index"],
                "score": round(chunk["score"], 4) if chunk["score"] is not None else 0.0
            })
            
        context = "\n".join(context_parts)
        logger.info(f"RAG Node matched {len(sources_list)} chunks.")
        return {"context": context, "sources": sources_list}
    except Exception as e:
        logger.error(f"RAG retrieve node failed: {e}")
        return {"context": "", "sources": []}


async def call_model_node(state: AgentState) -> Dict[str, Any]:
    """LLM 决策节点"""
    # 获取全部注册的工具，并绑定至 LLM
    tools = tool_registry.list_tools()
    llm_with_tools = llm.bind_tools(tools)

    # 动态组装最新的 System Message，以防止 system prompt 在 add_messages 下无限堆叠
    context = state.get("context", "")
    if state.get("use_rag") and context:
        system_prompt = build_rag_system_prompt(context)
    else:
        system_prompt = NO_CONTEXT_SYSTEM_PROMPT
        
    sys_msg = SystemMessage(content=system_prompt)

    # 提取历史消息，并做最大轮数截断防 Token 溢出
    history = state.get("messages", [])
    max_msgs = settings.MAX_MEMORY_MESSAGES
    if len(history) > max_msgs:
        history = history[-max_msgs:]
        # 确保第一条不是 assistant 消息
        while history and history[0].type != "human":
            history = history[1:]

    model_input = [sys_msg] + history
    logger.info("Calling LLM model node...")
    
    # 异步调用模型
    response = await llm_with_tools.ainvoke(model_input)
    return {"messages": [response]}


# 4. 构建并编译 LangGraph 状态图
workflow = StateGraph(AgentState)

# 注册节点
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("agent", call_model_node)
# 注入内置的工具执行节点
workflow.add_node("tools", ToolNode(tool_registry.list_tools()))

# 配置控制流边
workflow.add_edge(START, "retrieve")
workflow.add_edge("retrieve", "agent")

# 添加条件边：依据模型决定是否进行 Tool 调用 (使用 prebuilt 的 tools_condition)
workflow.add_conditional_edges("agent", tools_condition, path_map={"tools": "tools", END: END})
workflow.add_edge("tools", "agent")

# 初始化 Postgres 持久化存储器并编译
pool = get_connection_pool()
memory_saver = PostgresSaver(pool)

_saver_initialized = False


async def get_agent_graph():
    """获取编译好的 LangGraph 状态机实例，确保已调用 setup() 初始化数据库表"""
    global _saver_initialized
    if not _saver_initialized:
        logger.info("Running PostgresSaver setup for LangGraph checkpoints...")
        await memory_saver.setup()
        _saver_initialized = True
    return workflow.compile(checkpointer=memory_saver)


# 5. 定义流式运行入口供 API 调用

async def run_agent_stream(
    session_id: str,
    message: str,
    use_rag: bool = True,
    workspace_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    运行 Agent 并利用 standard langchain astream_events 流式发送结果（SSE 格式）
    """
    graph = await get_agent_graph()
    
    # 准备 LangGraph 会话线程配置
    config = {"configurable": {"thread_id": session_id}}
    
    # 构造状态输入
    state_input = {
        "messages": [HumanMessage(content=message)],
        "use_rag": use_rag,
        "workspace_id": workspace_id
    }
    
    # 我们先拉取一次最新的状态，以获取检索源 (因为 retrieve 节点输出在 LLM 输出前)
    # 为了能将 sources 回传，我们声明一个局部变量暂存检索源
    sources_data = []

    logger.info(f"Starting Agent execution for thread_id={session_id}")
    
    # 使用 astream_events 流式监听各类执行事件
    async for event in graph.astream_events(state_input, config, version="v1"):
        kind = event["event"]
        name = event["name"]
        
        # 1. 拦截 RAG 检索结果
        if kind == "on_chain_end" and name == "retrieve":
            outputs = event["data"].get("output", {})
            sources_data = outputs.get("sources", [])
            
        # 2. 拦截 LLM 流式 Token
        elif kind == "on_chat_model_stream" and name == "ChatOpenAI":
            chunk = event["data"].get("chunk")
            if chunk and chunk.content:
                yield f"data: {json.dumps({'content': chunk.content})}\n\n"
                
        # 3. 拦截工具调用启动
        elif kind == "on_tool_start":
            tool_input = event["data"].get("input", {})
            start_md = f"\n\n> 🔧 **正在调用系统工具**：`{name}`\n"
            if tool_input:
                args_str = json.dumps(tool_input, ensure_ascii=False)
                start_md += f"> 📥 **输入参数**：`{args_str}`\n"
            yield f"data: {json.dumps({'content': start_md})}\n\n"
            
        # 4. 拦截工具调用结束
        elif kind == "on_tool_end":
            tool_output = event["data"].get("output")
            result_json_str = (
                json.dumps(tool_output, ensure_ascii=False, indent=2)
                if not isinstance(tool_output, (str, int, float, bool))
                else str(tool_output)
            )
            formatted_result = "\n".join(f"> {line}" for line in result_json_str.split("\n"))
            result_md = (
                f"> 📤 **工具返回结果**：\n"
                f"> ```json\n"
                f"{formatted_result}\n"
                f"> ```\n\n"
            )
            yield f"data: {json.dumps({'content': result_md})}\n\n"

    # 如果有 RAG 检索来源，流末尾推送 sources 结构
    if use_rag and sources_data:
        yield f"data: {json.dumps({'sources': sources_data})}\n\n"

    yield "data: [DONE]\n\n"
