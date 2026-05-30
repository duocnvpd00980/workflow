from __future__ import annotations
from pydantic import BaseModel, Field, ConfigDict
from typing import Any, List, Optional, Annotated, Dict
from operator import add

# Import Protocols
from agent_os.nodes_library.node_ads.ads_protocol import AdOutput
from agent_os.nodes_library.node_blog_planner.planner_protocol import BlogPlanOutput
from agent_os.nodes_library.node_blog_writer.writer_protocol import WriterOutput
from agent_os.nodes_library.node_bus_splitter.splitter_protocol import BusSplitterOutput
from agent_os.nodes_library.node_cache_memory.cache_memory_protocol import CacheMemoryOutput
from agent_os.nodes_library.node_circuit_breaker.circuit_breaker_protocol import CircuitBreakerOutput
from agent_os.nodes_library.node_finalizer.finalizer_protocol import FinalizerOutput
from agent_os.nodes_library.node_gatekeeper.gatekeeper_protocol import GatekeeperOutput
from agent_os.nodes_library.node_knowledge_retriever.knowledge_protocol import KnowledgeRetrieverOutput
from agent_os.nodes_library.node_mail.mail_protocol import MailOutput
from agent_os.nodes_library.node_memory_engine.memory_engine_protocol import MemoryEngineOutput
from agent_os.nodes_library.node_observer.observer_protocol import ObserverOutput
from agent_os.nodes_library.node_rate_limiter.rate_limiter_protocol import RateLimitOutput
from agent_os.nodes_library.node_router.router_protocol import RouterOutput
from agent_os.nodes_library.node_dead_letter_queue.dead_letter_queue_protocol import DeadLetterQueueOutput
from agent_os.nodes_library.node_seed.seed_protocol import SeedOutput
# Các protocol mới bạn vừa tạo
from agent_os.nodes_library.node_interrupt_sync.interrupt_sync_protocol import InterruptSyncOutput
from agent_os.nodes_library.node_tools.tools_protocol import ToolsAdapterOutput
from agent_os.nodes_library.node_validator.validator_protocol import ValidatorOutput

from .protocol import StandardFrame

# =========================================================
# MAIN BUS (The Motherboard)
# =========================================================

class MainBus(BaseModel):
    """
    MAINBOARD STATE: Kiến trúc thanh ghi cô lập.
    Loại bỏ các thuộc tính lẻ để tin tưởng tuyệt đối vào Payload của thanh ghi.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    # 1. INPUT BUFFER
    user_input: str = ""

    # 2. CORE REGISTERS (Thanh ghi hệ thống)
    reg_gatekeeper:   Optional[StandardFrame[GatekeeperOutput]] = None
    reg_seed:         Optional[StandardFrame[SeedOutput]] = None
    reg_router:       Optional[StandardFrame[RouterOutput]] = None
    reg_rate_limiter: Optional[StandardFrame[RateLimitOutput]] = None
    reg_circuit_breaker: Optional[StandardFrame[CircuitBreakerOutput]] = None
    reg_dead_letter_queue: Optional[StandardFrame[DeadLetterQueueOutput]] = None
    reg_cache_memory: Optional[StandardFrame[CacheMemoryOutput]] = None

    # 3. SPECIALIST AGENTS & PIPELINES (Thanh ghi nghiệp vụ)
    reg_ads: Optional[StandardFrame[AdOutput]] = None
    reg_email: Optional[StandardFrame[MailOutput]] = None
    reg_blog_plan: Optional[StandardFrame[BlogPlanOutput]] = None
    reg_blog_writer: Optional[StandardFrame[WriterOutput]] = None
    reg_validator: Optional[StandardFrame[ValidatorOutput]] = None
    reg_tool_results: Optional[StandardFrame[ToolsAdapterOutput]] = None
    reg_knowledge: Optional[StandardFrame[KnowledgeRetrieverOutput]] = None

    # 4. INFRASTRUCTURE & SYNC (Điều hướng & Đồng bộ)
    reg_bus_splitter: Optional[StandardFrame[BusSplitterOutput]] = None
    reg_interrupt_sync: Optional[StandardFrame[InterruptSyncOutput]] = None
    reg_observer: Optional[StandardFrame[ObserverOutput]] = None
    reg_memory_context: Optional[StandardFrame[MemoryEngineOutput]] = None
    reg_finalizer: Optional[StandardFrame[FinalizerOutput]] = None
    reg_ui_selector: Optional[StandardFrame] = None

    # 5. PARALLEL TRACKING (Dành cho Reducer - Bắt buộc giữ lại)
    # Các trường này dùng Annotated[list, add] để LangGraph merge dữ liệu từ các nhánh
    active_branches: Annotated[list[str], add] = Field(default_factory=list)
    completed_modules: Annotated[list[str], add] = Field(default_factory=list)
    errors: Annotated[list[str], add] = Field(default_factory=list)

    # 6. GLOBAL CONTROL FLAGS (Trạng thái vận hành thực tế)
    workflow_stage: str = "init"
    is_aborted: bool = False
    revision_count: int = 0
    tool_call_count: int = 0   # đếm số lần BW→TE
    rework_count: int = 0      # đếm số lần VA→BW

    # =====================================================
    # HELPER LOGIC
    # =====================================================
    def write_to_slot(self, slot: str, frame: StandardFrame):
        if hasattr(self, slot):
            setattr(self, slot, frame)

    def read_from_slot(self, slot: str) -> Optional[StandardFrame]:
        return getattr(self, slot, None)