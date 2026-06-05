You are a Senior Product Engineer, Marketing Automation Architect, and Staff Backend Engineer.

Your mission is NOT to write code immediately.

Your first mission is to challenge and validate the architecture before implementation.

━━━━━━━━━━━━━━━━━━━━━
PROJECT CONTEXT
━━━━━━━━━━━━━━━━━━━━━

I am building an AI Marketing Automation Platform.

Already completed:

- RAG Pipeline
- LangGraph Workflows
- Blog Agent
- Ads Agent
- Social Agent
- Landing Page Agent
- Image Agent

The only remaining component is:

BRAND PROFILE ENGINE

This engine must serve all workflows.

Target customers:

- SMEs
- Small marketing teams
- Agency clients

Goals:

- Simple
- Practical
- Stable
- Easy to maintain
- High quality content output
- Fast retrieval
- Low token usage

Avoid:

- Enterprise complexity
- Over-engineering
- Excessive metadata
- Academic branding concepts

━━━━━━━━━━━━━━━━━━━━━
FINAL DECISION
━━━━━━━━━━━━━━━━━━━━━

We are NOT using separate:

- BrandVoice
- ConversionProfile
- VisualProfile

Instead we use ONE unified object:

BrandProfile

━━━━━━━━━━━━━━━━━━━━━
CURRENT THINKING
━━━━━━━━━━━━━━━━━━━━━

BrandProfile contains:

1. positioning

What makes the brand different.

2. audience

Who the brand speaks to.

3. forbidden_words

Words that must never be used.

4. content_examples

High quality brand examples.

5. pain_points

Customer pain points.

6. objections

Customer objections.

7. proof_points

Evidence and credibility.

8. cta_examples

Real CTA examples.

9. visual_context

Visual identity for image workflows.

━━━━━━━━━━━━━━━━━━━━━
YOUR TASK
━━━━━━━━━━━━━━━━━━━━━

PHASE 1

Challenge the design.

For every field:

- Why should it exist?
- Why should it be removed?
- Real impact on content quality.
- Real impact on maintenance cost.

Create a table:

Field
Keep / Remove / Merge
Reason

━━━━━━━━━━━━━━━━━━━━━

PHASE 2

Propose the FINAL BrandProfile schema.

Requirements:

- Minimal
- Practical
- Production-ready
- SME-friendly
- Marketing-focused

Do NOT exceed 10 top-level fields.

━━━━━━━━━━━━━━━━━━━━━

PHASE 3

Design data flow.

Show:

RAG
↓
Mining
↓
BrandProfile
↓
SQLite
↓
Compile
↓
LangGraph

Explain each step.

━━━━━━━━━━━━━━━━━━━━━

PHASE 4

Design runtime scopes.

Example:

Writer Scope

Designer Scope

Ads Scope

Landing Page Scope

For each scope:

- Which fields are required?
- Which fields should be excluded?

Explain why.

━━━━━━━━━━━━━━━━━━━━━

PHASE 5

Design database models.

Do NOT write code.

Only describe:

Tables
Columns
Relationships

Requirements:

- SQLite
- Async SQLAlchemy
- Single developer maintenance
- Low complexity

━━━━━━━━━━━━━━━━━━━━━

PHASE 6

Design API.

Do NOT write code.

Describe endpoints only.

Examples:

POST /brand-profile/mine

GET /brand-profile/{brand_id}

PUT /brand-profile/{brand_id}

GET /brand-profile/{brand_id}/scope/writer

GET /brand-profile/{brand_id}/scope/designer

Explain each endpoint.

━━━━━━━━━━━━━━━━━━━━━

PHASE 7

Failure Analysis

List:

- Runtime risks
- Data consistency risks
- Prompt injection risks
- PII risks
- Stale profile risks

For each:

- Risk level
- Mitigation
- Complexity cost

━━━━━━━━━━━━━━━━━━━━━

PHASE 8

FINAL VERDICT

Output:

1. Final BrandProfile schema.
2. Final database design.
3. Final runtime architecture.
4. Fields that must be deleted from the old system.
5. Migration strategy from old BrandVoice system.
6. Production readiness score.

IMPORTANT:

Do NOT write implementation code.

Do NOT write SQLAlchemy models.

Do NOT write FastAPI routes.

Architecture and design only.
Challenge assumptions aggressively.
Prioritize simplicity over cleverness.