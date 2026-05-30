from agent_os.system.bus.main_bus import MainBus
from agent_os.system.bus.protocol import StandardFrame


def system_monitor(state: MainBus):
    print("\n" + "="*50)
    print(f"{'NODE ID':<20} | {'TIME (ms)':<10} | {'TOKENS':<8} | {'COST ($)':<10}")
    print("-" * 50)

    total_cost = 0.0
    total_tokens = 0
    total_time = 0.0

    # Duyệt qua các thanh ghi trong MainBus
    # Pydantic cho phép duyệt qua các field bằng .dict() hoặc .__dict__
    for field_name, frame in state:
        if isinstance(frame, StandardFrame) and frame.telemetry:
            t = frame.telemetry
            print(f"{frame.node_id:<20} | {t.latency_ms:>10.2f} | {t.total_tokens:>8} | {t.cost_usd:>10.6f}")
            
            total_cost += t.cost_usd
            total_tokens += t.total_tokens
            total_time += t.latency_ms

    print("-" * 50)
    print(f"{'TOTAL':<20} | {total_time:>10.2f} | {total_tokens:>8} | {total_cost:>10.6f}")
    print("="*50 + "\n")