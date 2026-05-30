from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import RetryPolicy

from agent_os.system.infra.telemetry import setup_observability
from agent_os.system.shields.shield_faults import PipelineError
from agent_os.system.infra.persistence import factory
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.shields.shield_node import Node

# =========================================================
# MAPPING: CORE AGENT FLOW (Theo sơ đồ Mermaid)
# =========================================================

from agent_os.nodes_library.node_final_response.adapter_final_response import (
    node_final_response,
)
from agent_os.nodes_library.node_input_guard.adapter_input_guard import node_input_guard
from agent_os.nodes_library.node_output_guard.adapter_output_guard import (
    node_output_guard,
)
from agent_os.nodes_library.node_cache_layer.adapter_cache_read import node_cache_read
from agent_os.nodes_library.node_cache_layer.adapter_cache_write import node_cache_write
from agent_os.nodes_library.node_heuristic_router.adapter_heuristic_router import (
    node_heuristic_router,
)
from agent_os.nodes_library.node_knowledgebase.adapter_knowledgebase import (
    node_knowledgebase,
)
from agent_os.nodes_library.node_relevance_check.adapter_relevance_check import (
    node_relevance_check,
)
from agent_os.nodes_library.node_fallback_search.adapter_fallback_search import (
    node_fallback_search,
)
from agent_os.nodes_library.node_generation.adapter_generation import node_generation


setup_observability()

# =========================================================
# RETRY POLICY
# =========================================================
_max = RetryPolicy(
    max_attempts=2,
    backoff_factor=1.5,
    retry_on=PipelineError,
)

# =========================================================
# BOARD
# =========================================================

board = StateGraph(MainBus)

# =========================================================
# CORE AGENT FLOW
# =========================================================


# =============================================================================
# 2. ĐĂNG KÝ CÁC NODE (Khớp chuẩn xác tên hàm và định danh hệ thống của cậu)
# =============================================================================
Node(BusRegistry.IG, node_input_guard).mount(board)  # Node 1: Kiểm tra an toàn
Node(BusRegistry.RO, node_heuristic_router).mount(
    board
)  # Node 2: Bộ định tuyến từ khóa
Node(BusRegistry.CR, node_cache_read).mount(board)  # Node 3: Bộ nhớ đệm L1/L2
Node(BusRegistry.CW, node_cache_write).mount(board)  # Node 3: Bộ nhớ đệm L1/L2
Node(BusRegistry.FR, node_final_response).mount(board)  # Node 8: Trả kết quả UI
Node(BusRegistry.FB, node_fallback_search).mount(
    board
)  # Node THÊM MỚI: Khối cứu cánh Fallback

Node(BusRegistry.KLB, node_knowledgebase).mount(board)  # Node 4: Quét FAISS lấy Context
Node(BusRegistry.RC, node_relevance_check).mount(board)  # Node 5: Check rác tài liệu
Node(BusRegistry.GEN, node_generation).mount(board)  # Node 6: Gọi LLM sinh câu trả lời
Node(BusRegistry.OG, node_output_guard).mount(board)  # Node 7: Kiểm tra đầu ra

# =============================================================================
# 3. THIẾT LẬP ĐƯỜNG ĐI TUYẾN TÍNH - KHỚP 100% MÃ MERMAID CỦA CẬU
# =============================================================================


board.add_edge(START, BusRegistry.IG)
board.add_edge(BusRegistry.IG, BusRegistry.RO)
board.add_edge(BusRegistry.RO, BusRegistry.CR)
board.add_conditional_edges(
    BusRegistry.CR,
    lambda state: state.route("cache_read", default="miss"),
    {
        "hit": BusRegistry.FR,
        "miss": BusRegistry.KLB,
        "end": END,
    },
)
board.add_edge(BusRegistry.KLB, BusRegistry.RC)
board.add_conditional_edges(
    BusRegistry.RC,
    lambda state: state.route("relevance_check", default="low_rel"),
    {
        "high_rel": BusRegistry.GEN,
        "low_rel": BusRegistry.FB,
        "end": END,
    },
)
board.add_edge(BusRegistry.GEN, BusRegistry.OG)
board.add_edge(BusRegistry.OG, BusRegistry.CW)
board.add_conditional_edges(
    BusRegistry.OG,
    lambda state: state.route("output_guard"),
    {
        "cache": END,
        "skip_cache": END,
    },
)

board.add_edge(BusRegistry.OG, BusRegistry.FR)
board.add_conditional_edges(
    BusRegistry.FB,
    lambda state: state.route("fallback_search"),
    {
        "tool_executed": BusRegistry.RC,
        "error": BusRegistry.FR,
    },
)
board.add_edge(BusRegistry.FR, END)


# =========================================================
# COMPILE
# =========================================================
async def get_industrial_mainboard():
    async with factory.get_checkpointer() as db_checkpointer:
        return board.compile(
            checkpointer=db_checkpointer,
        )
