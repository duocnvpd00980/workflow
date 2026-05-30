# agent_os/system/law.py
# ============================================================
# SYSTEM LAW — như #define trong C nhúng
# Khai báo một lần, không ai sửa, mọi thứ tuân theo
# ============================================================
from dataclasses import dataclass


@dataclass(frozen=True)
class Law:
    max_seconds:    float = 30.0   # wall clock tuyệt đối
    max_iterations: int   = 50     # tổng vòng lặp toàn graph
    max_rework:     int   = 3      # retry tối đa
    max_errors:     int   = 10     # lỗi tích lũy


# Singleton — import và dùng thẳng
DEFAULT_LAW = Law()