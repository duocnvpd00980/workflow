import os

def setup_observability():
    # Tích hợp LangSmith (Tiêu chuẩn công nghiệp cho AI Tracing)
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "Marketing_SaaS_Prod"
    os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")

    # Bạn có thể thêm Prometheus/OpenTelemetry ở đây để đo latency thô
    print("✅ Observability Layer: LangSmith Tracing Enabled.")