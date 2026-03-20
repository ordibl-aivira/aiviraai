"""Content Agent Service — Thinking Layer (Content Generation).

The Content Agent is the second stage of the Cognitive → Execution Stack.
It takes intelligence from the Research Agent and generates personalized,
execution-ready content: emails, call scripts, proposals, SMS, follow-ups.

Key difference from generic content generators: the Content Agent generates
AND feeds directly into the Execution Engine — content is never orphaned.

Capabilities
------------
- Personalized email generation
- Call script generation
- Proposal drafting
- SMS message generation
- Follow-up sequence generation
- Marketing campaign copy

Endpoints
---------
GET   /health
POST  /internal/content/generate          - generate content from intelligence
POST  /internal/content/generate-sequence - generate a multi-step content sequence
GET   /internal/content/{content_id}      - get generated content
GET   /internal/content                   - list generated content
POST  /internal/content/templates         - list available templates
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from packages.shared.models import (
    ContentRequest,
    ContentType,
    GeneratedContent,
)
from packages.shared.settings import settings

app = FastAPI(title="Content Agent", version="0.1.0")

# In-memory stores
_generated_content: Dict[str, dict] = {}

# ── Content Templates ─────────────────────────────────────────────

_TEMPLATES: Dict[str, Dict[str, str]] = {
    "sales_outreach_email": {
        "subject": "How {company} Can Save {hours_saved}+ Hours/Week",
        "body": (
            "Hi {decision_maker},\n\n"
            "I noticed that {company} ({industry}) is dealing with "
            "{pain_point_summary}. Many businesses in your space are "
            "solving this with AI-powered {solution}.\n\n"
            "{pitch}\n\n"
            "Would you be open to a quick 15-minute call this week?\n\n"
            "Best,\nAivira AI"
        ),
        "call_to_action": "Schedule a demo call",
    },
    "follow_up_email": {
        "subject": "Re: {previous_subject}",
        "body": (
            "Hi {decision_maker},\n\n"
            "Just following up on my previous message about {solution}. "
            "I understand you're busy — here's a quick summary of how "
            "we can help:\n\n"
            "- {benefit_1}\n"
            "- {benefit_2}\n"
            "- {benefit_3}\n\n"
            "Happy to chat whenever works for you.\n\n"
            "Best,\nAivira AI"
        ),
        "call_to_action": "Reply to schedule",
    },
    "call_script": {
        "subject": None,
        "body": (
            "Opening: \"Hi {decision_maker}, this is {agent_name} from Aivira. "
            "I'm reaching out because I noticed {company} is in the "
            "{industry} space, and we've been helping similar businesses "
            "with {solution}.\"\n\n"
            "Pain point probe: \"Are you currently dealing with {pain_point}?\"\n\n"
            "Value prop: \"{pitch}\"\n\n"
            "Close: \"Would you be interested in seeing a quick demo? "
            "I can set one up for this week.\""
        ),
        "call_to_action": "Book demo",
    },
    "sms_outreach": {
        "subject": None,
        "body": (
            "Hi {decision_maker}! Quick note from Aivira — "
            "we help {industry} businesses automate {pain_point_short}. "
            "Interested in a quick chat? Reply YES or visit {demo_link}"
        ),
        "call_to_action": "Reply YES",
    },
    "proposal": {
        "subject": "Proposal: AI Workforce Solution for {company}",
        "body": (
            "# Proposal for {company}\n\n"
            "## Executive Summary\n"
            "{company} is experiencing {pain_point_summary}. "
            "Aivira's AI Workforce platform can automate these processes, "
            "saving an estimated {hours_saved} hours per week.\n\n"
            "## Recommended Solution\n"
            "{pitch}\n\n"
            "## Key Benefits\n"
            "- {benefit_1}\n"
            "- {benefit_2}\n"
            "- {benefit_3}\n\n"
            "## Investment\n"
            "Starting at $X/month for {solution}.\n\n"
            "## Next Steps\n"
            "1. Schedule a demo call\n"
            "2. Custom configuration\n"
            "3. Go live in 48 hours"
        ),
        "call_to_action": "Schedule demo",
    },
}

# Map content types to default templates
_CONTENT_TYPE_TEMPLATES: Dict[str, str] = {
    ContentType.EMAIL.value: "sales_outreach_email",
    ContentType.FOLLOW_UP.value: "follow_up_email",
    ContentType.CALL_SCRIPT.value: "call_script",
    ContentType.SMS.value: "sms_outreach",
    ContentType.PROPOSAL.value: "proposal",
}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "content-agent"}


@app.post("/internal/content/generate")
def generate_content(request: ContentRequest) -> dict:
    """Generate personalized content from intelligence and context."""
    content_id = f"cnt_{uuid4().hex[:12]}"
    now = datetime.utcnow()

    # Merge intelligence and context for template variables
    variables = _build_template_variables(request)

    # Select template
    template_id = request.template_id or _CONTENT_TYPE_TEMPLATES.get(
        request.content_type.value, "sales_outreach_email"
    )
    template = _TEMPLATES.get(template_id)

    if not template:
        result = {
            "content_id": content_id,
            "organization_id": request.organization_id,
            "content_type": request.content_type.value,
            "status": "failed",
            "content": None,
            "variants": [],
            "intelligence_used": request.intelligence,
            "created_at": now.isoformat(),
        }
        _generated_content[content_id] = result
        return result

    # Generate primary content
    primary = _render_content(template, variables, request.content_type)

    # Generate variants if configured
    variants: List[dict] = []
    if settings.content_max_variants > 1:
        for i in range(min(settings.content_max_variants - 1, 2)):
            variant_vars = variables.copy()
            variant_vars["_variant"] = i + 1
            variant = _render_content(template, variant_vars, request.content_type)
            variants.append(variant.model_dump())

    result = {
        "content_id": content_id,
        "organization_id": request.organization_id,
        "content_type": request.content_type.value,
        "status": "generated",
        "content": primary.model_dump(),
        "variants": variants,
        "intelligence_used": request.intelligence,
        "created_at": now.isoformat(),
    }
    _generated_content[content_id] = result
    return result


@app.post("/internal/content/generate-sequence")
def generate_sequence(request: ContentRequest) -> dict:
    """Generate a multi-step content sequence (email → follow-up → SMS)."""
    sequence_id = f"cseq_{uuid4().hex[:12]}"
    now = datetime.utcnow()

    variables = _build_template_variables(request)
    sequence_types = [
        ContentType.EMAIL,
        ContentType.FOLLOW_UP,
        ContentType.SMS,
        ContentType.CALL_SCRIPT,
    ]

    pieces: List[dict] = []
    for ct in sequence_types:
        template_id = _CONTENT_TYPE_TEMPLATES.get(ct.value)
        template = _TEMPLATES.get(template_id, {}) if template_id else {}
        if template:
            content = _render_content(template, variables, ct)
            pieces.append({
                "content_type": ct.value,
                "content": content.model_dump(),
            })

    return {
        "sequence_id": sequence_id,
        "organization_id": request.organization_id,
        "status": "generated",
        "pieces": pieces,
        "total": len(pieces),
        "intelligence_used": request.intelligence,
        "created_at": now.isoformat(),
    }


@app.get("/internal/content/{content_id}")
def get_content(content_id: str) -> dict:
    """Retrieve previously generated content."""
    content = _generated_content.get(content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@app.get("/internal/content")
def list_content(organization_id: str) -> dict:
    """List all generated content for an organization."""
    results = [
        c for c in _generated_content.values()
        if c["organization_id"] == organization_id
    ]
    return {"content": results, "total": len(results)}


@app.post("/internal/content/templates")
def list_templates() -> dict:
    """List available content templates."""
    templates = [
        {
            "template_id": tid,
            "subject_template": t.get("subject"),
            "has_body": bool(t.get("body")),
            "call_to_action": t.get("call_to_action"),
        }
        for tid, t in _TEMPLATES.items()
    ]
    return {"templates": templates, "total": len(templates)}


# ── Internal helpers ──────────────────────────────────────────────

def _build_template_variables(request: ContentRequest) -> Dict[str, str]:
    """Build template variables from intelligence, context, and defaults."""
    intel = request.intelligence
    ctx = request.context
    merged: Dict[str, str] = {}

    # From lead intelligence
    merged["company"] = str(intel.get("company", intel.get("lead_name", "your company")))
    merged["decision_maker"] = str(intel.get("decision_maker", request.recipient or "there"))
    merged["industry"] = str(intel.get("industry", "your industry"))
    merged["lead_name"] = str(intel.get("lead_name", ""))

    # Pain points
    pain_points = intel.get("pain_points", [])
    if pain_points:
        merged["pain_point"] = str(pain_points[0])
        merged["pain_point_short"] = str(pain_points[0])[:50]
        merged["pain_point_summary"] = ", ".join(str(p) for p in pain_points[:3])
    else:
        merged["pain_point"] = "operational challenges"
        merged["pain_point_short"] = "operational challenges"
        merged["pain_point_summary"] = "common operational challenges"

    # Solution / pitch
    merged["pitch"] = str(intel.get("recommended_pitch",
                                     "AI-powered business automation"))
    merged["solution"] = str(intel.get("recommended_pitch",
                                       "AI workforce automation"))

    # Benefits
    merged["benefit_1"] = "Reduce missed calls by 95%"
    merged["benefit_2"] = "Automate booking and scheduling"
    merged["benefit_3"] = "24/7 availability without hiring"
    merged["hours_saved"] = "20"

    # Agent/context
    merged["agent_name"] = str(ctx.get("agent_name", "Alex"))
    merged["previous_subject"] = str(ctx.get("previous_subject",
                                              f"AI solution for {merged['company']}"))
    merged["demo_link"] = str(ctx.get("demo_link", "https://aivira.ai/demo"))

    return merged


def _render_content(
    template: Dict[str, str],
    variables: Dict[str, str],
    content_type: ContentType,
) -> GeneratedContent:
    """Render a template with variables, returning GeneratedContent."""
    subject_tmpl = template.get("subject")
    body_tmpl = template.get("body", "")
    cta = template.get("call_to_action")

    subject = _safe_format(subject_tmpl, variables) if subject_tmpl else None
    body = _safe_format(body_tmpl, variables)

    return GeneratedContent(
        content_type=content_type,
        subject=subject,
        body=body,
        call_to_action=cta,
        personalization_fields={k: v for k, v in variables.items()
                                if k in ("company", "decision_maker", "industry")},
    )


def _safe_format(template: str, variables: Dict[str, str]) -> str:
    """Format a template string, replacing missing variables with placeholders."""
    try:
        return template.format(**variables)
    except KeyError:
        # Fill in missing keys with placeholder
        import re
        result = template
        for match in re.finditer(r"\{(\w+)\}", template):
            key = match.group(1)
            if key not in variables:
                result = result.replace(f"{{{key}}}", f"[{key}]")
        try:
            return result.format(**variables)
        except (KeyError, ValueError):
            return result
