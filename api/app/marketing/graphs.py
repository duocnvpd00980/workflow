from __future__ import annotations

from app.marketing.blog_graph import blog_graph

GRAPHS = {
    "blog_web": blog_graph,
    # "email_sale": email_graph,      # TODO: Thêm sau
    # "social_media": social_graph,   # TODO: Thêm sau
}

def get_graph(group: str):
    if group not in GRAPHS:
        raise ValueError(f"Unknown group: {group}. Available: {list(GRAPHS.keys())}")
    return GRAPHS[group]