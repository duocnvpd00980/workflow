from langgraph.graph import StateGraph, END, START
from langgraph.types import RetryPolicy

from agent_os.system.shields.shield_faults import PipelineError
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.shields.shield_node import Node

from agent_os.nodes_library.node_final_response.adapter_final_response import node_final_response
from agent_os.nodes_library.node_input_guard.adapter_input_guard import node_input_guard
from agent_os.nodes_library.node_output_guard.adapter_output_guard import node_output_guard
from agent_os.nodes_library.node_cache_layer.adapter_cache_read import node_cache_read
from agent_os.nodes_library.node_cache_layer.adapter_cache_write import node_cache_write
from agent_os.nodes_library.node_heuristic_router.adapter_heuristic_router import node_heuristic_router
from agent_os.nodes_library.node_knowledgebase.adapter_knowledgebase import node_knowledgebase
from agent_os.nodes_library.node_relevance_check.adapter_relevance_check import node_relevance_check
from agent_os.nodes_library.node_fallback_search.adapter_fallback_search import node_fallback_search
from agent_os.nodes_library.node_generation.adapter_generation import node_generation

_retry = RetryPolicy(max_attempts=2, backoff_factor=1.5, retry_on=PipelineError)

# ── NODES ─────────────────────────────────────────────────
board = StateGraph(MainBus)

for key, fn in [
    (BusRegistry.IG,  node_input_guard),
    (BusRegistry.RO,  node_heuristic_router),
    (BusRegistry.CR,  node_cache_read),
    (BusRegistry.CW,  node_cache_write),
    (BusRegistry.KLB, node_knowledgebase),
    (BusRegistry.RC,  node_relevance_check),
    (BusRegistry.GEN, node_generation),
    (BusRegistry.OG,  node_output_guard),
    (BusRegistry.FB,  node_fallback_search),
    (BusRegistry.FR,  node_final_response),
]:
    Node(key, fn).mount(board)

# ── EDGES ─────────────────────────────────────────────────
board.add_edge(START,           BusRegistry.IG)
board.add_edge(BusRegistry.IG,  BusRegistry.RO)
board.add_edge(BusRegistry.RO,  BusRegistry.CR)

board.add_conditional_edges(
    BusRegistry.CR,
    lambda s: s.route("cache_read", default="miss"),
    {"hit": BusRegistry.FR, "miss": BusRegistry.KLB, "end": END},
)

board.add_edge(BusRegistry.KLB, BusRegistry.RC)

board.add_conditional_edges(
    BusRegistry.RC,
    lambda s: s.route("relevance_check", default="low_rel"),
    {"high_rel": BusRegistry.GEN, "low_rel": BusRegistry.FB, "end": END},
)

board.add_edge(BusRegistry.GEN, BusRegistry.OG)

board.add_conditional_edges(
    BusRegistry.OG,
    lambda s: s.route("output_guard"),
    {"cache": BusRegistry.CW, "skip_cache": BusRegistry.FR},
)

board.add_edge(BusRegistry.CW, BusRegistry.FR)

board.add_conditional_edges(
    BusRegistry.FB,
    lambda s: s.route("fallback_search"),
    {"tool_executed": BusRegistry.RC, "error": BusRegistry.FR},
)

board.add_edge(BusRegistry.FR, END)

# ── COMPILE ───────────────────────────────────────────────
async def get_industrial_mainboard(checkpointer):
    return board.compile(checkpointer=checkpointer)