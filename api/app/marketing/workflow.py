from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict, Optional, Literal
from typing import Annotated
import operator

from .nodes import (
    prepare, execute_social, execute_blog, execute_image,
    execute_research, review_pause, publish, save,
    select_template, route_after_review,
)


class WorkflowState(TypedDict):
    session_id: str
    request: str
    brand_id: str
    template: Optional[Literal["social", "blog", "image", "research"]]
    context: dict
    draft: Optional[dict]
    approved: bool
    publish_status: Optional[Literal["pending", "published", "failed", "dead_letter"]]
    usage: Annotated[dict, operator.or_]
    error: Optional[Literal["timeout", "rate_limit", "invalid", "fatal"]]
   


workflow = StateGraph(WorkflowState)

workflow.add_node("prepare",           prepare)
workflow.add_node("execute_social",    execute_social)
workflow.add_node("execute_blog",      execute_blog)
workflow.add_node("execute_image",     execute_image)
workflow.add_node("execute_research",  execute_research)
workflow.add_node("review_pause",      review_pause)
workflow.add_node("publish",           publish)
workflow.add_node("save",              save)

workflow.add_edge(START, "prepare")

workflow.add_conditional_edges("prepare", select_template, {
    "execute_social":   "execute_social",
    "execute_blog":     "execute_blog",
    "execute_image":    "execute_image",
    "execute_research": "execute_research",
    "save":             "save",
})

workflow.add_edge("execute_social",   "review_pause")
workflow.add_edge("execute_blog",     "review_pause")
workflow.add_edge("execute_image",    "review_pause")
workflow.add_edge("execute_research", "save")

workflow.add_conditional_edges("review_pause", route_after_review, {
    "publish": "publish",
    "save":    "save",
})

workflow.add_edge("publish", "save")
workflow.add_edge("save", END)

graph = workflow.compile(checkpointer=MemorySaver())