 
from __future__ import annotations
import hashlib
import json
import logging
import time
import uuid

from enum import Enum
from typing import Annotated, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


# =============================================================================
# §0  STRUCTURED LOGGING  (cross-cutting concern, initialised first)
# =============================================================================
 
_log = logging.getLogger("agent_os_v11")
if not _log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter(
        '{"ts":"%(asctime)s","lvl":"%(levelname)s","body":%(message)s}',
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))
    _log.addHandler(_h)
    _log.setLevel(logging.INFO)
 
 
def _emit(level: str, **kw) -> None:
    """Emit a structured JSON log line."""
    getattr(_log, level)(json.dumps(kw, ensure_ascii=False, default=str))

# =============================================================================
# §1  SYSTEM-WIDE CONFIG  (immutable after process boot)
# =============================================================================
 
class AppConfig(BaseModel):
    """
    ┌─────────────────────────────────────────────────────┐
    │  BOOT ROM — read-only after initialisation.          │
    │  All runtime constants live here; no magic numbers   │
    │  scattered through the codebase.                     │
    └─────────────────────────────────────────────────────┘
    """
    model_config = ConfigDict(frozen=True)
 
    # ── LLM back-end ──────────────────────────────────────────────────────────
    default_model:        str   = "llama3.2:3b"
    url:                  str   = "http://192.168.101.18:11434/v1/chat/completions"
    api_key:              str   = "ollama"
    cost_per_1k_tokens:   float = 0.0009
 
    # ── Retry / timeout ───────────────────────────────────────────────────────
    max_retries:          int   = 3
    base_backoff:         float = 0.5
    node_timeout:         float = 60.0
    sla_timeout:          float = 300.0
 
    # ── Input / output limits ─────────────────────────────────────────────────
    max_input_len:        int   = 4_000
    max_outputs_kept:     int   = 5
 
    # ── Circuit-breaker ───────────────────────────────────────────────────────
    cb_failure_threshold: int   = 5
    cb_recovery_seconds:  float = 30.0
 
    # ── Rate limiter ──────────────────────────────────────────────────────────
    rate_limit_per_min:   int   = 20
 
    # ── Supervisor (closed-loop blog pipeline) ────────────────────────────────
    max_blog_revisions:   int   = 3
 
    # ── Quality gate thresholds ───────────────────────────────────────────────
    min_content_length:   int   = 150
    validator_pass_score: float = 0.70
 
 
CFG = AppConfig()
 
 
# =============================================================================
# ┌─────────────────────────────────────────────────────────────────────────┐
# │  NAMESPACE: Infrastructure::StateBus                                     │
# │  The typed, shared memory bus that all execution units read/write.       │
# └─────────────────────────────────────────────────────────────────────────┘
# =============================================================================
 
# =============================================================================
# §2  DOMAIN VALUE OBJECTS  (pure data; no behaviour)
# =============================================================================
 
class SeedStrategy(BaseModel):
    """
    Immutable campaign brief extracted from user input.
    Carried on the bus for the lifetime of the pipeline run.
    """
    target_audience: str = "general"
    main_benefit:    str = "engagement"
    brand_voice:     str = "professional"
    keyword:         str = "marketing"
    language:        str = "vi"
    tone:            str = "professional"
    content_rules:   str = ""
 
    @model_validator(mode="before")
    @classmethod
    def _flatten_nested(cls, v: dict) -> dict:
        """Coerce any nested dict/list values to plain strings."""
        def _f(x: object) -> str:
            if isinstance(x, str):  return x
            if isinstance(x, dict): return ", ".join(str(i) for i in x.values() if i)[:200]
            if isinstance(x, list): return ", ".join(str(i) for i in x)[:200]
            return str(x)[:200]
        for k in ("target_audience", "main_benefit", "brand_voice",
                  "keyword", "language", "tone", "content_rules"):
            if k in v:
                v[k] = _f(v[k])
        return v
 
 
class ContentItem(BaseModel):
    """A single piece of produced content with provenance metadata."""
    content:           str  = ""
    agent:             str  = ""
    language_detected: str  = ""
    has_cta:           bool = False
 
 
class BlogOutline(BaseModel):
    """Intermediate artefact — pruned by ContextClipper after Writer consumes it."""
    title:       str = ""
    sections:    str = ""
    key_points:  str = ""
    word_target: int = 300
 
 
class BlogDraft(BaseModel):
    """Mutable draft that travels through the closed-loop blog pipeline."""
    content: str  = ""
    has_cta: bool = False
 
 
class ValidatorVerdict(BaseModel):
    """Quality gate output — drives the supervisor retry decision."""
    passed:       bool  = False
    score:        float = 0.0     # 0.0 – 1.0
    issues:       str   = ""
    needs_retry:  bool  = False
    retry_reason: str   = ""
 
 
class ToolCallRecord(BaseModel):
    """Serialisable record of every sandboxed tool invocation."""
    agent_id:  str
    tool_name: str
    query:     str
    result:    str   = ""
    success:   bool  = False
    ts:        float = Field(default_factory=time.time)
 
 
class NodeAudit(BaseModel):
    """Per-node telemetry appended to the audit trail on the bus."""
    node:              str
    model:             str
    session_id:        str
    runtime_ms:        float
    prompt_tokens:     int   = 0
    completion_tokens: int   = 0
    total_tokens:      int   = 0
    cost_usd:          float = 0.0
    success:           bool  = True
    error:             str   = ""
    ts:                float = Field(default_factory=time.time)
 
    @classmethod
    def failure(
        cls,
        node: str,
        model: str,
        session_id: str,
        error: str,
        runtime_ms: float = 0.0,
    ) -> "NodeAudit":
        return cls(node=node, model=model, session_id=session_id,
                   runtime_ms=round(runtime_ms, 1), success=False, error=error)
 
 
class PipelineError(BaseModel):
    """Structured fault record — never raises; always recorded on bus."""
    node:        str
    code:        str
    message:     str
    recoverable: bool  = True
    ts:          float = Field(default_factory=time.time)
 
 
# =============================================================================
# §3  STATE BUS  (AgentState)
# =============================================================================
 
# ── Reducer helpers ───────────────────────────────────────────────────────────
 
def _dedup_merge(a: list[ContentItem], b: list[ContentItem]) -> list[ContentItem]:
    """Union merge — deduplicate by content hash (MD5)."""
    seen: set[str] = set()
    out:  list     = []
    for item in (a or []) + (b or []):
        h = hashlib.md5(item.content.encode()).hexdigest()
        if h not in seen:
            seen.add(h)
            out.append(item)
    return out
 
def _sum_cost(a: float, b: float)                   -> float: return round(float(a or 0) + float(b or 0), 6)
def _append_audits(a: list, b: list)                -> list:  return (a or []) + (b or [])
def _append_errors(a: list, b: list)                -> list:  return (a or []) + (b or [])
def _append_tools(a: list, b: list)                 -> list:  return (a or []) + (b or [])
def _or_degraded(a: bool, b: bool)                  -> bool:  return a or b
 
 
class SupervisorStatus(str, Enum):
    """State-machine labels for the blog closed-loop supervisor."""
    IDLE      = "idle"
    RUNNING   = "running"
    PASSED    = "passed"
    FAILED    = "failed"
    EXHAUSTED = "exhausted"
 
 
class AgentState(BaseModel):
    """
    ┌──────────────────────────────────────────────────────────────────────┐
    │  PCIe-STYLE DATA BUS                                                  │
    │                                                                        │
    │  Design contract:                                                      │
    │    • Every field MUST be JSON-serialisable (LangGraph checkpoint)      │
    │    • No Optional[dataclass] — use Optional[BaseModel] only            │
    │    • Annotated fields use explicit reducer functions (no magic)        │
    │    • Field docstrings indicate which namespace owns the field          │
    └──────────────────────────────────────────────────────────────────────┘
    """
    model_config = ConfigDict(arbitrary_types_allowed=False)
 
    # ── Identity lane ─────────────────────────────────────────────────────────
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()),
                            description="Server-generated; never client-supplied.")
    user_id:    str = Field(default="anonymous",
                            description="Caller identity for audit trail.")
 
    # ── Input lane ────────────────────────────────────────────────────────────
    user_input: str = Field(description="Raw user request; sanitised by Gatekeeper.")
    language:   str = Field(default="vi",
                            description="ISO-639-1 language code; enforced pipeline-wide.")
 
    # ── Security lane (owned by Infrastructure::PowerManagement) ──────────────
    is_safe:       bool = Field(default=True,  description="Cleared by SafetyGatekeeper.")
    safety_reason: str  = Field(default="",    description="Populated on unsafe verdict.")
    aborted:       bool = Field(default=False, description="Set on kill-switch / budget exhaustion.")
 
    # ── Orchestration lane ────────────────────────────────────────────────────
    seed: Optional[SeedStrategy] = Field(default=None,
                                         description="Campaign brief; written once by SEED node.")
 
    # ── Blog pipeline lane (owned by Modules::ExecutionUnits::BlogUnit) ───────
    blog_outline:        Optional[BlogOutline] = Field(default=None,
                                                       description="Consumed & pruned by ContextClipper.")
    blog_draft:          Optional[BlogDraft]   = Field(default=None,
                                                       description="Live draft inside closed-loop.")
    blog_stage_degraded: Annotated[bool, _or_degraded] = Field(
        default=False, description="True if any blog stage used a fallback path.")
 
    # Supervisor closed-loop counters
    supervisor_status: str = Field(default=SupervisorStatus.IDLE,
                                   description="State-machine label for blog closed-loop.")
    revision_count:    int = Field(default=0,  description="Number of revision cycles completed.")
    max_revisions:     int = Field(default=CFG.max_blog_revisions,
                                   description="Hard ceiling on revision cycles.")
    feedback:          str = Field(default="", description="Editor feedback carried to next Writer pass.")
 
    # Validator verdict
    last_validator_verdict: Optional[ValidatorVerdict] = Field(
        default=None, description="Most recent Validator output; drives routing decision.")
 
    # ── Tool sandbox lane (owned by Infrastructure::PowerManagement) ──────────
    pending_tool:        str = Field(default="", description="Tool name awaiting execution.")
    pending_tool_input:  str = Field(default="", description="Sanitised query for pending tool.")
    tool_result:         str = Field(default="", description="Sanitised result from last tool call.")
    tool_call_history:   Annotated[list[ToolCallRecord], _append_tools] = Field(
        default_factory=list, description="Append-only ledger of all tool invocations.")
 
    # ── Output lane ───────────────────────────────────────────────────────────
    outputs: Annotated[list[ContentItem], _dedup_merge] = Field(
        default_factory=list, description="Final produced content items.")
 
    # ── Finance lane (owned by Infrastructure::PowerManagement) ───────────────
    total_cost:   Annotated[float, _sum_cost] = Field(
        default=0.0, description="Cumulative LLM spend in USD.")
    budget_limit: float = Field(
        default=2.0, description="Hard cap; enforced by FinancialFirewall.")
 
    # ── Observability lane ────────────────────────────────────────────────────
    audit_log: Annotated[list[NodeAudit],     _append_audits] = Field(default_factory=list)
    errors:    Annotated[list[PipelineError], _append_errors] = Field(default_factory=list)
 
 
# Alias for type hints inside modules
StateBus = AgentState
 
 
 # =============================================================================
# ┌─────────────────────────────────────────────────────────────────────────┐
# │  NAMESPACE: Infrastructure::PowerManagement                              │
# │  Security, budget enforcement, and model routing.                        │
# │  No execution-unit code lives here.                                      │
# └─────────────────────────────────────────────────────────────────────────┘
# =============================================================================
 
# =============================================================================
# §4  SANITISER + INJECTION DETECTOR
# =============================================================================
 
_INJECTION_SIGNALS: frozenset[str] = frozenset({
    "ignore previous", "ignore all", "system prompt", "reveal key",
    "reveal secret", "act as", "pretend you", "jailbreak",
    "disregard instruction", "forget everything", "new instructions",
    "override", "admin mode", "developer mode", "sudo",
})
 
_RE_SCRIPT    = re.compile(r"<script[\s\S]*?</script>", re.I)
_RE_TAG       = re.compile(r"<[^>]+>")
_RE_FENCE     = re.compile(r"```[\s\S]*?```")
_RE_INLINE_CD = re.compile(r"`[^`]+`")
_RE_NULL      = re.compile(r"\x00")
 
 
def sanitise(text: str) -> str:
    """Strip HTML, code fences, null bytes, and homoglyphs."""
    if not text:
        return ""
    text = _RE_NULL.sub("", text)
    text = text.translate(str.maketrans("ａｂｃ", "abc"))
    text = _RE_SCRIPT.sub("", text)
    text = _RE_TAG.sub("", text)
    text = _RE_FENCE.sub("", text)
    text = _RE_INLINE_CD.sub("", text)
    return text.strip()
 
 
def detect_language(text: str) -> str:
    """Heuristic: count Vietnamese diacritics → 'vi' or 'en'."""
    vi = len(re.findall(r"[àáâãèéêìíòóôõùúýăđơưạảấầẩẫậắặẵằẳ]", text, re.I))
    return "vi" if vi > 2 else "en"
 
 
# =============================================================================
# §5  CUSTOM EXCEPTIONS  ("Hardware fault signals")
# =============================================================================
 
class FuseBlownException(RuntimeError):
    """
    Raised by FinancialFirewall when estimated cost would breach budget.
    Analogous to a main fuse tripping on over-current draw.
    """
    def __init__(self, node: str, current: float, estimated: float, limit: float) -> None:
        self.node      = node
        self.current   = current
        self.estimated = estimated
        self.limit     = limit
        super().__init__(
            f"FUSE_BLOWN [{node}]: ${current:.5f} + ${estimated:.5f} > ${limit:.5f}"
        )
 
 
class InjectionDetectedException(ValueError):
    """Raised by SafetyGatekeeper on prompt-injection signal."""
 
 
class CircuitOpenException(RuntimeError):
    """Raised when the circuit-breaker is open (too many consecutive failures)."""
 
 
class ToolForbiddenException(PermissionError):
    """Raised by ToolSandbox when agent attempts an unauthorised tool call."""
 


# =============================================================================
# §15  SHARED FALLBACK PLACEHOLDER
# =============================================================================
 
_PLACEHOLDER = ContentItem(
    content="[Content unavailable — fallback placeholder]",
    agent="FALLBACK",
)



# =============================================================================
# ┌─────────────────────────────────────────────────────────────────────────┐
# │  NAMESPACE: Infrastructure::PowerManagement                              │
# │  Security, budget enforcement, and model routing.                        │
# │  No execution-unit code lives here.                                      │
# └─────────────────────────────────────────────────────────────────────────┘
# =============================================================================




# =============================================================================
# §3.1  SHIELD INTERFACE PROTOCOL (Giao thức chân cắm Arduino)
# =============================================================================

class ShieldInput(BaseModel):
    """Gói tin đầu vào chuẩn cho linh kiện (Data In)"""
    payload:  dict = Field(default_factory=dict)  # Dữ liệu cần xử lý (VD: Seed)
    config:   dict = Field(default_factory=dict)  # Cấu hình Agent (Role, Goal)
    metadata: dict = Field(default_factory=dict)  # Dữ liệu bổ trợ (SLA, Limits)

class ShieldOutput(BaseModel):
    """Gói tin đầu ra chuẩn từ linh kiện (Data Out)"""
    data:  dict = Field(default_factory=dict)     # Kết quả (VD: Nội dung Ads)
    audit: Optional[NodeAudit] = None             # Nhật ký tiêu thụ


    