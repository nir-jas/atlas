# Context Assembly Interview Guide

## Short Explanation

Context assembly turns retrieved chunks into the exact text a model receives.

## Engineer-Level Explanation

After retrieval, a RAG system must choose which chunks fit the answer request,
filter noisy results, preserve useful metadata, and format the final context.
This step controls prompt size, source traceability, and how easy the model's
input is to inspect.

## 2-Minute Interview Answer

Atlas keeps context assembly separate from retrieval and generation. That makes
it possible to preview the context before calling an LLM, tune chunk count and
similarity thresholds, and ensure citations come from the chunks that actually
survived filtering and budget limits.

## How Atlas Implements This

Context formatting is implemented in
`apps/api/src/atlas_api/services/context_assembly.py`. The preview endpoint is
defined in `apps/api/src/atlas_api/http/v1/rag.py`, and its request/response
models are in `apps/api/src/atlas_api/schemas/rag.py`.

## Key Tradeoffs

- Smaller context is cheaper and less noisy but may omit supporting evidence.
- Including source metadata improves traceability but uses prompt budget.
- Preserving retrieval order is simple and inspectable, but reranking could
  improve final ordering later.

## Common Failure Modes

- Relevant chunks are filtered out by a high threshold.
- Context budget cuts off the most useful evidence.
- Formatting hides source or section information.
- The model receives too many near-duplicate chunks.

## Debugging Checklist

- Use the context preview endpoint before changing generation.
- Check score thresholds and `max_chunks`.
- Confirm selected chunks still contain the answer.
- Verify source and section labels are present.
- Look for duplicate or low-value chunks.

## Common Interview Questions

- Why is context assembly a separate step?
- What metadata should be included in context?
- How do you manage context window limits?
- How do thresholds affect answer quality?
- Why preview context before calling the model?

## Follow-Up Questions

- How would you order chunks from the same document?
- When would you add compression or summarization?
- How would you prevent prompt injection in retrieved text?
- How would you make context assembly observable?
