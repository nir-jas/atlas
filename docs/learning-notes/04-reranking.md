# Reranking

## 1. What problem reranking solves

Initial retrieval is optimized for recall: find a useful candidate set quickly.
That first pass can still return chunks in a weak order, especially when hybrid
search mixes vector similarity and keyword rank.

Reranking adds a second pass:

```text
User query
↓
Retrieve candidate chunks
↓
Score each candidate against the original query
↓
Sort and filter
↓
Assemble context
```

The reranker does not search the whole corpus. It only evaluates chunks that
retrieval already found.

## 2. Why not replace retrieval with reranking?

Reranking every chunk would be slow and expensive. Retrieval narrows the search
space first. Reranking then spends more work on a smaller candidate set.

This split gives the system two controls:

- `top_k` controls how many candidates retrieval fetches.
- `RERANKER_TOP_K` controls how many reranked chunks survive for context.

## 3. How Atlas implements reranking

Atlas adds a `RerankerService` after vector, keyword, or hybrid retrieval.

When `RERANKER_ENABLED=false`, search keeps the existing retrieval order.

When `RERANKER_ENABLED=true`:

1. Retrieval fetches `top_k` candidates.
2. The reranker scores each candidate against the original user query.
3. Results are sorted by `reranker_score` descending.
4. Up to `RERANKER_TOP_K` chunks are kept.
5. Chunks below `RERANKER_SCORE_THRESHOLD` are removed.

The response preserves original retrieval metadata such as `similarity_score`,
`keyword_rank`, and `matched_by`, then adds `reranker_enabled` and
`reranker_score`.

## 4. Fake reranker

Atlas only includes a fake reranker provider for now. It is deterministic and
local, so tests can verify the pipeline without an external model.

The fake provider scores lexical overlap between the original query and chunk
text. This is not meant to be a production relevance model. It exists to make
the service boundary and behavior testable.

## 5. Thresholds

`RERANKER_SCORE_THRESHOLD` controls how strict the second pass is.

Higher thresholds:

- reduce weak context
- can remove useful supporting chunks
- make no-context answers more likely

Lower thresholds:

- preserve recall
- can pass noisy chunks into context
- make answers less focused

## Key Lessons

- Retrieval finds candidates; reranking orders and filters them.
- Reranking should preserve original retrieval scores for debugging.
- A fake reranker is useful for testing the pipeline before adding external APIs.
- The main tradeoff is quality versus latency and complexity.
