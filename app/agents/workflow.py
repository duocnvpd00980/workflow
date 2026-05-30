from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.core.config import get_settings


settings = get_settings()

def get_llm():
    if settings.is_dev:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
        )
    else:
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
        )
    
settings = get_settings()

SYSTEM_PROMPT = "Bạn là AI assistant thông minh và hữu ích. Trả lời rõ ràng, súc tích."

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

def get_llm():
    return ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        google_api_key=settings.google_api_key,
    )

def agent_node(state: AgentState) -> dict:
    llm = get_llm()
    msgs = [SystemMessage(content=SYSTEM_PROMPT)] + list(state["messages"])
    response = llm.invoke(msgs)
    return {"messages": [response]}

def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.set_entry_point("agent")
    graph.add_edge("agent", END)
    return graph

async def run_agent(user_message: str, history: list[dict], session_id: str) -> str:
    msgs: list[BaseMessage] = []
    for m in history:
        if m["role"] == "user":
            msgs.append(HumanMessage(content=m["content"]))
        elif m["role"] == "assistant":
            msgs.append(AIMessage(content=m["content"]))
    msgs.append(HumanMessage(content=user_message))

    async with AsyncSqliteSaver.from_conn_string("./chat_checkpoints.db") as checkpointer:
        app = build_graph().compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": session_id}}
        result = await app.ainvoke({"messages": msgs}, config=config)

    return result["messages"][-1].content
