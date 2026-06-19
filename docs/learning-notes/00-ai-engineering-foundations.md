# AI Engineering Foundations

## Topic

Core concepts for building production-oriented AI applications with language
models, retrieval, tools, memory, and evaluation.

## Source

Current Atlas project learning notes and public AI Engineering concepts. This
note contains no personal or private information.

## Key Ideas

### AI Engineering

AI Engineering is the practice of building reliable software systems around AI
models. It combines backend engineering, product design, data handling,
retrieval, model integration, evaluation, observability, and safety.

The goal is not only to call a model API. The goal is to build a system that
can take user input, gather the right context, call the right model or tool,
return useful output, and be tested and improved over time.

### Embeddings

Embeddings turn text, images, or other data into numeric vectors. Similar items
should have vectors that are close together in vector space.

In AI applications, embeddings are commonly used for semantic search. Instead
of matching exact keywords, the system can find content with similar meaning.

Typical flow:

1. Split documents into chunks.
2. Generate an embedding for each chunk.
3. Store chunks and vectors in a database.
4. Embed the user's query.
5. Search for nearby vectors.

### RAG

RAG means retrieval augmented generation. A RAG system retrieves relevant source
material before asking a model to answer.

The model receives both the user question and retrieved context. This helps the
answer stay grounded in known documents instead of relying only on model
training data.

A basic RAG pipeline:

1. Ingest documents.
2. Chunk the documents.
3. Embed the chunks.
4. Store vectors in a vector database.
5. Retrieve relevant chunks for a question.
6. Generate an answer with source context.

### Memory

Memory is information kept across interactions. It can be short-term, such as
the current conversation, or long-term, such as saved user preferences, project
facts, or prior decisions.

Memory should be explicit and controlled. A system should know what is stored,
why it is stored, when it should be used, and how stale or sensitive it might
be.

### Tools

Tools let a model interact with external systems. Examples include search,
databases, calendars, file parsers, code execution, and internal APIs.

Tool use should be constrained by clear schemas, permissions, and validation.
The application should decide which tools exist and how results are checked.

### Context Window

The context window is the amount of input a model can consider at once. It can
include instructions, conversation history, retrieved documents, tool results,
and the user's request.

Context is limited, so AI systems need context selection. More context is not
always better. The system should pass only the information needed for the task.

### Structured Outputs

Structured outputs make model responses easier to validate and use in software.
Instead of asking for free-form text, the application can request JSON or
schema-shaped data.

Structured outputs are useful for extraction, classification, routing, tool
calls, eval results, and UI-ready responses.

### Debugging AI Systems

Debugging AI systems means inspecting both software behavior and model behavior.
Useful signals include:

- input prompt
- retrieved context
- tool calls and tool results
- model response
- latency and cost
- validation errors
- user feedback
- eval scores

Good debugging requires reproducible test cases. If a model answer is wrong,
check whether the issue came from missing context, bad retrieval, poor
instructions, invalid tool output, weak schemas, or unrealistic expectations.

## Implementation Notes

For Atlas, the first useful implementation target is a small RAG loop:

1. Upload or load a safe sample document.
2. Chunk the text.
3. Generate embeddings.
4. Store chunks and vectors in PostgreSQL with pgvector.
5. Retrieve relevant chunks for a question.
6. Generate an answer with cited source chunks.
7. Add eval cases that verify retrieval and answer quality.

Keep the backend boundaries clear:

- HTTP routes handle requests and responses.
- Services coordinate use cases.
- Repositories hide storage details.
- AI providers hide model-specific details.
- Evals measure whether behavior improved or regressed.

## Key Lessons

- AI apps are software systems first.
- Retrieval quality often matters more than prompt wording.
- Context should be selected, not dumped.
- Memory needs rules, not just storage.
- Tool outputs must be validated before the model or user relies on them.
- Structured outputs make AI behavior easier to test.
- Evals are how AI systems improve without guessing.
- Start with one complete workflow before adding many features.

## Follow-Up Questions

- What document types should Atlas ingest first?
- What chunking strategy works best for learning notes?
- Which embedding model should be used for the first implementation?
- What makes an answer acceptable in the first Atlas eval set?
- How should source citations appear in API responses and the frontend?
