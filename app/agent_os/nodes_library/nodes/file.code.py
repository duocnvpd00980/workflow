from .registry import BusRegistry
from .protocol import StandardFrame


# --- NHÓM 1: HỆ THỐNG LÕI ---
async def node_GATEKEEPER(state: MainBus, config: dict) -> dict:
    # Logic: Check toxic...
    res = {"is_safe": True}
    return StandardFrame.create("GK", res).to_bus(BusRegistry.GK)


async def node_SEED(state: MainBus, config: dict) -> dict:
    # Logic: Phân tích topic...
    res = {"topic": state.user_input, "lang": "vi"}
    return StandardFrame.create("SD", res).to_bus(BusRegistry.SD)


async def node_ROUTER(state: MainBus, config: dict) -> dict:
    # Logic: Rẽ nhánh...
    return StandardFrame.create("RT", {"route": "full"}).to_bus(BusRegistry.RT)


# --- NHÓM 2: SẢN XUẤT NỘI DUNG ---
async def node_BLOG_PLANNER(state: MainBus, config: dict) -> dict:
    topic = state.reg_seed.payload["topic"]
    # Logic: Lên outline...
    res = {"outline": ["H1", "H2"]}
    return StandardFrame.create("BP", res).to_bus(BusRegistry.BP)


async def node_BLOG_WRITER(state: MainBus, config: dict) -> dict:
    plan = state.reg_blog_plan.payload
    # Logic: Viết nháp...
    return {
        **StandardFrame.create("BW", "Nội dung bài viết...").to_bus(BusRegistry.BW),
        "pending_tool": False,  # Tín hiệu ngắt
    }


async def node_TOOL_EXECUTOR(state: MainBus, config: dict) -> dict:
    # Logic: Search Google...
    return StandardFrame.create("TE", "Kết quả search").to_bus(BusRegistry.TE)


async def node_BLOG_EDITOR(state: MainBus, config: dict) -> dict:
    draft = state.reg_blog_draft.payload
    # Logic: Chỉnh sửa...
    return StandardFrame.create("BE", "Bài viết đã edit").to_bus(BusRegistry.BE)


async def node_VALIDATOR(state: MainBus, config: dict) -> dict:
    # Logic: Kiểm định chất lượng...
    return {
        **StandardFrame.create("VA", {"passed": True}).to_bus(BusRegistry.VA),
        "needs_retry": False,
    }


# --- NHÓM 3: MARKETING AGENTS ---
async def node_AGENT_ADS(state: MainBus, config: dict) -> dict:
    # Logic: Viết quảng cáo...
    return StandardFrame.create("AD", "Nội dung Ads").to_bus(BusRegistry.AD)


async def node_AGENT_EMAIL(state: MainBus, config: dict) -> dict:
    # Logic: Viết Email...
    return StandardFrame.create("ML", "Nội dung Email").to_bus(BusRegistry.ML)


# --- NHÓM 4: HẬU KỲ & ĐẦU RA ---
async def node_AGGREGATOR(state: MainBus, config: dict) -> dict:
    # Logic: Gom Blog + Ads + Email
    res = {"bundle": "All Content"}
    return StandardFrame.create("AG", res).to_bus(BusRegistry.AG)


async def node_CONTEXT_CLIPPER(state: MainBus, config: dict) -> dict:
    # Logic: Dọn dẹp token thừa
    return StandardFrame.create("CP", "Cleaned").to_bus(BusRegistry.CP)


async def node_FINAL_POLISHER(state: MainBus, config: dict) -> dict:
    # Logic: Format Markdown cuối cùng
    return StandardFrame.create("FP", "MARKDOWN_FINAL").to_bus(BusRegistry.FP)


async def node_PERSIST_STREAMING(state: MainBus, config: dict) -> dict:
    # Logic: Ghi Database / Gửi API
    print(">>> Đã đẩy dữ liệu ra cổng kết nối!")
    return StandardFrame.create("PS", "SAVED").to_bus(BusRegistry.PS)
