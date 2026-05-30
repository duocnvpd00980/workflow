=======================================================================
MAINBOARD NODE PROTOCOL — REV 2.0
AgentOS / LangGraph Infrastructure · Node Development Standard
Applies to: all Node authors (human & AI) · MANDATORY COMPLIANCE
=======================================================================

ART. 1  INFRASTRUCTURE AXIOMS
───────────────────────────────────────────────────────────────────────
1.1  Runtime
     All Nodes execute on a LangGraph graph.
     Communication is exclusively via the `MainBus` State Object.
     No side-channels permitted.

1.2  Dependency Injection
     All engines MUST be obtained via the central Container.
     Direct instantiation is forbidden.

       ctx   = await get_ctx()
       llm   = ctx.llm_factory.get_model("default")
       embed = ctx.llm_factory.get_embedding("default_embed")

1.3  Output Contract
     Every Node MUST return exactly one StandardFrame.emit() call.
     No raw dict, no custom object, no bare return.

       return StandardFrame.emit(
           registry_key=BusRegistry.[KEY],
           payload=BodyFrame(...)
       )

ART. 2  3-FILE STRUCTURE  [IMMUTABLE]
───────────────────────────────────────────────────────────────────────
①  _protocol.py
   Pydantic Model only.
   Config: ConfigDict(frozen=True, extra="ignore")
   This is the sole output contract of the Node. No logic.

②  _service.py
   Input:  raw primitives (str, int, list)
   Logic:  pure domain only
   Output: MUST return the Pydantic Object from _protocol.py
   VIOLATION: returning dict

③  adapter_.py
   Input:  state: MainBus
   Role:   executes the 4-Step Pipeline (Art. 3)
   Constraint: only file that touches the Bus

ART. 3  ADAPTER 4-STEP PIPELINE  [FIXED EXECUTION ORDER]
───────────────────────────────────────────────────────────────────────
S1  SAFE POST-GUARD
    Assert: state.reg_prev_node exists AND payload.status == "SUCCESS"
    On violation → emit immediately:
      StandardFrame.emit(status="FAILED", error="<detail>")
    PROHIBITED: raise · RuntimeError · any exception propagation
    REQUIRED:   graph continues (Graceful Degradation)

S2  CONTEXT EXTRACTION & DEPENDENCY INJECTION
    Extract data via dot-notation only: state.reg_X.payload.text
    Inject engines via: await get_ctx()
    PROHIBITED: dict access · string parsing on Bus data

S3  PURE DOMAIN EXECUTION
    Call Service module with raw primitives.
    Receive frozen Pydantic Object.
    PROHIBITED: business logic inside the Adapter

S4  STATUS NORMALIZATION & EMIT
    Derive status from Pydantic result.
    Construct BodyFrame. Emit one StandardFrame.
    No code executes after this line.

ART. 4  BODYFRAME SCHEMA  [NON-NEGOTIABLE]
───────────────────────────────────────────────────────────────────────
Field       Type            Requirement     Rule
─────────── ─────────────── ─────────────── ───────────────────────────
status      SUCCESS|FAILED  REQUIRED        Exactly one of three values.
            |EMPTY
text        str             REQUIRED        UI output. Single source of
                                            truth. Never duplicated.
records     list[Model]     OPTIONAL        Empty list [] when unused.
entities    list[dict]      OPTIONAL        Extracted named entities.
state       dict            OPTIONAL        Runtime flags only.
                                            No nested schemas.
metrics     dict            OPTIONAL        System observability only.
context     dict            OPTIONAL        Debug/trace. Not read by
                                            downstream Nodes.
error       str | None      FAILED ONLY     None on SUCCESS.
                                            Populated on FAILED.

PROHIBITED:
  · Any field outside this schema
  · Nested Pydantic models inside state / context / metrics
  · Returning any object other than BodyFrame

ART. 5  CERTIFIED DOCSTRING  [MANDATORY — FIRST LINE OF EVERY ADAPTER]
───────────────────────────────────────────────────────────────────────
"""
=======================================================================
CERTIFIED PROTOCOL WORKFLOW: [NODE_NAME]
=======================================================================
BUSINESS INTENT
  [One sentence: what business outcome does this Node produce?]

UPSTREAM DEPENDENCY
  Reads from : state.reg_[PREV_NODE]
  Emits to   : BusRegistry.[THIS_NODE_KEY]

WORKFLOW PIPELINE
  S1 Safe Post-Guard         — Validate upstream. Emit FAILED, never raise.
  S2 Context Extraction & DI — Dot-notation extraction. get_ctx() injection.
  S3 Pure Domain Execution   — Service call. Receive frozen Pydantic Object.
  S4 Status Normalization    — Derive status. Emit single StandardFrame.
=======================================================================
"""

ART. 6  YOUR TASK
───────────────────────────────────────────────────────────────────────
Apply Arts. 1–5 without deviation.
Produce exactly 3 files: _protocol.py · _service.py · adapter_.py

Node specification:
[Mô tả Node cần tạo hoặc sửa ở đây]