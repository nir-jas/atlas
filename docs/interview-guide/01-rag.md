# RAG Interview Guide

## Short Explanation

RAG means retrieving relevant source material before asking a model to answer.
It gives the model fresh, domain-specific context instead of relying only on
training data.

## Engineer-Level Explanation

A RAG system has an indexing path and a query path. Indexing loads documents,
splits them into chunks, embeds the chunks, and stores chunk metadata plus
vectors. Querying embeds the user question, retrieves similar chunks, assembles
context, and generates an answer grounded in that context.

## 2-Minute Interview Answer

In Atlas, RAG is treated as an inspectable pipeline: upload documents, chunk
them, store embeddings, retrieve ranked chunks with pgvector, assemble context,
and generate an answer with citations. The important engineering point is that
each stage can be tested and debugged separately, so bad answers can be traced
back to retrieval, filtering, context assembly, or generation.

## How Atlas Implements This

Atlas exposes RAG endpoints in `apps/api/src/atlas_api/http/v1/rag.py` and the
request/response contracts in `apps/api/src/atlas_api/schemas/rag.py`.
Retrieval behavior lives in `apps/api/src/atlas_api/services/retrieval.py`, and
database-backed similarity search lives in
`apps/api/src/atlas_api/repositories/retrieval.py`.

## Key Tradeoffs

- More chunks improve recall but can add noise.
- Higher similarity thresholds reduce irrelevant context but can miss useful
  evidence.
- Separating retrieval, context assembly, and generation makes the system easier
  to inspect but adds more moving parts.

## Common Failure Modes

- The answer is not present in retrieved chunks.
- `top_k` is too low or too high.
- Metadata filters exclude the right documents.
- The model guesses when context is missing.
- Citations do not match the chunks actually used.

## Debugging Checklist

- Check the original question and any rewrites.
- Inspect retrieved chunks and similarity scores.
- Confirm the answer exists in the selected chunks.
- Review `top_k`, collection filters, and score thresholds.
- Preview assembled context before changing prompts.
- Add or update an eval for the failure.

## Common Interview Questions

- What problem does RAG solve?
- What are the main stages of a RAG pipeline?
- Why is retrieval quality often more important than prompt wording?
- How do you decide chunk size and `top_k`?
- How do citations improve trust?

## Follow-Up Questions

- How would you debug a hallucinated answer?
- When would you add reranking?
- How would you evaluate retrieval separately from generation?
- How would the design change for a much larger corpus?
