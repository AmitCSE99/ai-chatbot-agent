from datetime import datetime
from typing import TypedDict, Annotated
from langchain_core.tools import tool
from langgraph.graph import add_messages, StateGraph, END
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_community.tools import TavilySearchResults
from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

model = ChatOpenAI(model="gpt-4o")


@tool
def get_current_datetime() -> str:
    """Returns the current date and time in a human-readable format."""
    now = datetime.now()
    return now.strftime("%A, %B %d, %Y %H:%M:%S")


search_tool = TavilySearchResults(max_results=4)

tools = [search_tool, get_current_datetime]
memory = MemorySaver()


class State(TypedDict):
    messages: Annotated[list, add_messages]


llm_with_tools = model.bind_tools(tools)


async def model(state: State):

    system_prompt = """
    You are a helpful AI chatbot that answers user's queries intelligently using avaliable tools wherever necessary. Always remember you need to give latest information untill a specific date or event is mentioned. Use proper tools to fetch latest information.

    The avaliable tools:
    - get_current_datetime: Helps you to get the current date and time. It is particularly useful for finding latest information from web
    - tavily_search_results_json: Helps to perform web search and extract out latest information from the web. Make sure you find the latest information from the web according to the latest date untill a specific date is mentioned.

    IMPORTANT: If you are providing an answer in a markdown format, make sure it is properly formatted. Also if the answer is in points form then you must format in such a way where each point starts from a new line in markdown
    """

    messages = [SystemMessage(content=system_prompt)] + state["messages"]

    result = await llm_with_tools.ainvoke(messages)

    return {
        "messages": [result]
    }


async def tools_router(state: State):
    last_message = state["messages"][-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_node"
    else:
        return END


async def tool_node(state: State):
    """Custom tool node that handles tool calls from the LLM"""

    tool_calls = state["messages"][-1].tool_calls

    tool_messages = []

    for tool_call in tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]

        if tool_name == "tavily_search_results_json":

            search_results = await search_tool.ainvoke(tool_args)

            tool_message = ToolMessage(
                content=str(search_results),
                tool_call_id=tool_id,
                name=tool_name
            )

            tool_messages.append(tool_message)

        if tool_name == "get_current_datetime":
            current_date_time = await get_current_datetime.ainvoke(tool_args)

            tool_message = ToolMessage(
                content=str(current_date_time),
                tool_call_id=tool_id,
                name=tool_name
            )

            tool_messages.append(tool_message)

    return {
        "messages": tool_messages
    }

graph_builder = StateGraph(State)

graph_builder.add_node("model", model)
graph_builder.add_node("tool_node", tool_node)

graph_builder.set_entry_point("model")

graph_builder.add_conditional_edges("model", tools_router)

graph_builder.add_edge("tool_node", "model")

agent_graph = graph_builder.compile(checkpointer=memory)
