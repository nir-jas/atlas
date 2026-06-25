# Evaluations Interview Guide

## Short Explanation

Evaluations check whether the RAG system returns the right sources and answers
for known test cases.

## Engineer-Level Explanation

RAG evals should test retrieval and generation behavior with repeatable inputs.
Useful cases include expected citations, expected answer phrases, no-context
handling, and failures caused by filters or thresholds. Evals make quality
changes safer than manual spot checks.

## 2-Minute Interview Answer

Atlas includes a lightweight RAG eval harness that seeds synthetic documents,
calls the answer endpoint with fake providers, and checks citations, expected
phrases, and no-context behavior. The goal is not to prove perfect quality; it
is to catch regressions and make retrieval or generation changes measurable.

## How Atlas Implements This

The eval runner is `scripts/run_rag_evals.py`, and the fixture is
`evals/rag_cases.json`. The harness exercises the RAG answer path exposed in
`apps/api/src/atlas_api/http/v1/rag.py`.

## Key Tradeoffs

- Deterministic fake providers make evals reliable but do not measure live model
  quality.
- Small fixtures are easy to maintain but can miss real-world edge cases.
- Phrase checks are simple but less nuanced than human or model-graded evals.

## Common Failure Modes

- Evals assert answer wording too tightly.
- Fixtures do not cover retrieval misses.
- Tests pass with fake providers but live providers behave differently.
- No-context behavior is not checked.

## Debugging Checklist

- Reproduce the failing case with the eval harness.
- Inspect expected sources and actual citations.
- Check missing answer phrases.
- Review seeded document text.
- Add a new case before changing retrieval logic.

## Common Interview Questions

- Why do RAG systems need evals?
- What should a RAG eval case assert?
- How do you separate retrieval quality from generation quality?
- What are the limits of deterministic evals?
- How do evals help with regression testing?

## Follow-Up Questions

- How would you add live-provider evals safely?
- How would you measure citation precision?
- When would you use LLM-as-judge?
- How would you track quality over time?
