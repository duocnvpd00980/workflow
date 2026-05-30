🔥 “Embedded system thinking áp dụng cho AI system design”


agent_os/
│
├── system/
│
│   ├── core_protocol.py
│
│   ├── bus/
│   │   ├── __init__.py
│   │   ├── main_bus.py
│   │   ├── protocol.py
│   │   └── registry.py
│   │
│   ├── shields/
│   │   ├── __init__.py
│   │   ├── run_shielded.py
│   │   ├── shield_telemetry.py
│   │   ├── shield_node.py
│   │   ├── shield_registry.py
│   │   └── shield_runtime.py
│   │
│   ├── contracts/
│   │   ├── __init__.py
│   │   ├── content_contracts.py
│   │   ├── blog_contracts.py
│   │   ├── tool_contracts.py
│   │   ├── seed_contracts.py
│   │   └── validator_contracts.py
│   │
│   ├── infra/
│   │   ├── __init__.py
│   │   ├── app_config.py
│   │   ├── logging_system.py
│   │   ├── sanitiser.py
│   │   ├── kill_switch.py
│   │   ├── circuit_breaker.py
│   │   ├── budget_guard.py
│   │   ├── rate_limiter.py
│   │   ├── policy_engine.py
│   │   └── safety_gatekeeper.py
│   │
│   ├── runtime/
│   │   ├── __init__.py
│   │   ├── runtime_engine.py
│   │   ├── llm_router.py
│   │   ├── service_container.py
│   │   ├── financial_firewall.py
│   │   └── safe_node.py
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── language.py
│   │   ├── hashing.py
│   │   └── serializers.py
│   │
│   └── knowledge/
│       ├── __init__.py
│       └── ingestion_service.py
│       └── knowledge_engine.py
│       └── retrieval_service.py
│       └── ingestion_service.py
│
│
├── nodes_library/
│
│   ├── node_gatekeeper/
│   │   ├── __init__.py
│   │   ├── adapter_gatekeeper.py
│   │   ├── gatekeeper_service.py
│   │   └── gatekeeper_schema.py
│   │
│   ├── node_ads/
│   │   ├── __init__.py
│   │   ├── adapter_ads.py
│   │   ├── ads_schema.py
│   │   └── ads_service.py
│   │
│   ├── node_rate_limiter/
│   │   ├── adapter_rate_limiter.py
│   │   ├── rate_limiter_schema.py
│   │   ├
│   │   └── editrate_limiter_serviceor.py
│   │
│   └── node_rate_limiter/
│       ├── fallback_factory.py
│       └── node_helpers.py
│
│
├── mainboard.py
│
└── app.py





🔥 MAINBOARD (SHIELD ENFORCER)
motherboard.add_node(
    "AGENT_ADS",
    run_shielded(node_AGENT_ADS)
)
🔥 NODE (PURE)
async def node_AGENT_ADS(state, config):
    module = AdsModule(llm)
    return await module.run(state.seed)
🔥 MODULE (AI LOGIC)
AdsModule → prompt → LLM → parser
7. QUY TẮC VÀNG
NODE KHÔNG ĐƯỢC LÀM:
shield_pre
shield_post
policy check
budget logic
SHIELD KHÔNG ĐƯỢC LÀM:
business logic
prompt design
parsing output
8. TƯ DUY CHUẨN CÔNG TY LỚN
Kubernetes admission controller style:

MAINBOARD = enforcement layer

NODE = stateless function

SHIELD = middleware layer


============



USER INPUT
   ↓
MAINBOARD (run_shielded)
   ↓
PRE-GUARD
   ↓
NODE (pure adapter)
   ↓
ADS MODULE (LLM logic)
   ↓
POST-GUARD
   ↓
MAINBUS OUTPUT




https://docs.aurelio.ai/semantic-router/get-started/introduction


==================================

Trước tiên cần hiểu rõ cấu trúc project của bạn. Gửi output của lệnh này lên:

find /home/duoc/ai-stack -type f -name "*.py" | grep -v "__pycache__" | grep -v ".venv" | sort | head -80

find /home/duoc/ai-stack -maxdepth 3 -type f -name "*.py" | grep -v "__pycache__" | grep -v ".venv" | grep -v "nodes_library" | sort


================

promptfoo eval