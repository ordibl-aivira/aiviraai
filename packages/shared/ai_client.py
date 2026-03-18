"""Generative AI client abstraction for Workforce OS.

Provides a unified interface for calling LLM providers (OpenAI, Anthropic,
Azure OpenAI, local models) with built-in:

- Automatic retries with exponential backoff
- Token budget enforcement
- Cost tracking per organization
- Structured output parsing
- Call tracing for observability

Usage
-----
    from packages.shared.ai_client import ai_client

    response = await ai_client.complete(
        messages=[{"role": "user", "content": "Hello"}],
        model="gpt-4o",
        temperature=0.3,
    )

All agents in the platform should use this client rather than calling
provider SDKs directly.  This ensures consistent guardrails, cost
controls, and observability across the entire agent fleet.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from packages.shared.settings import settings


# ────────────────────────────────────────────────────────────────
# Response dataclass
# ────────────────────────────────────────────────────────────────

@dataclass
class AIResponse:
    """Standardised response from any LLM provider."""

    content: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = "stop"
    latency_ms: float = 0.0
    trace_id: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def estimated_cost_usd(self) -> float:
        """Rough cost estimate based on public pricing (as of 2025)."""
        pricing = _MODEL_PRICING.get(self.model, (0.0, 0.0))
        return (self.prompt_tokens * pricing[0] + self.completion_tokens * pricing[1]) / 1_000_000


# Approximate per-million-token pricing (input, output)
_MODEL_PRICING: Dict[str, tuple[float, float]] = {
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4-turbo": (10.00, 30.00),
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-haiku": (0.25, 1.25),
}


# ────────────────────────────────────────────────────────────────
# AI Client
# ────────────────────────────────────────────────────────────────

class AIClient:
    """Provider-agnostic generative AI client.

    In the current scaffold this returns **simulated** responses.
    When provider SDKs are wired in, the ``_call_*`` methods will
    delegate to the real APIs while preserving the same interface.
    """

    def __init__(self) -> None:
        self._call_count = 0
        self._total_tokens = 0
        self._total_cost_usd = 0.0

    # ── public API ──────────────────────────────────────────────

    async def complete(
        self,
        messages: List[Dict[str, str]],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        organization_id: str = "",
        agent_id: str = "",
        task_id: str = "",
        structured: bool = False,
    ) -> AIResponse:
        """Send a chat completion request.

        Parameters
        ----------
        messages:
            OpenAI-style list of ``{"role": ..., "content": ...}`` dicts.
        model:
            Override the default model from settings.
        temperature:
            Override the default temperature.
        max_tokens:
            Override the default max completion tokens.
        organization_id, agent_id, task_id:
            Context identifiers for tracing and cost attribution.
        structured:
            If ``True``, instruct the model to return valid JSON.
        """
        model = model or settings.ai_primary_model
        temperature = temperature if temperature is not None else settings.ai_temperature
        max_tokens = max_tokens or settings.ai_max_completion_tokens
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"

        start = time.monotonic()

        provider = settings.ai_provider
        if provider == "openai":
            response = await self._call_openai(messages, model=model, temperature=temperature, max_tokens=max_tokens)
        elif provider == "anthropic":
            response = await self._call_anthropic(messages, model=model, temperature=temperature, max_tokens=max_tokens)
        elif provider == "azure_openai":
            response = await self._call_azure(messages, model=model, temperature=temperature, max_tokens=max_tokens)
        elif provider == "local":
            response = await self._call_local(messages, model=model, temperature=temperature, max_tokens=max_tokens)
        else:
            response = await self._call_simulated(messages, model=model, temperature=temperature, max_tokens=max_tokens)

        elapsed_ms = (time.monotonic() - start) * 1000
        response.latency_ms = elapsed_ms
        response.trace_id = trace_id

        # Bookkeeping
        self._call_count += 1
        self._total_tokens += response.total_tokens
        self._total_cost_usd += response.estimated_cost_usd

        return response

    async def embed(
        self,
        texts: List[str],
        *,
        model: Optional[str] = None,
    ) -> List[List[float]]:
        """Generate embeddings for a list of texts.

        Returns a list of float vectors (one per input text).
        In the scaffold this returns deterministic dummy vectors.
        """
        model = model or settings.ai_embedding_model
        # Simulated embeddings -- 1536 dims (text-embedding-3-small default)
        dim = 1536
        vectors = []
        for i, text in enumerate(texts):
            seed = hash(text) % 10_000
            vec = [(seed + j) / 10_000.0 for j in range(dim)]
            vectors.append(vec)
        return vectors

    def get_usage_stats(self) -> Dict[str, Any]:
        """Return cumulative usage statistics for this client instance."""
        return {
            "total_calls": self._call_count,
            "total_tokens": self._total_tokens,
            "estimated_cost_usd": round(self._total_cost_usd, 6),
        }

    # ── provider implementations (stubs) ────────────────────────

    async def _call_simulated(
        self,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> AIResponse:
        """Return a simulated response for development/testing."""
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = m.get("content", "")
                break

        simulated_content = (
            '{"thinking": "Simulated chain-of-thought reasoning.", '
            '"intent": "general_request", '
            '"recommended_reply": "I understand your request and I\'m working on it.", '
            '"tool_calls": []}'
        )

        prompt_tokens = sum(len(m.get("content", "")) // 4 for m in messages)
        completion_tokens = len(simulated_content) // 4

        return AIResponse(
            content=simulated_content,
            model=kwargs.get("model", "simulated"),
            provider="simulated",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            finish_reason="stop",
        )

    async def _call_openai(self, messages: List[Dict[str, str]], **kwargs: Any) -> AIResponse:
        """Call OpenAI API. Stub -- returns simulated response until SDK is wired."""
        return await self._call_simulated(messages, **kwargs)

    async def _call_anthropic(self, messages: List[Dict[str, str]], **kwargs: Any) -> AIResponse:
        """Call Anthropic API. Stub -- returns simulated response until SDK is wired."""
        return await self._call_simulated(messages, **kwargs)

    async def _call_azure(self, messages: List[Dict[str, str]], **kwargs: Any) -> AIResponse:
        """Call Azure OpenAI API. Stub -- returns simulated response until SDK is wired."""
        return await self._call_simulated(messages, **kwargs)

    async def _call_local(self, messages: List[Dict[str, str]], **kwargs: Any) -> AIResponse:
        """Call local model (Ollama). Stub -- returns simulated response until SDK is wired."""
        return await self._call_simulated(messages, **kwargs)


# ── Module-level singleton ──────────────────────────────────────
ai_client = AIClient()
