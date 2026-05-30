from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# STDLIB
# ─────────────────────────────────────────────────────────────────────────────
import asyncio
from pydantic import BaseModel, ConfigDict

from agent_os.system.core_protocol import (
    _INJECTION_SIGNALS,
    ToolCallRecord,
    ToolForbiddenException,
    _emit,
)

# =============================================================================
# §9  KILL SWITCH
# =============================================================================


class KillSwitch:
    def __init__(self) -> None:
        self._active = False
        self._lock = asyncio.Lock()

    def trip(self) -> None:
        self._active = True
        _emit("critical", event="kill_switch_tripped")

    def reset(self) -> None:
        self._active = False

    @property
    def tripped(self) -> bool:
        return self._active


KILL_SWITCH = KillSwitch()


# =============================================================================
# §10  TOOL SANDBOX
# =============================================================================


class ToolPermission(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_id: str
    allowed_tools: frozenset[str] = frozenset()
    max_query_len: int = 500
    max_calls: int = 3

    def can_use(self, tool: str) -> bool:
        return tool in self.allowed_tools


_TOOL_PERMISSIONS: dict[str, ToolPermission] = {
    "BLOG_WRITER": ToolPermission(
        agent_id="BLOG_WRITER",
        allowed_tools=frozenset({"web_search"}),
        max_query_len=300,
        max_calls=2,
    ),
    "BLOG_PLANNER": ToolPermission(
        agent_id="BLOG_PLANNER",
        allowed_tools=frozenset({"web_search"}),
        max_query_len=200,
        max_calls=1,
    ),
}
_DEFAULT_PERM = ToolPermission(agent_id="__default__")


def _get_perm(agent_id: str) -> ToolPermission:
    return _TOOL_PERMISSIONS.get(agent_id, _DEFAULT_PERM)


def validate_tool_call(
    agent_id: str,
    tool_name: str,
    query: str,
    call_history: list[ToolCallRecord],
) -> None:
    """
    Three-layer sandbox validation.
    Raises ToolForbiddenException on any violation (never returns False).
    """
    perm = _get_perm(agent_id)

    # Layer 1 — permission
    if not perm.can_use(tool_name):
        raise ToolForbiddenException(
            f"{agent_id} is not permitted to use '{tool_name}'"
        )

    # Layer 2 — input hygiene
    if not query.strip():
        raise ToolForbiddenException("EMPTY_QUERY")
    if len(query) > perm.max_query_len:
        raise ToolForbiddenException(
            f"QUERY_TOO_LONG: {len(query)} > {perm.max_query_len}"
        )
    for sig in _INJECTION_SIGNALS:
        if sig in query.lower():
            raise ToolForbiddenException(f"INJECTION_IN_QUERY: '{sig}'")

    # Layer 3 — rate cap
    calls = [r for r in call_history if r.agent_id == agent_id]
    if len(calls) >= perm.max_calls:
        raise ToolForbiddenException(
            f"TOOL_RATE_CAP: {agent_id} exceeded {perm.max_calls} calls"
        )


# =============================================================================
# §13  AGENT CONFIG REGISTRY
# =============================================================================


class AgentConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    agent_id: str
    role: str
    goal: str
    backstory: str
    output_schema_hint: str
    temperature: float = 0.3


AGENT_REGISTRY: dict[str, AgentConfig] = {
    "BLOG_PLANNER": AgentConfig(
        agent_id="BLOG_PLANNER",
        role="Senior Content Strategist",
        goal="Build a detailed, language-correct blog outline from the campaign brief.",
        backstory="10 years top-tier agency; believes success starts with a sharp outline.",
        output_schema_hint=(
            '{"title":"<headline>","sections":"Intro|Problem|Solution|CTA",'
            '"key_points":"<comma-sep>","word_target":300}'
        ),
        temperature=0.25,
    ),
    "BLOG_WRITER": AgentConfig(
        agent_id="BLOG_WRITER",
        role="Creative Copywriter",
        goal="Turn an outline into a full blog post with a clear CTA.",
        backstory="Wrote for major SEA brands; blends data and emotion.",
        output_schema_hint='{"content":"<full post>","has_cta":true}',
        temperature=0.5,
    ),
    "BLOG_EDITOR": AgentConfig(
        agent_id="BLOG_EDITOR",
        role="Brand Manager / Senior Critic",
        goal="Ruthlessly review drafts; reject on tone/CTA/style issues.",
        backstory="Motto: 'Rewrite before publishing anything mediocre'.",
        output_schema_hint=(
            '{"is_approved":false,"feedback":"<reason>","content":"<revised if approved>"}'
        ),
        temperature=0.1,
    ),
    "VALIDATOR": AgentConfig(
        agent_id="VALIDATOR",
        role="QA Referee",
        goal="Score content on rubric (length, CTA, tone, language); decide pass/retry.",
        backstory="NLP-background QA specialist — metrics only, no sentiment.",
        output_schema_hint=(
            '{"passed":true,"score":0.9,"issues":"","needs_retry":false,"retry_reason":""}'
        ),
        temperature=0.0,
    ),
    "AGENT_ADS": AgentConfig(
        agent_id="AGENT_ADS",
        role="Performance Marketer",
        goal="Write concise ad copy — strong hook, pain-point focus, direct CTA.",
        backstory="Lives by ROAS and CTR. Uses PAS framework.",
        output_schema_hint='{"content":"<ad copy>","has_cta":true}',
        temperature=0.4,
    ),
    "AGENT_EMAIL": AgentConfig(
        agent_id="AGENT_EMAIL",
        role="CRM Specialist",
        goal="Write a personalised marketing email — curiosity subject line, natural CTA.",
        backstory="Email is highest ROI if done right. Always writes to one person.",
        output_schema_hint='{"content":"<email with subject>","has_cta":true}',
        temperature=0.4,
    ),
}
