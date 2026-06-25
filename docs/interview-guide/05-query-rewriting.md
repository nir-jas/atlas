# Query Rewriting Interview Guide

## Short Explanation

Query rewriting creates alternative versions of a user question to improve
retrieval recall.

## Engineer-Level Explanation

Users often ask questions using different wording than the source documents.
Query rewriting searches the original query plus related variants, then merges
and deduplicates the results. This can recover evidence that a single embedding
query might miss.

## 2-Minute Interview Answer

Atlas applies query rewriting before retrieval. The original query is searched
first, then deterministic rewrites are searched, and results are merged by
`chunk_id`. Atlas keeps `matched_queries` metadata so engineers can see which
query forms retrieved each chunk.

## How Atlas Implements This

Query expansion is implemented in
`apps/api/src/atlas_api/services/query_rewrite.py`. Retrieval consumes rewrites
and merges results in `apps/api/src/atlas_api/services/retrieval.py`. The
`matched_queries` response field is defined in
`apps/api/src/atlas_api/schemas/rag.py`.

## Key Tradeoffs

- Rewrites can improve recall but add extra search work.
- More variants can introduce irrelevant chunks.
- Deterministic rewrites are easy to test but less flexible than an LLM-based
  rewriter.

## Common Failure Modes

- Rewrites drift away from the user's intent.
- Duplicate results are not merged cleanly.
- The best chunk is found by a rewrite but loses ranking after merge.
- Extra rewrites increase latency without improving quality.

## Debugging Checklist

- Inspect the original query and generated rewrites.
- Check `matched_queries` on returned chunks.
- Compare retrieval with rewriting enabled versus original-only search.
- Look for irrelevant chunks introduced by rewrites.
- Add eval cases for missed-recall failures.

## Common Interview Questions

- Why rewrite queries in RAG?
- How do you avoid changing user intent?
- How do you merge results from multiple query variants?
- What metadata helps debug query rewriting?
- When would you use an LLM for rewriting?

## Follow-Up Questions

- How would you evaluate whether rewrites help?
- How many rewrites should be allowed?
- How would you cache rewritten queries?
- How would you handle ambiguous user questions?
