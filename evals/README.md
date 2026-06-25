# Evals

Use this folder for retrieval, generation, and workflow evaluation cases.

Keep fixtures synthetic, public, or explicitly safe to share in an open-source
repository.

## RAG Harness

`rag_cases.json` contains a small public-safe RAG fixture with seed documents
and expected answer behavior. Each case includes:

- `question`
- optional `collection`
- `expected_sources`
- `expected_answer_contains`

Run the harness from the repository root:

```bash
uv run python scripts/run_rag_evals.py
```

The runner creates an isolated in-memory Atlas app, overrides both embedding and
LLM providers with deterministic fake providers, uploads the fixture documents,
and calls `/api/v1/rag/answer` for each case. It checks cited sources, expected
answer phrases, no-context behavior, and prints per-case pass/fail plus a final
score.
