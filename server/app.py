from typing import Optional
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
import json
from contextlib import asynccontextmanager
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph
from graph import create_agent_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSqliteSaver.from_conn_string("chatbot.db") as checkpointer:
        app.state.agent_graph: CompiledStateGraph = create_agent_graph(
            checkpointer)
        app.state.checkpointer = checkpointer
        yield

app = FastAPI(lifespan=lifespan)

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

        events = app.state.agent_graph.astream_events(
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

        events = app.state.agent_graph.astream_events(
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


@app.get("/get-all")
async def get_chats():
    config = {
        "configurable": {
            "thread_id": "4647cc2b-3e7a-44db-9de2-59f49c02b889"
        }
    }
    agent_graph: CompiledStateGraph = app.state.agent_graph
    data = await agent_graph.aget_state(config=config)

    print(data.values['messages'])

    response = {
        "messages": []
    }

    for message in data.values["messages"]:

        if (isinstance(message, HumanMessage) or isinstance(message, AIMessage)) and message.content:
            response["messages"].append({
                "id": message.id,
                "message_type": type(message).__name__,
                "message_content": message.content
            })

    return response


@app.get("/get-threads")
async def get_threads():
    checkpointer: AsyncSqliteSaver = app.state.checkpointer

    thread_list = set()
    async for thread in checkpointer.alist(None):
        thread_list.add(thread.config["configurable"]["thread_id"])
    return {
        "thread_list": thread_list
    }
