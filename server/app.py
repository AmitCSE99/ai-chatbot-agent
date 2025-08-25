from datetime import datetime
from typing import Optional, TypedDict, Annotated
from langchain_core.tools import tool
from langgraph.graph import add_messages, StateGraph, END
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langchain_community.tools import TavilySearchResults
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
import json

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

graph = graph_builder.compile(checkpointer=memory)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Type"]
)


async def serialise_ai_message_chunk(chunk):
    if isinstance(chunk, AIMessageChunk):
        return chunk.content
    else:
        raise TypeError(
            f"Object of type {type(chunk).__name__} is not currently formatted for serialisation"
        )


async def generate_chat_responses(message: str, checkpoint_id: Optional[str] = None):
    is_new_conversion = checkpoint_id is None

    if is_new_conversion:
        new_checkpoint_id = str(uuid4())

        config = {
            "configurable": {
                "thread_id": new_checkpoint_id
            }
        }

        events = graph.astream_events(
            {
                "messages": [HumanMessage(content=message)]
            },
            config=config,
            version="v2"
        )

        yield f"data: {{\"type\": \"checkpoint\", \"checkpoint_id\": \"{new_checkpoint_id}\"}}\n\n"
    else:
        config = {
            "configurable": {
                "thread_id": checkpoint_id
            }
        }

        events = graph.astream_events(
            {
                "messages": [HumanMessage(content=message)]
            }, config=config, version="v2"
        )

    async for event in events:
        event_type = event["event"]

        if event_type == "on_chat_model_stream":
            chunk_content = await serialise_ai_message_chunk(event["data"]["chunk"])

            # Safely encode JSON
            payload = {
                "type": "content",
                "content": chunk_content
            }

            yield f"data: {json.dumps(payload)}\n\n"
        elif event_type == "on_chat_model_end":
            tool_calls = event["data"]["output"].tool_calls if hasattr(
                event["data"]["output"], "tool_calls") else []

            search_calls = [
                call for call in tool_calls if call["name"] == "tavily_search_results_json"]

            if search_calls:
                search_query = search_calls[0]["args"].get("query", "")

                safe_query = search_query.replace('"', '\\"').replace(
                    "'", "\\'").replace("\n", "\\n")
                yield f"data: {{\"type\": \"search_start\", \"query\": \"{safe_query}\"}}\n\n"
        elif event_type == "on_tool_end" and event["name"] == "tavily_search_results_json":
            output = event["data"]["output"]

            if isinstance(output, list):

                urls = []
                for item in output:
                    if isinstance(item, dict) and "url" in item:
                        urls.append(item["url"])

                urls_json = json.dumps(urls)

                yield f"data: {{\"type\": \"search_results\", \"urls\": {urls_json}}}\n\n"

    yield f"data: {{\"type\": \"end\"}}\n\n"


@app.get("/chat_stream/{message}")
async def chat_stream(message: str, checkpoint_id: Optional[str] = Query(None)):
    return StreamingResponse(
        generate_chat_responses(message, checkpoint_id),
        media_type="text/event-stream"
    )
