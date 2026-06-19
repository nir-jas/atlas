# RAG

## Topic

Retrieval augmented generation for grounding model answers in external source
material.

## Source

Current Atlas project learning notes and public RAG concepts. This note contains
no personal or private information.

## Key Ideas

### What Problem RAG Solves

Language models answer from patterns learned during training and from the
context passed at request time. They do not automatically know private,
project-specific, or newly updated documents.

RAG solves this by retrieving relevant source material before generation. The
model answers with the retrieved context instead of relying only on its
training data.

RAG is useful when answers should be grounded in documents, citations, product
knowledge, policies, notes, or other application data.

### RAG Pipeline

A basic RAG pipeline has two phases.

Indexing phase:

1. Load documents.
2. Split documents into chunks.
3. Generate embeddings for chunks.
4. Store chunks, metadata, and vectors in a vector store.

Query phase:

1. Receive a user question.
2. Generate an embedding for the question.
3. Retrieve similar chunks from the vector store.
4. Assemble the retrieved chunks into context.
5. Ask the model to answer using that context.
6. Return the answer with sources.

### Chunking

Chunking splits large documents into smaller pieces that can be embedded,
retrieved, and passed to the model.

Good chunks should be small enough to retrieve precisely but large enough to
preserve meaning. If chunks are too small, they lose context. If chunks are too
large, retrieval becomes noisy and context windows fill quickly.

Common chunking choices:

- fixed-size chunks
- paragraph-based chunks
- heading-aware chunks
- overlapping chunks

### Embeddings

Embeddings convert text into vectors. Similar text should produce nearby
vectors.

In RAG, embeddings are used twice:

1. Document chunks are embedded during indexing.
2. User questions are embedded during retrieval.

The embedding model should match the language, domain, and retrieval quality
needed by the application.

### Vector Store

A vector store saves embeddings and supports similarity search.

For Atlas, PostgreSQL with pgvector is the planned vector store. This keeps
document metadata, chunks, and vectors close together in one database while the
project is still small.

The vector store should keep metadata such as document id, chunk id, source
name, section title, and timestamps. Metadata helps filter results and explain
where answers came from.

### Retrieval

Retrieval finds chunks likely to answer the user's question.

Basic retrieval uses vector similarity. More advanced retrieval can combine:

- vector search
- keyword search
- metadata filters
- reranking
- query rewriting

Retrieval quality strongly affects answer quality. A good prompt cannot fix
missing or irrelevant context.

### `top_k`

`top_k` is the number of retrieved chunks returned by the search step.

A low `top_k` can miss important context. A high `top_k` can add noise, cost,
and latency. The best value depends on chunk size, document type, model context
window, and answer task.

Start with a small value such as 3 to 5, then tune with evals.

### Context Assembly

Context assembly prepares retrieved chunks for the model.

The assembled context should include:

- source identifiers
- relevant chunk text
- clear separators
- instructions to answer only from provided context

Context should be ordered intentionally. Common approaches include highest
similarity first, source order, or reranked order.

## Common Failure Modes

- Documents are not chunked well.
- Embeddings do not capture the needed meaning.
- `top_k` is too low and misses the answer.
- `top_k` is too high and adds irrelevant context.
- Retrieved chunks are relevant but incomplete.
- Metadata filters exclude useful documents.
- The model ignores context and guesses.
- The prompt does not require source-grounded answers.
- The answer has no citations or source trace.
- Eval cases do not represent real user questions.

## Debugging Checklist

When a RAG answer is wrong, inspect the pipeline step by step:

- What exact question was asked?
- What query embedding was generated?
- Which chunks were retrieved?
- Were the retrieved chunks actually relevant?
- Was the answer present in the retrieved chunks?
- Was `top_k` too low or too high?
- Did metadata filtering remove useful chunks?
- Was the context assembled clearly?
- Did the prompt tell the model how to use context?
- Did the model cite the correct sources?
- Is this failure covered by an eval case?

## Implementation Notes

For Atlas, the first RAG implementation should stay small:

1. Ingest plain text or Markdown sample documents.
2. Chunk by headings or paragraphs.
3. Store chunks and metadata in PostgreSQL.
4. Store embeddings with pgvector.
5. Retrieve `top_k` similar chunks for a question.
6. Assemble context with source ids.
7. Return an answer with cited chunks.
8. Add evals for retrieval and answer quality.

## Key Lessons

- RAG is mainly a retrieval problem before it is a generation problem.
- Chunking controls what the system can retrieve.
- Embedding quality affects search quality.
- `top_k` is a tuning parameter, not a constant truth.
- Context assembly should be deliberate and inspectable.
- Answers should include source traceability.
- Debug retrieval before changing the prompt.
- Evals are required to improve RAG without guessing.

## Follow-Up Questions

- What document type should Atlas support first?
- Should Atlas start with heading-aware chunking or fixed-size chunking?
- What metadata is required for useful source citations?
- What initial `top_k` value should Atlas evaluate?
- Which eval cases prove retrieval is working?
