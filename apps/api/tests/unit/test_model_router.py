"""
Unit tests for ModelRouter (§32 of the build plan).

No network calls are made — all provider methods are patched with AsyncMock.
Tests cover:
  - Ollama-first routing happy path
  - Automatic fallback to OpenAI when Ollama is unavailable
  - Automatic fallback when Ollama raises mid-request
  - RuntimeError when no provider is available
  - Embedding happy path and graceful degradation
  - Singleton behaviour of get_model_router()
  - TaskType → model-name mapping
  - Health-cache reset
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.model_router import (
    ModelRouter,
    OllamaProvider,
    OpenAICompatibleProvider,
    RoutingResult,
    TaskType,
    get_model_router,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_router(*, ollama_healthy: bool = True, openai_key: str = "") -> ModelRouter:
    """Build a ModelRouter with mocked providers."""
    router = ModelRouter.__new__(ModelRouter)
    router._ollama_available = None

    router.ollama = AsyncMock(spec=OllamaProvider)
    router.ollama.base_url = "http://localhost:11434"
    router.ollama.default_model = "llama3"
    router.ollama.health_check = AsyncMock(return_value=ollama_healthy)
    router.ollama.complete = AsyncMock(return_value=("ollama response", 42))
    router.ollama.embed = AsyncMock(return_value=[0.1, 0.2, 0.3])

    if openai_key:
        router.openai = AsyncMock(spec=OpenAICompatibleProvider)
        router.openai.default_model = "gpt-4o-mini"
        router.openai.complete = AsyncMock(return_value=("openai response", 99))
    else:
        router.openai = None

    return router


# ---------------------------------------------------------------------------
# OllamaProvider unit tests
# ---------------------------------------------------------------------------

class TestOllamaProvider:
    def test_base_url_strips_trailing_slash(self):
        p = OllamaProvider(base_url="http://localhost:11434/", default_model="llama3")
        assert p.base_url == "http://localhost:11434"

    def test_default_model_stored(self):
        p = OllamaProvider(base_url="http://localhost:11434", default_model="mistral")
        assert p.default_model == "mistral"

    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_connection_error(self):
        """health_check must not raise — returns False on any network error."""
        p = OllamaProvider(base_url="http://127.0.0.1:1", default_model="llama3")
        result = await p.health_check()
        assert result is False


# ---------------------------------------------------------------------------
# OpenAICompatibleProvider unit tests
# ---------------------------------------------------------------------------

class TestOpenAICompatibleProvider:
    def test_base_url_strips_trailing_slash(self):
        p = OpenAICompatibleProvider(
            base_url="https://api.openai.com/v1/",
            api_key="sk-test",
            default_model="gpt-4o-mini",
        )
        assert p.base_url == "https://api.openai.com/v1"

    def test_attributes_stored(self):
        p = OpenAICompatibleProvider(
            base_url="https://api.openai.com/v1",
            api_key="sk-test",
            default_model="gpt-4o-mini",
        )
        assert p.api_key == "sk-test"
        assert p.default_model == "gpt-4o-mini"


# ---------------------------------------------------------------------------
# ModelRouter.complete — routing logic
# ---------------------------------------------------------------------------

class TestModelRouterComplete:
    @pytest.mark.asyncio
    async def test_uses_ollama_when_healthy(self):
        router = _make_router(ollama_healthy=True)
        result = await router.complete("Hello", TaskType.GENERATION)

        assert result.provider_used == "ollama"
        assert result.text == "ollama response"
        assert result.tokens_used == 42
        assert result.latency_ms is not None
        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_returns_routing_result_type(self):
        router = _make_router(ollama_healthy=True)
        result = await router.complete("test prompt")
        assert isinstance(result, RoutingResult)

    @pytest.mark.asyncio
    async def test_model_used_matches_task_type(self):
        router = _make_router(ollama_healthy=True)
        # SUMMARIZATION should use llama3
        result = await router.complete("summarise this", TaskType.SUMMARIZATION)
        assert result.model_used == "llama3"

    @pytest.mark.asyncio
    async def test_embedding_task_uses_nomic_embed_text(self):
        router = _make_router(ollama_healthy=True)
        result = await router.complete("embed me", TaskType.EMBEDDING)
        assert result.model_used == "nomic-embed-text"

    @pytest.mark.asyncio
    async def test_falls_back_to_openai_when_ollama_unhealthy(self):
        router = _make_router(ollama_healthy=False, openai_key="sk-test")
        result = await router.complete("Hello", TaskType.GENERATION)

        assert result.provider_used == "openai"
        assert result.text == "openai response"
        assert result.tokens_used == 99
        # Ollama complete should NOT have been called
        router.ollama.complete.assert_not_called()

    @pytest.mark.asyncio
    async def test_falls_back_to_openai_on_ollama_runtime_error(self):
        """If Ollama raises during completion, fallback to OpenAI."""
        router = _make_router(ollama_healthy=True, openai_key="sk-test")
        router.ollama.complete = AsyncMock(side_effect=RuntimeError("model not loaded"))

        result = await router.complete("Hello", TaskType.GENERATION)

        assert result.provider_used == "openai"
        assert result.text == "openai response"
        # Health cache should now be False
        assert router._ollama_available is False

    @pytest.mark.asyncio
    async def test_raises_runtime_error_when_no_provider(self):
        """No Ollama and no OpenAI key → RuntimeError."""
        router = _make_router(ollama_healthy=False, openai_key="")

        with pytest.raises(RuntimeError, match="No AI model provider available"):
            await router.complete("Hello")

    @pytest.mark.asyncio
    async def test_raises_runtime_error_when_both_providers_fail(self):
        """Ollama fails, OpenAI also fails → RuntimeError propagated."""
        router = _make_router(ollama_healthy=False, openai_key="sk-test")
        router.openai.complete = AsyncMock(side_effect=RuntimeError("API error"))

        with pytest.raises(RuntimeError, match="All model providers failed"):
            await router.complete("Hello")

    @pytest.mark.asyncio
    async def test_ollama_health_cached_across_calls(self):
        """Second call should reuse the cached health result, not re-check."""
        router = _make_router(ollama_healthy=True)

        await router.complete("first call")
        await router.complete("second call")

        # health_check should only be called once
        router.ollama.health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_passes_temperature_and_max_tokens_to_ollama(self):
        router = _make_router(ollama_healthy=True)
        await router.complete("prompt", temperature=0.7, max_tokens=512)

        router.ollama.complete.assert_called_once()
        call_kwargs = router.ollama.complete.call_args
        assert call_kwargs.kwargs["temperature"] == 0.7
        assert call_kwargs.kwargs["max_tokens"] == 512

    @pytest.mark.asyncio
    async def test_default_task_type_is_generation(self):
        """complete() without task_type should use GENERATION routing."""
        router = _make_router(ollama_healthy=True)
        result = await router.complete("generate something")
        assert result.model_used == ModelRouter.TASK_MODEL_MAP[TaskType.GENERATION]


# ---------------------------------------------------------------------------
# ModelRouter.embed
# ---------------------------------------------------------------------------

class TestModelRouterEmbed:
    @pytest.mark.asyncio
    async def test_returns_vector_when_ollama_healthy(self):
        router = _make_router(ollama_healthy=True)
        vector = await router.embed("Python developer")

        assert vector == [0.1, 0.2, 0.3]
        router.ollama.embed.assert_called_once_with("Python developer")

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_ollama_unhealthy(self):
        router = _make_router(ollama_healthy=False)
        vector = await router.embed("Python developer")

        assert vector == []
        router.ollama.embed.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_embed_error(self):
        """embed() must not raise — graceful degradation to empty list."""
        router = _make_router(ollama_healthy=True)
        router.ollama.embed = AsyncMock(side_effect=RuntimeError("embed failed"))

        vector = await router.embed("some text")
        assert vector == []

    @pytest.mark.asyncio
    async def test_embed_does_not_require_openai(self):
        """Embeddings only use Ollama; no OpenAI fallback for embeddings."""
        router = _make_router(ollama_healthy=False, openai_key="sk-test")
        vector = await router.embed("test")

        # Even with OpenAI configured, embed returns [] when Ollama is down
        assert vector == []


# ---------------------------------------------------------------------------
# Health cache and reset
# ---------------------------------------------------------------------------

class TestHealthCache:
    @pytest.mark.asyncio
    async def test_reset_health_cache_triggers_recheck(self):
        router = _make_router(ollama_healthy=True)

        await router.complete("first call")
        assert router.ollama.health_check.call_count == 1

        router.reset_health_cache()
        await router.complete("second call after reset")
        assert router.ollama.health_check.call_count == 2

    @pytest.mark.asyncio
    async def test_health_cache_set_false_after_ollama_error(self):
        router = _make_router(ollama_healthy=True, openai_key="sk-test")
        router.ollama.complete = AsyncMock(side_effect=ConnectionError("refused"))

        await router.complete("prompt")
        assert router._ollama_available is False


# ---------------------------------------------------------------------------
# TaskType enum
# ---------------------------------------------------------------------------

class TestTaskType:
    def test_all_task_types_in_model_map(self):
        """Every TaskType should have an entry in TASK_MODEL_MAP."""
        for task in TaskType:
            assert task in ModelRouter.TASK_MODEL_MAP, (
                f"TaskType.{task.name} is missing from TASK_MODEL_MAP"
            )

    def test_task_type_values_are_strings(self):
        for task in TaskType:
            assert isinstance(task.value, str)


# ---------------------------------------------------------------------------
# RoutingResult dataclass
# ---------------------------------------------------------------------------

class TestRoutingResult:
    def test_required_fields(self):
        r = RoutingResult(text="hello", model_used="llama3", provider_used="ollama")
        assert r.text == "hello"
        assert r.model_used == "llama3"
        assert r.provider_used == "ollama"
        assert r.tokens_used is None
        assert r.latency_ms is None

    def test_optional_fields(self):
        r = RoutingResult(
            text="hi", model_used="gpt-4o-mini", provider_used="openai",
            tokens_used=100, latency_ms=250.0,
        )
        assert r.tokens_used == 100
        assert r.latency_ms == 250.0


# ---------------------------------------------------------------------------
# Singleton: get_model_router
# ---------------------------------------------------------------------------

class TestGetModelRouter:
    def test_returns_model_router_instance(self):
        import app.services.model_router as mr_module
        # Reset singleton so test is isolated
        mr_module._router = None
        router = get_model_router()
        assert isinstance(router, ModelRouter)

    def test_returns_same_instance_on_repeated_calls(self):
        import app.services.model_router as mr_module
        mr_module._router = None
        r1 = get_model_router()
        r2 = get_model_router()
        assert r1 is r2

    def test_singleton_reset_creates_new_instance(self):
        import app.services.model_router as mr_module
        mr_module._router = None
        r1 = get_model_router()
        mr_module._router = None
        r2 = get_model_router()
        assert r1 is not r2
