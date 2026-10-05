# model-router

> Open-source-first AI model router for CareerOS.  
> Ollama (local) is the primary provider; OpenAI-compatible APIs serve as fallback.  
> Business logic never calls a model directly — it always goes through this router.

---

## What it is

`model-router` is the single integration point between CareerOS business logic and any
AI inference provider.  It:

- **Routes by task type** — picks the best model for embedding vs. generation vs. reasoning.
- **Prefers local, open-source models** — Ollama runs entirely on your machine; no API keys needed.
- **Falls back automatically** — if Ollama is unavailable, requests transparently retry via any
  OpenAI-compatible API (OpenAI, Groq, Together AI, Azure OpenAI, Anyscale, etc.).
- **Returns structured results** — every call returns `RoutingResult` with the response text,
  which model/provider was used, token count, and wall-clock latency.
- **Never fabricates** — the router is a transport layer; truth-policy enforcement lives in the
  calling service.

---

## Quick start

```python
from app.services.model_router import get_model_router, TaskType

router = get_model_router()          # singleton; safe to call anywhere

# Text completion
result = await router.complete(
    prompt="Summarise this resume in two sentences: ...",
    task_type=TaskType.SUMMARIZATION,
)
print(result.text)          # "Experienced Python engineer with..."
print(result.provider_used) # "ollama" or "openai"
print(result.latency_ms)    # e.g. 312.0

# Embedding
vector = await router.embed("Python developer, 5 years experience")
# Returns list[float] — empty list if no provider available (graceful degradation)
```

### FastAPI dependency injection

```python
from fastapi import Depends
from app.services.model_router import ModelRouter, get_model_router, TaskType

@router.post("/classify")
async def classify_email(body: str, mr: ModelRouter = Depends(get_model_router)):
    result = await mr.complete(body, task_type=TaskType.CLASSIFICATION)
    return {"label": result.text.strip()}
```

---

## Configuration (environment variables)

| Variable               | Default                        | Description                                   |
|------------------------|--------------------------------|-----------------------------------------------|
| `OLLAMA_BASE_URL`      | `http://localhost:11434`       | Ollama server URL                             |
| `OLLAMA_DEFAULT_MODEL` | `llama3`                       | Default Ollama model for text tasks           |
| `OPENAI_API_KEY`       | *(unset — fallback disabled)*  | Set to enable OpenAI-compatible fallback      |
| `OPENAI_BASE_URL`      | `https://api.openai.com/v1`    | Override for Azure, Groq, Together, etc.      |
| `OPENAI_DEFAULT_MODEL` | `gpt-4o-mini`                  | OpenAI-compatible model name                  |

---

## Supported providers

| Provider          | Role      | Requires                    | Notes                                  |
|-------------------|-----------|-----------------------------|----------------------------------------|
| **Ollama**        | Primary   | Running Ollama server       | Free, local, private, no data egress   |
| **OpenAI**        | Fallback  | `OPENAI_API_KEY`            | `gpt-4o-mini` default                  |
| **Azure OpenAI**  | Fallback  | `OPENAI_API_KEY` + custom `OPENAI_BASE_URL` | Set URL to your Azure endpoint |
| **Groq**          | Fallback  | `OPENAI_API_KEY` + `OPENAI_BASE_URL=https://api.groq.com/openai/v1` | Fast inference |
| **Together AI**   | Fallback  | `OPENAI_API_KEY` + `OPENAI_BASE_URL=https://api.together.xyz/v1` | Open-source models |
| **Anyscale**      | Fallback  | `OPENAI_API_KEY` + custom `OPENAI_BASE_URL` | Llama, Mistral, etc. |

---

## Task → model mapping

| TaskType         | Ollama model       | Notes                                  |
|------------------|--------------------|----------------------------------------|
| `EMBEDDING`      | `nomic-embed-text` | Dedicated embedding model (384-dim)    |
| `EXTRACTION`     | `llama3`           | JSON-structured data extraction        |
| `CLASSIFICATION` | `llama3`           | Email / document category labels       |
| `SUMMARIZATION`  | `llama3`           | Resume / job description summaries     |
| `MATCHING`       | `llama3`           | Candidate ↔ job semantic matching      |
| `GENERATION`     | `llama3`           | Resume bullet / cover letter writing   |
| `REASONING`      | `llama3`           | Multi-step eligibility reasoning       |

To override any mapping, subclass `ModelRouter` and replace `TASK_MODEL_MAP`.

---

## How to add a new provider

1. **Create a provider class** that exposes:
   ```python
   async def complete(self, prompt, model, temperature, max_tokens, timeout) -> tuple[str, int]:
       ...  # returns (text, tokens_used)
   ```

2. **Register it in `ModelRouter.__init__`**:
   ```python
   self.my_provider = MyProvider(
       base_url=os.getenv("MY_PROVIDER_URL", "https://..."),
       api_key=os.getenv("MY_PROVIDER_KEY", ""),
   )
   ```

3. **Add a fallback branch in `ModelRouter.complete`** after the Ollama block:
   ```python
   if self.my_provider.api_key:
       try:
           text, tokens = await self.my_provider.complete(prompt, ...)
           return RoutingResult(text=text, provider_used="my_provider", ...)
       except Exception as exc:
           logger.error("my_provider failed: %s", exc)
           raise RuntimeError(...) from exc
   ```

4. **Add tests** in `apps/api/tests/unit/test_model_router.py` following the existing
   `pytest-asyncio` + `unittest.mock.AsyncMock` pattern.

---

## Files

```
packages/model-router/
└── README.md                   ← You are here

apps/api/app/services/
└── model_router.py             ← Implementation (canonical source)

apps/api/tests/unit/
└── test_model_router.py        ← Unit tests (no network required)
```

The implementation lives in the API app (`apps/api/app/services/model_router.py`) so it shares
the FastAPI dependency-injection system and is importable from any other service without a
circular package dependency.
