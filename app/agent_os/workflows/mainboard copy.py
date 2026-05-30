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

from agent_os.nodes_library.node_aggregator.adapter_aggregator import node_aggregator
from agent_os.nodes_library.node_evaluator.adapter_evaluator import node_evaluator
from agent_os.nodes_library.node_final_response.adapter_final_response import node_final_response
from agent_os.nodes_library.node_human_review.adapter_human_review import node_human_review
from agent_os.nodes_library.node_input_guard.adapter_input_guard import node_input_guard
from agent_os.nodes_library.node_knowledge.adapter_knowledge import node_knowledge
from agent_os.nodes_library.node_marketing.adapter_node_marketing import node_marketing
from agent_os.nodes_library.node_output_guard.adapter_output_guard import node_output_guard
from agent_os.nodes_library.node_shared_state.adapter_shared_state import node_shared_state
from agent_os.nodes_library.node_supervisor.adapter_supervisor import node_supervisor
from agent_os.nodes_library.node_lightweight_chat.adapter_lightweight_chat import node_lightweight_chat



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
# NODES
# =========================================================
Node(BusRegistry.IG,  node_input_guard).mount(board)
Node(BusRegistry.LWC, node_lightweight_chat).mount(board)
Node(BusRegistry.AG,  node_aggregator).mount(board)
Node(BusRegistry.HR,  node_human_review).mount(board)
Node(BusRegistry.OG,  node_output_guard).mount(board)
Node(BusRegistry.FR,  node_final_response).mount(board)
Node(BusRegistry.MT,  node_marketing).retry(_max).mount(board)
Node(BusRegistry.KL,  node_knowledge).retry(_max).mount(board)
Node(BusRegistry.EV,  node_evaluator).retry(_max).mount(board)
Node(BusRegistry.SV,  node_supervisor).retry(_max).mount(board)

# =========================================================
# EDGES
# =========================================================
board.add_edge(START, BusRegistry.IG)
board.add_edge(BusRegistry.IG, BusRegistry.SV)

# Supervisor → Workers
board.add_conditional_edges(
    BusRegistry.SV,
    lambda state: state.route("supervisor", default="end"),
    {
        "knowledge": BusRegistry.KL,
        "marketing": BusRegistry.MT,
        "smalltalk": BusRegistry.LWC,
        "end":       END,
    },
)

# Smalltalk shortcut
board.add_edge(BusRegistry.LWC, BusRegistry.FR)

# Workers → Evaluator
board.add_edge(BusRegistry.MT, BusRegistry.EV)
board.add_edge(BusRegistry.KL, BusRegistry.EV)

# Evaluator routing
board.add_conditional_edges(
    BusRegistry.EV,
    lambda state: state.route("evaluator", default="end"),
    {
        "retry": BusRegistry.SV,
        "pass":  BusRegistry.AG,
        "end":   END,
    },
)

# Output pipeline
board.add_edge(BusRegistry.AG, BusRegistry.OG)
board.add_edge(BusRegistry.OG, BusRegistry.HR)

# Human review routing
board.add_conditional_edges(
    BusRegistry.HR,
    lambda state: state.route("human_review", default="end"),
    {
        "approved": BusRegistry.FR,
        "rejected": BusRegistry.SV,  # retry từ supervisor
        "end":      END,
    },
)

# Final
board.add_edge(BusRegistry.FR, END)

# =========================================================
# COMPILE
# =========================================================
async def get_industrial_mainboard():
    async with factory.get_checkpointer() as db_checkpointer:
        return board.compile(
            checkpointer=db_checkpointer,
        )

