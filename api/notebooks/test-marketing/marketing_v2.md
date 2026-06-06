# CONTENT FACTORY PRO — StoryBrand + PAS + AIDA
# Version 2: Hybrid Language (EN system prompts, VI data, configurable output)

---

```python
# ═══════════════════════════════════════════════════════════════
# CELL 1: IMPORTS & SETUP
# ═══════════════════════════════════════════════════════════════
import os, json, time, requests
from typing import TypedDict, List, Optional, Dict, Any
from datetime import datetime

# ── Groq API Config ──
GROQ_API_KEY = "YOUR_GROQ_API_KEY"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "meta-llama/llama-4-scout-17b-16e-instruct"

MAX_RETRIES  = 6
BASE_DELAY   = 20

# ── Token Tracker ──
_tracker = {"prompt": 0, "completion": 0, "calls": 0}
PRICE_INPUT  = 0.11   # USD / 1M tokens
PRICE_OUTPUT = 0.34

def reset_tracker():
    _tracker["prompt"] = _tracker["completion"] = _tracker["calls"] = 0

def print_token_summary():
    p, c, n = _tracker["prompt"], _tracker["completion"], _tracker["calls"]
    cost = (p * PRICE_INPUT + c * PRICE_OUTPUT) / 1_000_000
    print(f"""
╔══════════════════════════════════════╗
║       TOKEN & COST SUMMARY           ║
╠══════════════════════════════════════╣
║  API calls  : {n:>6}                 ║
║  Prompt     : {p:>6} tokens          ║
║  Completion : {c:>6} tokens          ║
║  Total      : {p+c:>6} tokens        ║
║  Est. cost  : ${cost:.6f} USD        ║
╚══════════════════════════════════════╝""")

def groq_chat(system_prompt: str, user_prompt: str,
              temperature: float = 0.6, max_tokens: int = 1000) -> str:
    """Call Groq API with auto-retry on 429/503"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "temperature": temperature,
        "max_completion_tokens": max_tokens,
        "top_p": 0.95,
        "stream": False,
    }

    for attempt in range(MAX_RETRIES):
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=120)

        if response.status_code == 200:
            data  = response.json()
            usage = data.get("usage", {})
            p_tok = usage.get("prompt_tokens", 0)
            c_tok = usage.get("completion_tokens", 0)
            _tracker["prompt"]     += p_tok
            _tracker["completion"] += c_tok
            _tracker["calls"]      += 1
            print(f"  ✓ +{p_tok}p +{c_tok}c (total {_tracker['prompt']+_tracker['completion']})")
            return data["choices"][0]["message"]["content"]

        elif response.status_code in (429, 503):
            retry_after = response.headers.get("Retry-After")
            wait = int(retry_after) if retry_after else BASE_DELAY * (2 ** attempt)
            print(f"  ⏳ {response.status_code} — chờ {wait}s (lần {attempt+1}/{MAX_RETRIES})...")
            time.sleep(wait)

        else:
            response.raise_for_status()

    raise RuntimeError(f"❌ Thất bại sau {MAX_RETRIES} lần thử.")

print("✅ Cell 1: Setup hoàn tất")
```

---

```python
# ═══════════════════════════════════════════════════════════════
# CELL 2: STATE & TEST BRIEF
# ═══════════════════════════════════════════════════════════════

class ContentFactoryState(TypedDict):
    client_brief:         Dict[str, Any]
    content_brief:        Optional[Dict[str, Any]]
    research_data:        Optional[Dict[str, Any]]
    long_form_draft:      Optional[str]
    social_copies:        Optional[Dict[str, Any]]
    visual_prompts:       Optional[List[str]]
    seo_optimized_content: Optional[Dict[str, Any]]
    qa_score:             Optional[float]
    qa_feedback:          Optional[str]
    approved_content:     Optional[Dict[str, Any]]
    distribution_plan:    Optional[Dict[str, Any]]
    performance_metrics:  Optional[Dict[str, Any]]
    optimization_notes:   Optional[str]
    current_step:         str
    retry_count:          int

TEST_BRIEF = {
    "brand_name":    "TechStart Vietnam",
    "product":       "Phần mềm quản lý dự án AI cho startup",
    "target_audience": "Founder startup Việt Nam, 25-40 tuổi, tech-savvy",
    "goal":          "Tăng sign-up trial 200% trong Q3",
    "tone":          "Chuyên nghiệp nhưng gần gũi, data-driven, có chút humor",
    "channels":      ["blog", "linkedin", "email", "twitter"],
    "content_type":  "long_form_blog",
    "word_count":    2500,
    "keywords":      ["AI project management", "startup tools Vietnam", "quản lý dự án AI"],
    "competitors":   ["Notion", "Asana", "Monday.com"],
    "brand_voice_examples": [
        "Chúng tôi không bán phần mềm. Chúng tôi bán thời gian.",
        "Startup không cần thêm công cụ. Startup cần ít công cụ hơn, hiệu quả hơn."
    ],
    "output_language": "Vietnamese",   # ← đổi sang "English" nếu cần
}

print("✅ Cell 2: State & Test Brief định nghĩa xong")
```

---

```python
# ═══════════════════════════════════════════════════════════════
# CELL 2.5: MOCK DATA — Competitor Research + Brand Voice RAG
# Swap ra real scraper + vector DB khi sẵn sàng
# ═══════════════════════════════════════════════════════════════

MOCK_COMPETITOR_DATA = {
    "keyword": "phần mềm quản lý dự án",
    "serp_top10": [
        {
            "rank": 1, "url": "https://asana.com/vi",
            "title": "Asana: Quản lý công việc nhóm hiệu quả",
            "word_count": 2400,
            "headings": ["Tại sao chọn Asana?", "Tính năng nổi bật", "Bắt đầu miễn phí"],
            "pain_points": ["deadline trễ", "team không sync", "báo cáo thủ công"],
            "cta": "Dùng thử miễn phí 30 ngày"
        },
        {
            "rank": 2, "url": "https://monday.com/vi",
            "title": "monday.com — Nền tảng quản lý việc làm",
            "word_count": 1900,
            "headings": ["Quản lý mọi dự án", "Tích hợp 200+ app", "Báo cáo realtime"],
            "pain_points": ["khó theo dõi tiến độ", "quá nhiều tool rời rạc", "tốn thời gian họp"],
            "cta": "Bắt đầu miễn phí"
        },
        {
            "rank": 3, "url": "https://notion.so/vi",
            "title": "Notion — All-in-one workspace",
            "word_count": 1600,
            "headings": ["Docs + Tasks + Wiki", "Cho team mọi quy mô", "Template sẵn có"],
            "pain_points": ["thông tin phân tán", "không có workflow chuẩn", "onboarding lâu"],
            "cta": "Dùng Notion miễn phí"
        }
    ],
    "avg_word_count": 1967,
    "common_sections": ["Hook/Problem", "Tính năng", "Social Proof", "Pricing", "CTA"],
    "content_gaps": [
        "Không ai nói về ROI cụ thể cho startup Việt",
        "Thiếu case study tiếng Việt",
        "Không có so sánh chi phí bằng VND"
    ]
}

MOCK_BRAND_VOICE = {
    "brand_name": "TechStart Vietnam",
    "retrieved_chunks": [
        {
            "source": "website_homepage.txt", "score": 0.95,
            "content": "TechStart giúp founder startup Việt kiểm soát dự án như một CEO thực thụ — không cần MBA, không cần team lớn."
        },
        {
            "source": "sample_blog_post.txt", "score": 0.91,
            "content": "Chúng tôi không bán phần mềm. Chúng tôi bán sự yên tâm khi bạn biết team đang đi đúng hướng."
        },
        {
            "source": "social_media_posts.txt", "score": 0.88,
            "content": "Tone: thẳng thắn, không hoa mỹ. Dùng số liệu cụ thể. Tránh buzzword. Nói chuyện như người bạn có chuyên môn."
        },
        {
            "source": "email_campaign.txt", "score": 0.85,
            "content": "CTA luôn rõ ràng, một hành động duy nhất. Không bao giờ dùng 'Tìm hiểu thêm' — dùng 'Xem demo 5 phút' hoặc 'Thử ngay hôm nay'."
        }
    ],
    "voice_summary": "Thẳng thắn, dùng số liệu, không hoa mỹ, gần gũi như người bạn có chuyên môn"
}

def mock_competitor_research(keyword: str = None) -> dict:
    print(f"  [MOCK] Competitor research: {len(MOCK_COMPETITOR_DATA['serp_top10'])} competitors")
    return MOCK_COMPETITOR_DATA

def mock_brand_voice_rag(query: str = None) -> dict:
    print(f"  [MOCK] RAG retrieved: {len(MOCK_BRAND_VOICE['retrieved_chunks'])} chunks")
    return MOCK_BRAND_VOICE

print("✅ Cell 2.5: Mock Competitor + Brand Voice RAG sẵn sàng")
```

---

```python
# ═══════════════════════════════════════════════════════════════
# CELL 3: NODE 1 — STRATEGIST AGENT
# ═══════════════════════════════════════════════════════════════

STRATEGIST_SYSTEM_PROMPT = """You are a Chief Content Strategist trained in StoryBrand (Donald Miller) and PAS frameworks.

Apply the StoryBrand 7-part framework + PAS problem identification to create a content brief.

Return ONLY valid JSON — no explanation, no markdown:
{
  "storybrand_framework": {
    "hero": "customer description (not the brand)",
    "external_problem": "surface-level problem",
    "internal_problem": "emotional/deeper problem",
    "philosophical_problem": "bigger life problem",
    "guide": "how brand acts as guide",
    "empathy": "how brand understands hero",
    "authority": "brand credentials",
    "plan": ["Step 1", "Step 2", "Step 3"],
    "direct_cta": "primary action",
    "transitional_cta": "lower-commitment action",
    "failure_stakes": "what happens if hero doesn't act",
    "success_vision": "transformation after using the product"
  },
  "pas_framework": {
    "problem_statement": "clear problem statement",
    "agitation_points": ["pain point 1", "pain point 2", "pain point 3"],
    "solution_intro": "how product solves it"
  },
  "title": "StoryBrand + PAS optimized title",
  "content_angle": "unique differentiation angle"
}"""

def strategist_node(state: ContentFactoryState):
    """Node 1: StoryBrand + PAS Strategy"""
    client = state["client_brief"]
    lang   = client.get("output_language", "Vietnamese")

    user_prompt = f"""CLIENT BRIEF:
Brand: {client['brand_name']}
Product: {client['product']}
Target Audience: {client['target_audience']}
Goal: {client['goal']}
Keywords: {', '.join(client['keywords'])}
Competitors: {', '.join(client['competitors'])}
Brand Voice Examples: {client['brand_voice_examples']}

Output language: {lang}
Return ONLY JSON."""

    response = groq_chat(STRATEGIST_SYSTEM_PROMPT, user_prompt, temperature=0.7, max_tokens=1200)

    try:
        content_brief = json.loads(response.replace("```json", "").replace("```", "").strip())
    except:
        content_brief = {"raw_response": response[:300], "parse_error": True}

    return {**state, "content_brief": content_brief, "current_step": "research"}

print("✅ Cell 3: Strategist Node định nghĩa xong")
```

---

```python
# ═══════════════════════════════════════════════════════════════
# CELL 4: NODE 2 — RESEARCHER AGENT
# ═══════════════════════════════════════════════════════════════

RESEARCHER_SYSTEM_PROMPT = """You are a Senior Research Analyst specializing in pain point mining for conversion copywriting.

Synthesize competitor insights and brand voice data to support StoryBrand + PAS frameworks.

Return ONLY valid JSON:
{
  "pain_points": [
    {"pain": "...", "frequency": "high|medium|low", "emotional_intensity": 8, "source": "..."}
  ],
  "competitor_gaps": [
    {"competitor": "...", "gap": "...", "opportunity": "..."}
  ],
  "proof_data": {
    "statistics": [{"claim": "...", "source": "...", "year": 2024}],
    "case_studies": [{"company": "...", "before": "...", "after": "...", "metric": "..."}],
    "testimonials": [{"quote": "...", "persona": "..."}]
  },
  "emotional_triggers": ["trigger 1", "trigger 2"],
  "common_objections": [{"objection": "...", "reframe": "..."}],
  "voice_of_customer": ["how customers actually say it 1", "way 2"]
}"""

def researcher_node(state: ContentFactoryState):
    """Node 2: Pain Point Mining & Proof Gathering"""
    brief  = state.get("content_brief") or {}
    client = state["client_brief"]
    lang   = client.get("output_language", "Vietnamese")

    # ── Mock data (swap to real system when ready) ──
    competitor_data = mock_competitor_research()
    brand_voice     = mock_brand_voice_rag()

    storybrand = brief.get("storybrand_framework", {})
    all_pain_points = [p for c in competitor_data['serp_top10'] for p in c['pain_points']][:6]

    user_prompt = f"""STORYBRAND CONTEXT:
Hero: {storybrand.get('hero', 'N/A')}
External Problem: {storybrand.get('external_problem', 'N/A')}

COMPETITOR INSIGHTS (from SERP):
Content gaps: {competitor_data['content_gaps']}
Common pain points: {all_pain_points}

BRAND VOICE (from RAG):
Voice summary: {brand_voice['voice_summary']}
{chr(10).join([f"- {c['content']}" for c in brand_voice['retrieved_chunks']])}

Competitors: {', '.join(client.get('competitors', []))}

Output language: {lang}
Return ONLY JSON."""

    response = groq_chat(RESEARCHER_SYSTEM_PROMPT, user_prompt, temperature=0.6, max_tokens=800)

    try:
        research_data = json.loads(response.replace("```json", "").replace("```", "").strip())
        # Store brand voice so creation_node can use it directly
        research_data["_brand_voice"] = brand_voice
        research_data["_competitor_gaps"] = competitor_data["content_gaps"]
    except:
        research_data = {"raw_response": response[:300], "parse_error": True,
                         "_brand_voice": brand_voice,
                         "_competitor_gaps": competitor_data["content_gaps"]}

    return {**state, "research_data": research_data, "current_step": "creation"}

print("✅ Cell 4: Researcher Node định nghĩa xong")
```

---

```python
# ═══════════════════════════════════════════════════════════════
# CELL 5: NODE 3 — CREATION AGENT
# ═══════════════════════════════════════════════════════════════

WRITER_SYSTEM_PROMPT = """You are a Conversion Copywriter trained in StoryBrand, PAS, and AIDA frameworks.

Write long-form content following this exact 8-section structure:
SECTION 1: HOOK (AIDA Attention) — pattern interrupt, bold claim or story opening
SECTION 2: PROBLEM (PAS) — external + internal + philosophical problem
SECTION 3: AGITATE (PAS) — amplify pain, add urgency, make it personal
SECTION 4: MEET THE GUIDE (StoryBrand) — empathy + authority + transition to product
SECTION 5: THE PLAN (StoryBrand) — 3 clear steps, address objections
SECTION 6: PROOF (AIDA Desire) — case study with numbers, testimonials, before/after
SECTION 7: CTA (AIDA Action + StoryBrand) — direct CTA + transitional CTA + urgency
SECTION 8: SUCCESS VISION (StoryBrand) — transformation, future pacing, close the loop

RULES:
- Use "You/Bạn" 2x more than "We/Chúng tôi"
- Max 3-4 lines per paragraph
- Apply brand voice rules exactly as provided
- Address every content gap listed"""

COPYWRITER_SYSTEM_PROMPT = """You are a Social Media Copywriter.
Create platform-specific copies from long-form content.
Return ONLY valid JSON:
{"linkedin": "150-200 word professional post", "twitter": "5-tweet thread", "instagram": "storytelling caption with 5 hashtags", "email": {"subject": "curiosity gap subject", "body": "150-word email body"}}"""

DESIGNER_SYSTEM_PROMPT = """You are a Visual Content Strategist.
Create image prompts following StoryBrand visual rules — hero is the customer, not the product.
Return ONLY valid JSON list:
[{"section": "section name", "prompt": "detailed image prompt", "style": "photography|illustration|infographic"}]"""

def creation_node(state: ContentFactoryState):
    """Node 3: PAS + AIDA + StoryBrand Content Creation"""
    brief    = state.get("content_brief") or {}
    research = state.get("research_data") or {}
    client   = state["client_brief"]
    lang     = client.get("output_language", "Vietnamese")

    # ── Pull brand voice + gaps from research (set by researcher_node) ──
    brand_voice     = research.get("_brand_voice", MOCK_BRAND_VOICE)
    competitor_gaps = research.get("_competitor_gaps", MOCK_COMPETITOR_DATA["content_gaps"])
    pain_points     = [p["pain"] for p in research.get("pain_points", [])[:4]]
    storybrand      = brief.get("storybrand_framework", {})
    pas             = brief.get("pas_framework", {})

    # 3A: Long-form Writer
    writer_prompt = f"""STORYBRAND FRAMEWORK:
Hero: {storybrand.get('hero', 'N/A')}
External Problem: {storybrand.get('external_problem', 'N/A')}
Internal Problem: {storybrand.get('internal_problem', 'N/A')}
Guide: {storybrand.get('guide', 'N/A')}
Plan: {storybrand.get('plan', [])}
Direct CTA: {storybrand.get('direct_cta', 'N/A')}
Failure Stakes: {storybrand.get('failure_stakes', 'N/A')}
Success Vision: {storybrand.get('success_vision', 'N/A')}

PAS FRAMEWORK:
Problem: {pas.get('problem_statement', 'N/A')}
Agitation: {pas.get('agitation_points', [])}

RESEARCH — Pain Points: {pain_points}

BRAND VOICE RULES (mandatory — apply exactly):
Voice: {brand_voice.get('voice_summary', 'N/A')}
{chr(10).join([f"- {c['content']}" for c in brand_voice.get('retrieved_chunks', [])])}

CONTENT GAPS TO ADDRESS (differentiate from competitors):
{chr(10).join([f"- {g}" for g in competitor_gaps])}

Output language: {lang}
Write all 8 sections with clear headings."""

    long_form = groq_chat(WRITER_SYSTEM_PROMPT, writer_prompt, temperature=0.7, max_tokens=1500)

    # 3B: Social Copywriter
    copy_prompt = f"""LONG-FORM CONTENT SUMMARY:
Title: {brief.get('title', 'N/A')}
Hook (first 400 chars): {long_form[:400]}
Brand voice: {brand_voice.get('voice_summary', 'N/A')}
Direct CTA: {storybrand.get('direct_cta', 'N/A')}

Output language: {lang}
Return ONLY JSON."""

    copy_response = groq_chat(COPYWRITER_SYSTEM_PROMPT, copy_prompt, temperature=0.7, max_tokens=500)
    try:
        social_copies = json.loads(copy_response.replace("```json", "").replace("```", "").strip())
    except:
        social_copies = {"raw": copy_response[:200]}

    # 3C: Visual Prompts
    design_prompt = f"""Content title: {brief.get('title', 'N/A')}
Hero persona: {storybrand.get('hero', 'N/A')}
Success vision: {storybrand.get('success_vision', 'N/A')}
Create 5 image prompts. Return ONLY JSON list."""

    design_response = groq_chat(DESIGNER_SYSTEM_PROMPT, design_prompt, temperature=0.7, max_tokens=400)
    try:
        visual_prompts = json.loads(design_response.replace("```json", "").replace("```", "").strip())
    except:
        visual_prompts = [design_response[:200]]

    return {**state, "long_form_draft": long_form, "social_copies": social_copies,
            "visual_prompts": visual_prompts, "current_step": "seo"}

print("✅ Cell 5: Creation Node định nghĩa xong")
```

---

```python
# ═══════════════════════════════════════════════════════════════
# CELL 6: NODE 4 — SEO OPTIMIZER
# ═══════════════════════════════════════════════════════════════

SEO_SYSTEM_PROMPT = """You are a Technical SEO Expert specializing in StoryBrand content optimization.

Optimize the provided content for search engines while preserving StoryBrand + PAS structure.

Return ONLY valid JSON:
{
  "title_tag": "primary keyword + power word (max 60 chars)",
  "meta_description": "PAS agitation point + CTA (max 155 chars)",
  "header_structure": ["H1: hero statement", "H2: section names"],
  "keyword_placement": {"primary": "placement notes", "secondary": ["kw1", "kw2"]},
  "optimized_intro": "first 150 words with keyword in first 100",
  "schema_type": "Article"
}"""

def seo_optimizer_node(state: ContentFactoryState):
    """Node 4: SEO Optimization"""
    draft  = state.get("long_form_draft") or ""
    brief  = state.get("content_brief") or {}
    client = state["client_brief"]
    lang   = client.get("output_language", "Vietnamese")

    user_prompt = f"""CONTENT (first 1500 chars):
{draft[:1500]}

PRIMARY KEYWORD: {client['keywords'][0] if client.get('keywords') else 'N/A'}
SECONDARY KEYWORDS: {', '.join(client.get('keywords', [])[1:])}
TITLE SUGGESTION: {brief.get('title', 'N/A')}

Output language: {lang}
Return ONLY JSON."""

    response = groq_chat(SEO_SYSTEM_PROMPT, user_prompt, temperature=0.5, max_tokens=600)

    try:
        seo_data = json.loads(response.replace("```json", "").replace("```", "").strip())
    except:
        seo_data = {"raw_response": response[:300], "parse_error": True}

    return {**state, "seo_optimized_content": seo_data, "current_step": "qa"}

print("✅ Cell 6: SEO Optimizer Node định nghĩa xong")
```

---

```python
# ═══════════════════════════════════════════════════════════════
# CELL 7: NODE 5 — QUALITY ASSURANCE
# ═══════════════════════════════════════════════════════════════

EDITOR_SYSTEM_PROMPT = """You are a Chief Editor specialized in StoryBrand, PAS, and AIDA compliance.

Score the content on framework compliance (0-10 each):
- storybrand_score: hero clarity, guide positioning, 3-step plan, CTA presence, success vision
- pas_score: problem clarity, agitation strength, solution positioning
- aida_score: attention hook, interest flow, desire building, action clarity

Return ONLY valid JSON:
{
  "storybrand_score": 8,
  "pas_score": 7,
  "aida_score": 8,
  "overall_score": 7.7,
  "verdict": "APPROVED|CONDITIONAL|REJECT",
  "feedback": {
    "strengths": ["strength 1", "strength 2"],
    "weaknesses": ["weakness 1"],
    "action_items": ["fix 1"]
  },
  "storybrand_improvements": ["improvement 1", "improvement 2"],
  "pas_improvements": ["improvement 1"],
  "aida_improvements": ["improvement 1"]
}"""

def qa_node(state: ContentFactoryState):
    """Node 5: Framework Compliance QA"""
    seo_content = state.get("seo_optimized_content") or {}
    social      = state.get("social_copies") or {}
    draft       = state.get("long_form_draft") or ""

    user_prompt = f"""CONTENT DRAFT (first 1000 chars):
{draft[:1000]}

SEO DATA: {json.dumps(seo_content, ensure_ascii=False)[:500]}
SOCIAL COPIES: {json.dumps(social, ensure_ascii=False)[:300]}

Evaluate framework compliance. Return ONLY JSON."""

    response = groq_chat(EDITOR_SYSTEM_PROMPT, user_prompt, temperature=0.3, max_tokens=600)

    try:
        qa_result = json.loads(response.replace("```json", "").replace("```", "").strip())
    except:
        qa_result = {"overall_score": 0, "verdict": "REJECT", "raw": response[:200]}

    overall = qa_result.get("overall_score", 0)

    return {**state,
            "qa_score":   overall,
            "qa_feedback": qa_result,
            "optimization_notes": {
                "storybrand_improvements": qa_result.get("storybrand_improvements", []),
                "pas_improvements":        qa_result.get("pas_improvements", []),
                "aida_improvements":       qa_result.get("aida_improvements", []),
            },
            "current_step": "distribute"}

print("✅ Cell 7: QA Node định nghĩa xong")
```

---

```python
# ═══════════════════════════════════════════════════════════════
# CELL 8: NODE 6 — DISTRIBUTION
# ═══════════════════════════════════════════════════════════════

DISTRIBUTOR_SYSTEM_PROMPT = """You are a Content Distribution Strategist.
Create a distribution plan for StoryBrand + PAS + AIDA content across multiple channels.

Return ONLY valid JSON:
{
  "distribution_timeline": [
    {"day": 0, "channel": "blog", "action": "publish full article", "hook": "..."},
    {"day": 1, "channel": "linkedin", "action": "hero-focused post", "hook": "..."},
    {"day": 2, "channel": "twitter", "action": "PAS thread", "hook": "..."},
    {"day": 3, "channel": "email", "action": "personal story CTA", "hook": "..."},
    {"day": 7, "channel": "repurpose", "action": "short video script", "hook": "..."},
    {"day": 14, "channel": "follow-up", "action": "case study post", "hook": "..."}
  ],
  "ab_test_plan": {"variable": "...", "variant_a": "...", "variant_b": "..."},
  "tracking_setup": {"utm_source": "...", "utm_campaign": "..."}
}"""

def distributor_node(state: ContentFactoryState):
    """Node 6: Distribution Planning"""
    approved = state.get("approved_content") or {}
    client   = state["client_brief"]
    lang     = client.get("output_language", "Vietnamese")
    seo      = approved.get("seo") or state.get("seo_optimized_content") or {}

    user_prompt = f"""CONTENT TITLE: {seo.get('title_tag', 'N/A')}
META: {seo.get('meta_description', 'N/A')}
CHANNELS: {', '.join(client.get('channels', []))}
GOAL: {client.get('goal', 'N/A')}

Output language: {lang}
Return ONLY JSON."""

    response = groq_chat(DISTRIBUTOR_SYSTEM_PROMPT, user_prompt, temperature=0.6, max_tokens=600)

    try:
        dist_plan = json.loads(response.replace("```json", "").replace("```", "").strip())
    except:
        dist_plan = {"raw": response[:200]}

    return {**state, "distribution_plan": dist_plan, "current_step": "analytics"}

print("✅ Cell 8: Distribution Node định nghĩa xong")
```

---

```python
# ═══════════════════════════════════════════════════════════════
# CELL 9: NODE 7 — ANALYTICS & FEEDBACK
# ═══════════════════════════════════════════════════════════════

ANALYST_SYSTEM_PROMPT = """You are a Marketing Analytics Expert.
Create a KPI tracking framework for StoryBrand + PAS + AIDA content performance.

Return ONLY valid JSON:
{
  "kpis": {
    "hook_metrics":    {"scroll_depth": "target %", "time_on_page": "target sec"},
    "pas_metrics":     {"comment_sentiment": "target", "shares": "target"},
    "cta_metrics":     {"cta_clicks": "target", "trial_signups": "target"},
    "conversion":      {"rate": "target %"}
  },
  "framework_performance": {
    "storybrand_elements": {"hero_clarity": "metric", "guide_appeal": "metric"},
    "pas_effectiveness":   {"problem_resonance": "metric", "agitation_strength": "metric"},
    "aida_flow":           {"attention_grab": "metric", "desire_build": "metric"}
  },
  "feedback_for_next_cycle": {
    "storybrand_improvements": ["improvement 1", "improvement 2"],
    "pas_improvements":        ["improvement 1"],
    "aida_improvements":       ["improvement 1"]
  }
}"""

def analytics_node(state: ContentFactoryState):
    """Node 7: Analytics & Framework Feedback"""
    dist_plan = state.get("distribution_plan") or {}
    client    = state["client_brief"]
    lang      = client.get("output_language", "Vietnamese")

    user_prompt = f"""DISTRIBUTION PLAN: {json.dumps(dist_plan, ensure_ascii=False)[:800]}
GOAL: {client.get('goal', 'N/A')}
CHANNELS: {', '.join(client.get('channels', []))}

Output language: {lang}
Return ONLY JSON."""

    response = groq_chat(ANALYST_SYSTEM_PROMPT, user_prompt, temperature=0.5, max_tokens=600)

    try:
        analytics = json.loads(response.replace("```json", "").replace("```", "").strip())
    except:
        analytics = {"raw": response[:200]}

    # Merge optimization_notes từ QA + analytics
    existing_notes = state.get("optimization_notes") or {}
    analytics_feedback = analytics.get("feedback_for_next_cycle", {})
    merged_notes = {**existing_notes, **analytics_feedback}

    return {**state,
            "performance_metrics":  analytics.get("kpis", {}),
            "optimization_notes":   merged_notes,
            "current_step": "complete"}

print("✅ Cell 9: Analytics Node định nghĩa xong")
```

---

```python
# ═══════════════════════════════════════════════════════════════
# CELL 10: ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════

def run_content_factory(client_brief: dict) -> ContentFactoryState:
    """Run full pipeline: StoryBrand → Research → Creation → SEO → QA → Distribution → Analytics"""

    state = {
        "client_brief": client_brief,
        "content_brief": None, "research_data": None,
        "long_form_draft": None, "social_copies": None,
        "visual_prompts": None, "seo_optimized_content": None,
        "qa_score": None, "qa_feedback": None,
        "approved_content": None, "distribution_plan": None,
        "performance_metrics": None, "optimization_notes": None,
        "current_step": "strategist", "retry_count": 0
    }

    lang = client_brief.get("output_language", "Vietnamese")
    print(f"🚀 CONTENT FACTORY PRO — StoryBrand + PAS + AIDA [{lang}]")
    print("=" * 60)

    # Node 1: StoryBrand Strategy
    print("\n📌 [1/7] STORYBRAND STRATEGIST...")
    state = strategist_node(state)
    sb = (state.get('content_brief') or {}).get('storybrand_framework', {})
    print(f"   ✅ Hero: {sb.get('hero', 'N/A')[:60]}...")
    print(f"   ✅ Problem: {sb.get('external_problem', 'N/A')[:60]}...")

    # Node 2: Pain Point Research
    print("\n🔍 [2/7] PAIN POINT RESEARCH...")
    state = researcher_node(state)
    research = state.get('research_data') or {}
    print(f"   ✅ {len(research.get('pain_points', []))} pain points")
    print(f"   ✅ {len((research.get('proof_data') or {}).get('case_studies', []))} case studies")

    # Node 3: Content Creation
    print("\n✍️ [3/7] PAS + AIDA + STORYBRAND CREATION...")
    state = creation_node(state)
    print(f"   ✅ Draft: {len(state.get('long_form_draft') or '')} chars")

    # Node 4: SEO
    print("\n🔍 [4/7] SEO OPTIMIZATION...")
    state = seo_optimizer_node(state)
    seo = state.get('seo_optimized_content') or {}
    print(f"   ✅ Title: {seo.get('title_tag', 'N/A')[:60]}...")

    # Node 5: QA — auto-approve
    print("\n✅ [5/7] FRAMEWORK COMPLIANCE QA...")
    state = qa_node(state)
    score = state.get('qa_score', 0)
    print(f"   Score: {score}/10 — tự động approve")
    state['approved_content'] = {"seo": seo, "social": state.get('social_copies'), "visual": state.get('visual_prompts')}
    state['current_step'] = 'distribute'

    # Node 6: Distribution
    print("\n📤 [6/7] DISTRIBUTION PLANNING...")
    state = distributor_node(state)
    dist = state.get('distribution_plan') or {}
    print(f"   ✅ {len(dist.get('distribution_timeline', []))} posts scheduled")

    # Node 7: Analytics
    print("\n📊 [7/7] FRAMEWORK ANALYTICS...")
    state = analytics_node(state)
    opt = state.get('optimization_notes') or {}
    print(f"   ✅ {len(opt.get('storybrand_improvements', []))} StoryBrand insights")

    print("\n" + "=" * 60)
    print("✅ WORKFLOW HOÀN TẤT")
    return state

print("✅ Cell 10: Orchestrator định nghĩa xong")
```

---

```python
# ═══════════════════════════════════════════════════════════════
# CELL 11: RUN FULL WORKFLOW
# ═══════════════════════════════════════════════════════════════
reset_tracker()
result = run_content_factory(TEST_BRIEF)
print_token_summary()
```

---

```python
# ═══════════════════════════════════════════════════════════════
# CELL 12: INSPECT OUTPUT DETAIL
# ═══════════════════════════════════════════════════════════════

print("🔍 CHI TIẾT OUTPUT — StoryBrand + PAS + AIDA\n")

print("━" * 50)
print("📌 STORYBRAND FRAMEWORK")
print("━" * 50)
sb = (result.get("content_brief") or {}).get("storybrand_framework", {})
print(f"Hero:           {sb.get('hero', 'N/A')}")
print(f"External Prob:  {sb.get('external_problem', 'N/A')[:80]}...")
print(f"Internal Prob:  {sb.get('internal_problem', 'N/A')[:80]}...")
print(f"Guide:          {sb.get('guide', 'N/A')[:80]}...")
print(f"Plan:           {sb.get('plan', [])}")
print(f"Direct CTA:     {sb.get('direct_cta', 'N/A')}")
print(f"Success Vision: {sb.get('success_vision', 'N/A')[:80]}...")

print("\n" + "━" * 50)
print("🔥 PAS FRAMEWORK")
print("━" * 50)
pas = (result.get("content_brief") or {}).get("pas_framework", {})
print(f"Problem:    {pas.get('problem_statement', 'N/A')[:80]}...")
print(f"Agitation:  {pas.get('agitation_points', [])[:2]}")

print("\n" + "━" * 50)
print("🔍 SEO")
print("━" * 50)
seo = result.get("seo_optimized_content") or {}
print(f"Title:  {seo.get('title_tag', 'N/A')}")
print(f"Meta:   {seo.get('meta_description', 'N/A')[:100]}...")

print("\n" + "━" * 50)
print("✍️ CONTENT DRAFT")
print("━" * 50)
draft = result.get("long_form_draft") or ""
print(f"Total: {len(draft)} chars")
print(f"Hook (300 chars):\n{draft[:300]}...")

print("\n" + "━" * 50)
print("✅ QA SCORE")
print("━" * 50)
print(f"Overall: {result.get('qa_score', 'N/A')}/10")

print("\n" + "━" * 50)
print("📊 IMPROVEMENTS")
print("━" * 50)
opt = result.get('optimization_notes') or {}
print(f"StoryBrand: {opt.get('storybrand_improvements', [])[:2]}")
print(f"PAS:        {opt.get('pas_improvements', [])[:2]}")
print(f"AIDA:       {opt.get('aida_improvements', [])[:2]}")
```

---

```python
# ═══════════════════════════════════════════════════════════════
# CELL 13: SAVE RESULT TO FILE
# ═══════════════════════════════════════════════════════════════

output = {
    "timestamp":            datetime.now().isoformat(),
    "framework":            "StoryBrand + PAS + AIDA Hybrid",
    "output_language":      TEST_BRIEF.get("output_language", "Vietnamese"),
    "client_brief":         result.get("client_brief"),
    "storybrand_framework": (result.get("content_brief") or {}).get("storybrand_framework"),
    "pas_framework":        (result.get("content_brief") or {}).get("pas_framework"),
    "research_data":        result.get("research_data"),
    "long_form_draft":      result.get("long_form_draft"),
    "social_copies":        result.get("social_copies"),
    "visual_prompts":       result.get("visual_prompts"),
    "seo_optimized_content": result.get("seo_optimized_content"),
    "qa_score":             result.get("qa_score"),
    "qa_feedback":          result.get("qa_feedback"),
    "distribution_plan":    result.get("distribution_plan"),
    "performance_metrics":  result.get("performance_metrics"),
    "optimization_notes":   result.get("optimization_notes"),
}

import os
output_dir = "./output"
os.makedirs(output_dir, exist_ok=True)
output_path = f"{output_dir}/content_factory_result.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ Đã lưu: {output_path}")
```
