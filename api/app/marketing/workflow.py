from typing import List, Annotated, TypedDict, Optional, Literal
import operator
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# ========== NODES IMPORT ==========
from app.marketing.nodes import (
    prepare,                  # Phân loại nhóm + chức năng + flag cần ảnh
    execute_content,          # 1 node viết nội dung chung (thay execute_blog, execute_social, execute_email)
    execute_image,            # Tạo ảnh (chỉ chạy khi cần)
    review_pause,             # Human-in-the-loop
    save,                     # Lưu kết quả
    route_after_review,       # Điều hướng sau review
    needs_visual,             # Conditional: có cần ảnh không?
)


# ========== STATE ==========
class WorkflowState(TypedDict):
    session_id: str
    request: str
    brand_id: str
    
    # 3 nhóm chính, mỗi nhóm có các chức năng con
    group: Literal["blog_web", "email_sale", "social_media"]
    function: Literal[
        # Blog & Web
        "blog_post", "product_description", "website_copy",
        # Email & Sale
        "email_marketing", "sales_page", "product_launch",
        # Social Media
        "social_post", "caption_set", "hashtag_set"
    ]
    
    # Flag cần ảnh (set tại prepare dựa vào function)
    needs_image: bool
    
    # Content & draft
    content: Optional[str]      # Nội dung text đã viết
    image_url: Optional[str]    # URL ảnh (nếu có)
    draft: Optional[dict]       # Gói kết quả cuối
    
    # Review flow
    approved: bool
    revision_note: Optional[str]  # Ghi chú sửa (nếu có)
    
    # Tracking
    usage: Annotated[dict, operator.or_]
    error: Optional[Literal["timeout", "rate_limit", "invalid", "fatal"]]
    memory_history: List[dict]


# ========== GRAPH ==========
workflow = StateGraph(WorkflowState)

# Đăng ký nodes
workflow.add_node("prepare",         prepare)
workflow.add_node("execute_content", execute_content)   # 1 node cho cả 3 nhóm
workflow.add_node("execute_image",   execute_image)       # Chạy khi needs_image=True
workflow.add_node("review_pause",    review_pause)
workflow.add_node("save",            save)

# Entry
workflow.add_edge(START, "prepare")

# Từ prepare → execute_content (luôn viết nội dung trước)
workflow.add_edge("prepare", "execute_content")

# Từ execute_content → conditional (cần ảnh không?)
workflow.add_conditional_edges(
    "execute_content",
    needs_visual,  # Hàm kiểm tra state["needs_image"]
    {
        "needs_image": "execute_image",   # Có ảnh → tạo ảnh
        "no_image":    "review_pause",    # Không ảnh → đi review luôn
    }
)

# Từ execute_image → review_pause
workflow.add_edge("execute_image", "review_pause")

# Review loop: publish (save) / revise (quay lại viết lại)
workflow.add_conditional_edges(
    "review_pause",
    route_after_review,
    {
        "approve": "save",              # Đồng ý → lưu
        "revise":  "execute_content",   # Sửa → quay lại viết lại (có thể ghi revision_note)
    }
)

# End
workflow.add_edge("save", END)

marketing_graph = workflow.compile(checkpointer=MemorySaver())