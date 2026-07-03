# RAG Architecture

The customer-service system was not designed as a pure generation-only chatbot. It was explicitly organized around a RAG workflow, and this is one of the two core lines of the project.

## Goals

RAG serves four practical goals here:

1. Keep postal-domain answers grounded in source knowledge.
2. Return citations together with model responses.
3. Reduce hallucination risk on rules, policies, and process questions.
4. Separate knowledge updates from model-parameter updates.

## Knowledge Sources

The main knowledge sources come from:

1. Filtered postal customer-service data and structured materials from the first phase.
2. Crawled postal FAQ, agreements, policy pages, and process materials.

These materials were converted into document records and embeddings, then loaded into PostgreSQL + pgvector.

## Retrieval Flow

The retrieval chain can be summarized as:

```text
User query
  -> context preparation
  -> vector retrieval
  -> relevant snippets recalled
  -> prompt assembly
  -> answer with citations
```

The same chain can be expressed more visually:

```mermaid
flowchart LR
    A[User Query] --> B[Context Preparation]
    B --> C[Vector Retrieval]
    C --> D[Relevant Snippets]
    D --> E[Prompt Assembly]
    E --> F[Model Answer]
    F --> G[Answer with Citations]
```

The point was not to retrieve as much as possible, but to keep the answer and the cited evidence aligned.

The retrieval layer was intentionally kept independent from the page layer so that it could be reused by the UI, the API layer, and later effect-analysis scripts.
