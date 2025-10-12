from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, MessagesState
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

llm = init_chat_model(
    model=os.getenv("OPENAI_MODEL_NAME"),
    model_provider="openai",
    base_url=os.getenv("OPENAI_API_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),
)

class State(MessagesState):
    term : int = 0


def A(state: State):
    """节点A：调用一次LLM"""
    chunks = []
    for chunk in llm.stream(state["messages"]):
        delta = getattr(chunk, "content", None)
        if delta:
            # print(delta, end="", flush=True)
            chunks.append(delta)
    full_text = "".join(chunks)
    state["messages"].append(AIMessage(content=full_text))
    state["messages"].append(HumanMessage(content="详细辩论上面你的回答"))
    print(f"{state} A")
    state["term"] += 1
    return state


def B(state: State):
    """节点B：调用一次LLM"""
    chunks = []
    for chunk in llm.stream(state["messages"]):
        delta = getattr(chunk, "content", None)
        if delta:
            # print(delta, end="", flush=True)
            chunks.append(delta)
    full_text = "".join(chunks)
    state["messages"].append(AIMessage(content=full_text))
    state["term"] += 1
    return state


graph = StateGraph(State)
graph.add_node(A)
graph.add_node(B)
graph.set_entry_point("A")
graph.add_edge("A", "B")
graph.add_edge("B", "__end__")

g = graph.compile()

# === 官方推荐的流式执行方式 ===
state = State(messages=[HumanMessage(content="详细介绍一下你自己")], term=0)


async def consume():
    for chunk in g.stream(state, stream_mode="messages"):
        print(chunk[0].content, end="", flush=True)
    print()


if __name__ == "__main__":
    asyncio.run(consume())
