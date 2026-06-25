# Reranking Interview Guide

## Short Explanation

Reranking is a second retrieval stage that scores already-retrieved chunks
against the original query, then sorts and filters them before context assembly.

## Engineer-Level Explanation

First-stage retrieval should be fast and broad enough to find plausible
matches. Reranking can spend more computation on that smaller candidate set to
improve ordering and remove weak chunks. It is especially useful after hybrid
search because vector and keyword scores are not directly comparable.

## 2-Minute Interview Answer

In Atlas, vector, keyword, or hybrid search first retrieves candidate chunks.
If reranking is enabled, `RerankerService` sends those candidates and the
original user query to a configured reranker provider. The service attaches a
`reranker_score`, sorts by that score descending, keeps up to
`RERANKER_TOP_K`, and filters chunks below `RERANKER_SCORE_THRESHOLD`.
Original retrieval metadata like `similarity_score`, `keyword_rank`, and
`matched_by` stays in the response for debugging.

## How Atlas Implements This

The provider boundary lives under `reranker_providers/`. The current provider
is fake and deterministic. The use-case logic lives in
`apps/api/src/atlas_api/services/reranking.py`, and `RetrievalService` applies
it after the selected retrieval mode.

Configuration:

```dotenv
RERANKER_ENABLED=false
RERANKER_PROVIDER=fake
RERANKER_TOP_K=5
RERANKER_SCORE_THRESHOLD=0.80
```

## Key Tradeoffs

- Reranking can improve context quality but adds a second scoring pass.
- A strict threshold reduces noise but can drop helpful chunks.
- Preserving original retrieval metadata makes ranking decisions debuggable.
- A fake provider keeps tests deterministic but does not model production
  relevance quality.

## Common Failure Modes

- Fetching too few first-stage candidates, so reranking never sees the best
  chunk.
- Setting the threshold too high and returning no context.
- Treating reranker scores as comparable across providers without validation.
- Hiding original retrieval scores, making ranking regressions hard to debug.

## Debugging Checklist

- Check `matched_by` to see whether the chunk came from vector, keyword, or both.
- Compare `similarity_score`, `keyword_rank`, and `reranker_score`.
- Lower `RERANKER_SCORE_THRESHOLD` if all candidates are filtered.
- Increase retrieval `top_k` if good chunks are not reaching the reranker.
- Run tests with the fake provider before introducing any external reranker.

## Common Interview Questions

- Why use reranking after retrieval?
- What is the difference between retrieval `top_k` and reranker top-k?
- How would you tune a reranker threshold?
- Why preserve original retrieval scores after reranking?
- What are the latency costs of reranking?

## Follow-Up Questions

- When would you add a cross-encoder reranker?
- How would you evaluate reranking quality?
- How would you handle provider failures?
- How would you make reranking configurable per collection?
