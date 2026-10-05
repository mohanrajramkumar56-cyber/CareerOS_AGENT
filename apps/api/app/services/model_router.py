"""
CareerOS Model Router — §32 of the build plan.

Routes AI inference tasks to the correct model/provider.
Supports Ollama (local open-source) and OpenAI-compatible APIs.
Business logic never calls a model directly — always goes through this router.

Task routing examples:
  EMBEDDING      → nomic-embed-text  (dedicated embedding model)
  EXTRACTION     → llama3            (structured data extraction)
  CLASSIFICATION → llama3            (email/document classification)
  SUMMARIZATION  → llama3            (resume summary, job summary)
  MATCHING       → llama3            (semantic matching reasoning)
  GENERATION     → llama3            (resume section generation)
  REASONING      → llama3            (complex multi-step reasoning)

Provider priority:
  1. Ollama (local, open-source, no API cost) — always tried first
  2. OpenAI-compatible (remote fallback, requires OPENAI_API_KEY)

Environment variables:
  OLLAMA_BASE_URL        Ollama server URL (default: http://localhost:11434)
  OLLAMA_DEFAULT_MODEL   Default Ollama model  (default: llama3)
  OPENAI_API_KEY         Enables OpenAI fallback when set
  OPENAI_BASE_URL        OpenAI-compatible base URL (default: https://api.openai.com/v1)
  OPENAI_DEFAULT_MODEL   OpenAI model name (default: gpt-4o-mini)
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------

class TaskType(str, Enum):
    EMBEDDING = "embedding"          # Vector embedding
    EXTRACTION = "extraction"        # Structured data extraction
    CLASSIFICATION = "classification"  # Email/document classification
    SUMMARIZATION = "summarization"  # Resume summary, job summary
    MATCHING = "matching"            # Semantic matching reasoning
    GENERATION = "generation"        # Resume section generation
    REASONING = "reasoning"          # Complex multi-step reasoning


@dataclass
class ModelConfig:
    """Configuration for a single model/provider pair."""
    provider: str          # "ollama" | "openai"
    model_name: str
    base_url: str
    api_key: Optional[str] = None
    timeout: float = 30.0
    max_tokens: int = 2048
    temperature: float = 0.1  # Low temperature for deterministic outputs


@dataclass
class RoutingResult:
    """Result returned from any ModelRouter call."""
    text: str
    model_used: str
    provider_used: str
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None


# ---------------------------------------------------------------------------
# Provider: Ollama (local, open-source)
# ---------------------------------------------------------------------------

class OllamaProvider:
    """Ollama local model provider (open-source, self-hosted)."""

    def __init__(self, base_url: str, default_model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    async def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        timeout: float = 30.0,
    ) -> tuple[str, int]:
        """
        Send a completion request to Ollama /api/generate.

        Returns:
            (response_text, eval_count_tokens)
        """
        import httpx

        model_name = model or self.default_model
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", ""), data.get("eval_count", 0)

    async def embed(
        self,
        text: str,
        model: Optional[str] = None,
        timeout: float = 30.0,
    ) -> list[float]:
        """
        Get text embeddings from Ollama /api/embeddings.

        Returns a list of floats (the embedding vector).
        """
        import httpx

        model_name = model or "nomic-embed-text"
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": model_name, "prompt": text},
            )
            resp.raise_for_status()
            return resp.json().get("embedding", [])

    async def health_check(self) -> bool:
        """Return True if the Ollama server is reachable."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Provider: OpenAI-compatible (remote fallback)
# ---------------------------------------------------------------------------

class OpenAICompatibleProvider:
    """
    OpenAI-compatible chat completion provider.

    Works with OpenAI, Azure OpenAI, Groq, Together, Anyscale, and any
    other service that exposes POST /chat/completions.
    """

    def __init__(self, base_url: str, api_key: str, default_model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model

    async def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        timeout: float = 60.0,
    ) -> tuple[str, int]:
        """
        Send a chat completion request.

        Returns:
            (response_text, total_tokens_used)
        """
        import httpx

        model_name = model or self.default_model
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
            return content, tokens


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class ModelRouter:
    """
    Routes AI tasks to the appropriate model and provider.

    Ollama is primary (open-source, local, no API cost).
    OpenAI-compatible is fallback (requires OPENAI_API_KEY env var).

    Usage:
        router = get_model_router()
        result = await router.complete("Summarise this resume...", TaskType.SUMMARIZATION)
        embedding = await router.embed("Python developer with 5 years experience")
    """

    # Task → preferred Ollama model.  Override via env if needed.
    TASK_MODEL_MAP: dict[TaskType, str] = {
        TaskType.EMBEDDING: "nomic-embed-text",
        TaskType.EXTRACTION: "llama3",
        TaskType.CLASSIFICATION: "llama3",
        TaskType.SUMMARIZATION: "llama3",
        TaskType.MATCHING: "llama3",
        TaskType.GENERATION: "llama3",
        TaskType.REASONING: "llama3",
    }

    def __init__(self) -> None:
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        ollama_model = os.getenv("OLLAMA_DEFAULT_MODEL", "llama3")
        self.ollama = OllamaProvider(base_url=ollama_url, default_model=ollama_model)

        openai_key = os.getenv("OPENAI_API_KEY", "")
        openai_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        openai_model = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini")
        self.openai: Optional[OpenAICompatibleProvider] = (
            OpenAICompatibleProvider(openai_url, openai_key, openai_model)
            if openai_key
            else None
        )

        # Cached health state; None = not yet checked.
        # Resets to False on first Ollama error so subsequent calls skip it.
        self._ollama_available: Optional[bool] = None

    async def _ollama_healthy(self) -> bool:
        """Lazily check Ollama health; cache result until an error occurs."""
        if self._ollama_available is None:
            self._ollama_available = await self.ollama.health_check()
            if self._ollama_available:
                logger.debug("model_router ollama=reachable url=%s", self.ollama.base_url)
            else:
                logger.warning("model_router ollama=unreachable url=%s", self.ollama.base_url)
        return self._ollama_available

    def reset_health_cache(self) -> None:
        """Force re-check of Ollama availability on the next call (useful in tests)."""
        self._ollama_available = None

    async def complete(
        self,
        prompt: str,
        task_type: TaskType = TaskType.GENERATION,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> RoutingResult:
        """
        Route a text-completion request.

        Tries Ollama first; falls back to OpenAI-compatible if Ollama is
        unavailable or raises.  Raises RuntimeError if no provider succeeds.

        Args:
            prompt:      The full prompt to send to the model.
            task_type:   Determines which Ollama model to select.
            temperature: Sampling temperature (0.0–1.0).
            max_tokens:  Maximum tokens to generate.

        Returns:
            RoutingResult with text, model/provider metadata, and latency.
        """
        model_name = self.TASK_MODEL_MAP.get(task_type, self.ollama.default_model)

        # ── 1. Try Ollama (open-source, local) ─────────────────────────────
        if await self._ollama_healthy():
            try:
                start = time.monotonic()
                text, tokens = await self.ollama.complete(
                    prompt,
                    model=model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                latency = (time.monotonic() - start) * 1000
                logger.info(
                    "model_router provider=ollama task=%s model=%s tokens=%s latency_ms=%.0f",
                    task_type,
                    model_name,
                    tokens,
                    latency,
                )
                return RoutingResult(
                    text=text,
                    model_used=model_name,
                    provider_used="ollama",
                    tokens_used=tokens,
                    latency_ms=latency,
                )
            except Exception as exc:
                logger.warning(
                    "model_router ollama_error=%s task=%s — falling back to OpenAI",
                    exc,
                    task_type,
                )
                self._ollama_available = False  # skip Ollama for subsequent calls

        # ── 2. Fallback: OpenAI-compatible ──────────────────────────────────
        if self.openai is not None:
            try:
                start = time.monotonic()
                text, tokens = await self.openai.complete(
                    prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                latency = (time.monotonic() - start) * 1000
                logger.info(
                    "model_router provider=openai task=%s model=%s tokens=%s latency_ms=%.0f",
                    task_type,
                    self.openai.default_model,
                    tokens,
                    latency,
                )
                return RoutingResult(
                    text=text,
                    model_used=self.openai.default_model,
                    provider_used="openai",
                    tokens_used=tokens,
                    latency_ms=latency,
                )
            except Exception as exc:
                logger.error(
                    "model_router openai_error=%s task=%s — no more providers",
                    exc,
                    task_type,
                )
                raise RuntimeError(
                    f"All model providers failed for task={task_type}. Last error: {exc}"
                ) from exc

        raise RuntimeError(
            "No AI model provider available. "
            "Start Ollama (OLLAMA_BASE_URL) or set OPENAI_API_KEY."
        )

    async def embed(self, text: str) -> list[float]:
        """
        Get a text embedding vector via Ollama's embedding model.

        Gracefully degrades to an empty list if Ollama is unavailable,
        so callers that use embeddings for ranking (not correctness) keep working.

        Args:
            text: The text to embed.

        Returns:
            List of floats representing the embedding, or [] on failure.
        """
        if await self._ollama_healthy():
            try:
                return await self.ollama.embed(text)
            except Exception as exc:
                logger.warning("model_router embed_error=%s — returning empty vector", exc)
        return []  # Graceful degradation


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """
    Return the process-wide ModelRouter singleton.

    Instantiated lazily on first call; safe to call from FastAPI
    dependency injection or anywhere in the application layer.

    Example (FastAPI):
        router = APIRouter()

        @router.post("/summarise")
        async def summarise(text: str, mr: ModelRouter = Depends(get_model_router)):
            result = await mr.complete(text, TaskType.SUMMARIZATION)
            return {"summary": result.text}
    """
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
