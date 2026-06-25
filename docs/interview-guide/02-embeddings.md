# Embeddings Interview Guide

## Short Explanation

Embeddings convert text into numeric vectors so similar meanings can be compared
mathematically.

## Engineer-Level Explanation

In RAG, document chunks and user queries are embedded into the same vector
space. Similarity search compares the query vector against stored chunk vectors
to find likely evidence. The embedding model, vector dimensions, and indexing
strategy must stay consistent.

## 2-Minute Interview Answer

Atlas uses embeddings to make document retrieval semantic instead of purely
keyword based. During indexing, chunks receive embeddings. During search, the
query is embedded and compared with stored chunk embeddings. Atlas defaults to a
deterministic fake provider for local development and tests, with OpenAI
embeddings available through configuration.

## How Atlas Implements This

Stored embeddings are represented by
`apps/api/src/atlas_api/models/chunk_embedding.py`. Retrieval embeds each query
in `apps/api/src/atlas_api/services/retrieval.py`, then passes the vector to
`apps/api/src/atlas_api/repositories/retrieval.py` for similarity search.

## Key Tradeoffs

- Stronger embedding models can improve recall but may add cost and latency.
- Fixed vector dimensions make storage predictable but require provider output
  to match configuration.
- Fake embeddings keep tests deterministic but do not represent real semantic
  quality.

## Common Failure Modes

- Query and chunk embeddings use different models or dimensions.
- Re-indexing is skipped after changing embedding settings.
- Text chunks are too small to preserve meaning.
- Similar but wrong chunks rank above the needed evidence.

## Debugging Checklist

- Confirm the embedding provider and dimensions.
- Verify documents were indexed after configuration changes.
- Inspect retrieved chunk text, not just scores.
- Check whether the corpus contains the expected answer.
- Compare failures against eval cases.

## Common Interview Questions

- What is an embedding?
- Why do embeddings help semantic search?
- What does vector dimensionality mean?
- Why must query and document embeddings use the same model?
- How do embeddings differ from keyword search?

## Follow-Up Questions

- How would you compare two embedding models?
- What happens when dimensions do not match?
- How would multilingual content affect model choice?
- When would keyword search still be useful?
