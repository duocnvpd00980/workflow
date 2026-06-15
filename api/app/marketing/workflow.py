from typing import List, Annotated, TypedDict, Optional, Literal
import operator
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from app.marketing.nodes import (
    prepare,                  
    visual_intent_analyzer,   
    execute_social,    
    execute_blog,             
    execute_image,     
    execute_research,  
    review_pause,             
    visual_asset_selector,    
    context_synthesizer,      
    publish,           
    save,              
    select_template, 
    route_after_review,
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
    visual_intent: dict 
    memory_history: List[dict]
   


workflow = StateGraph(WorkflowState)
    
# Định nghĩa hàm phụ trợ để fork ngay tại đây
def fork_blog_node(state):
    return {}

# Đăng ký toàn bộ các Node
workflow.add_node("prepare",                prepare)
workflow.add_node("fork_blog",              fork_blog_node)         
workflow.add_node("visual_intent_analyzer", visual_intent_analyzer) 
workflow.add_node("execute_social",         execute_social)
workflow.add_node("execute_blog",           execute_blog)
workflow.add_node("execute_image",          execute_image)
workflow.add_node("execute_research",       execute_research)
workflow.add_node("review_pause",           review_pause)           
workflow.add_node("visual_asset_selector",  visual_asset_selector)  
workflow.add_node("context_synthesizer",    context_synthesizer)    
workflow.add_node("publish",                publish)
workflow.add_node("save",                   save)

workflow.add_edge(START, "prepare")
workflow.add_conditional_edges("prepare", select_template, {
    "execute_social":   "execute_social",
    "execute_blog":     "fork_blog",        
    "execute_image":    "execute_image",
    "execute_research": "execute_research",
    "save":             "save",
})

workflow.add_edge("fork_blog", "execute_blog")
workflow.add_edge("fork_blog", "visual_intent_analyzer")
workflow.add_edge("execute_blog",           "visual_asset_selector")
workflow.add_edge("visual_intent_analyzer",   "visual_asset_selector")
workflow.add_edge("visual_asset_selector",    "review_pause")
workflow.add_edge("execute_social",   "review_pause")
workflow.add_edge("execute_image",    "review_pause")
workflow.add_edge("execute_research", "save")
workflow.add_conditional_edges("review_pause", route_after_review, {
    "publish": "publish",              
    "save":    "save",
    "revise":  "context_synthesizer",   
})

workflow.add_conditional_edges(
    "context_synthesizer", 
    lambda state: state.get("template", "blog"), 
    {
        "blog":   "execute_blog",
        "social": "execute_social"
    }
)

workflow.add_edge("publish", "save")
workflow.add_edge("save", END)

marketing_graph = workflow.compile(checkpointer=MemorySaver())