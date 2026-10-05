# ADR-006: Vector Search

## Status
Accepted

## Context
Semantic matching between job requirements and candidate evidence requires vector similarity search.

## Decision
Use pgvector extension on PostgreSQL. Embeddings generated via Ollama (nomic-embed-text). Vector similarity supplements but never replaces hard eligibility evaluation.

## Implementation
- pgvector installed and enabled in PostgreSQL init
- Embeddings stored as VECTOR(768) columns
- cosine similarity for matching
- Hard eligibility always evaluated first — vectors only for ranking

## Consequences
- No separate vector database needed
- Scales to tens of thousands of jobs per user
- Ollama must be running for embedding generation
