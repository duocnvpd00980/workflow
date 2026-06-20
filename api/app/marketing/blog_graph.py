from typing import List, Annotated, TypedDict, Optional, Literal
import operator
import json
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from app.marketing.blog_node import (
    blog_prepare,
    execute_blog_content,
    execute_blog_image,
    blog_review_pause,
    blog_save,
    blog_needs_visual,
    blog_route_after_review,
)


class BlogState(TypedDict):
    session_id: str
    request: str
    brand_id: str
    brand_profile: Optional[dict]
    
    group: Literal["blog_web", "email_sale", "social_media"]
    function: str
    needs_image: bool
    system_prompt: str
    enriched_topic: str
    
    title: Optional[str]
    content: Optional[str]
    seo_meta: Optional[dict]
    image_url: Optional[str]
    
    draft: Optional[dict]
    approved: bool
    revision_note: Optional[str]
    
    usage: Annotated[dict, operator.or_]
    error: Optional[str]
    memory_history: List[dict]
    publish_status: Optional[str]


# Build graph
workflow = StateGraph(BlogState)

workflow.add_node("blog_prepare",        blog_prepare)
workflow.add_node("execute_blog_content", execute_blog_content)
workflow.add_node("execute_blog_image",   execute_blog_image)
workflow.add_node("blog_review_pause",    blog_review_pause)
workflow.add_node("blog_save",            blog_save)

# Entry
workflow.add_edge(START, "blog_prepare")

# Prepare → viết content
workflow.add_edge("blog_prepare", "execute_blog_content")

# Content → check cần ảnh?
workflow.add_conditional_edges(
    "execute_blog_content",
    blog_needs_visual,
    {
        "needs_image": "execute_blog_image",
        "no_image":    "blog_review_pause",
    }
)

# Image → review
workflow.add_edge("execute_blog_image", "blog_review_pause")

# Review loop
workflow.add_conditional_edges(
    "blog_review_pause",
    blog_route_after_review,
    {
        "approve": "blog_save",
        "revise":  "execute_blog_content",  # Quay lại viết lại
    }
)

# End
workflow.add_edge("blog_save", END)

blog_graph = workflow.compile(checkpointer=MemorySaver())