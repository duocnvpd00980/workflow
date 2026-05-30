from langchain_core.runnables import RunnableConfig
from langgraph.errors import NodeInterrupt # Công cụ ngắt của LangGraph
from agent_os.nodes_library.node_interrupt_sync.interrupt_sync_protocol import InterruptSyncOutput
from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.registry import BusRegistry
from agent_os.system.bus.protocol import StandardFrame

async def node_INTERRUPT_SYNC(state: MainBus, config: RunnableConfig) -> dict:
    """
    NODE INTERRUPT SYNC: 
    1. Kiểm tra đủ các nhánh (Parallel Barrier).
    2. Nếu đủ, thực hiện ngắt để chờ User (Human-in-the-loop).
    """

    # --- BƯỚC 1: KIỂM TRA ĐỒNG BỘ CÁC NHÁNH ---
    active_branches = getattr(state, "active_branches", [])
    completed_modules = getattr(state, "completed_modules", [])
    
    # So sánh tập hợp để biết đã đủ quân số chưa
    is_sync_complete = set(active_branches).issubset(set(completed_modules))

    # --- BƯỚC 2: LOGIC NGẮT (INTERRUPT) ---
    # Nếu các nhánh chưa xong, chúng ta chưa ngắt để hỏi User mà chỉ đơn giản là "chưa qua cửa"
    if not is_sync_complete:
        return StandardFrame.emit(
            BusRegistry.IS,
            InterruptSyncOutput(
                active_branches=active_branches,
                completed_modules=completed_modules,
                is_sync_complete=False,
                checkpoint_note="Đang đợi các nhánh song song hoàn tất..."
            ).model_dump()
        )

    # Nếu ĐÃ XONG các nhánh, nhưng CHƯA có xác nhận của User (giả sử check qua registry)
    user_approval_status = False # Trong thực tế sẽ lấy từ state.reg_interrupt_sync
    if state.reg_interrupt_sync:
        user_approval_status = state.reg_interrupt_sync.payload.get("is_approved", False)

    if not user_approval_status:
        # ĐÂY LÀ LỆNH QUAN TRỌNG NHẤT:
        # LangGraph sẽ dừng workflow tại đây, lưu toàn bộ State vào Database (Checkpoint).
        # Khi User bấm nút trên UI, họ sẽ gửi một 'Input' mới vào thread này để resume.
        raise NodeInterrupt(f"Yêu cầu xác nhận: Toàn bộ các nhánh {active_branches} đã sẵn sàng. Bạn có duyệt không?")

    # --- BƯỚC 3: KHI USER ĐÃ DUYỆT (SAU KHI RESUME) ---
    return StandardFrame.emit(
        BusRegistry.IS,
        InterruptSyncOutput(
            active_branches=active_branches,
            completed_modules=completed_modules,
            is_sync_complete=True,
            is_approved=True,
            checkpoint_note="Đã hoàn tất đồng bộ và User đã duyệt."
        ).model_dump()
    )