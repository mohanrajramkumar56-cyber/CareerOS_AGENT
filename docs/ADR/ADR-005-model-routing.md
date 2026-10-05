# ADR-005: Model Routing

## Status
Accepted

## Context
CareerOS uses AI for semantic matching, resume generation, email classification, and extraction. Business logic must not be coupled to a specific model provider.

## Decision
All AI calls go through ModelRouter. Ollama (local, open-source) is the primary provider. OpenAI-compatible APIs are the fallback. Embedding uses nomic-embed-text via Ollama.

## Task Routing
- embedding → nomic-embed-text (Ollama)
- extraction/classification → llama3 (Ollama) → gpt-4o-mini (fallback)
- generation/reasoning → llama3 (Ollama) → gpt-4o-mini (fallback)

## Consequences
- Fully open-source deployment possible with only Ollama
- OpenAI key optional (only needed when Ollama unavailable)
- LLM results validated before use — never trusted blindly
