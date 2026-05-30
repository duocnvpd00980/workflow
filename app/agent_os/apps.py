"""
agent_os/apps.py

AppConfig tối giản — không boot bất kỳ async service nào.

Lý do không boot trong ready()
--------------------------------
ready() là synchronous context. Mọi cách chạy async từ đây đều là
workaround (ThreadPoolExecutor, nest_asyncio...) và không được Django
khuyến nghị. Django docs nói rõ: ready() dùng để đăng ký signals,
không phải để khởi tạo connections hay external resources.

Thay vào đó: lazy initialization trong get_services() — khởi tạo
đúng lúc cần, trong đúng async context, với asyncio.Lock đảm bảo
chỉ chạy một lần dù nhiều requests đến cùng lúc.
"""

from django.apps import AppConfig


class AgentOsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "agent_os"

    def ready(self) -> None:
        # Chỉ đăng ký signals ở đây nếu cần.
        # Không khởi tạo async resources.
        pass