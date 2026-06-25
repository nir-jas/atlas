# Vector Databases and pgvector

## 1. Why not store embeddings as JSON?

Embeddings can be stored as JSON, but JSON is not optimized for vector search.

Problems with storing embeddings as JSON:

- Similarity calculations become slower.
- Vector indexes cannot be used effectively.
- Large numbers of embeddings may need to be loaded into application memory.
- Search performance degrades as the dataset grows.
- Query logic becomes more complex.

JSON storage can be acceptable for prototypes or learning projects but is not ideal for production retrieval systems.

---

## 2. What problem does pgvector solve?

pgvector allows PostgreSQL to store embeddings as vectors and perform similarity search directly in the database.

Benefits:

- Native vector storage.
- Efficient similarity search.
- Support for vector indexes.
- Reduced application-side computation.
- Easy combination of metadata filtering and vector search.

Example:

```text
User Query
↓
Embedding
↓
pgvector Search
↓
Top K Chunks
```

Instead of loading every embedding into the application and comparing them manually.

---

## 3. Why is vector search different from SQL LIKE?

SQL LIKE performs literal text matching.

Example:

```sql
WHERE text LIKE '%dog%'
```

This only finds records containing the exact word "dog".

Vector search performs semantic matching.

Example:

```text
Query: puppy
```

Can match:

```text
dog
canine
pet
golden retriever
```

even when the exact word "puppy" is not present.

Vector search compares meaning rather than exact text patterns.

---

## 4. How Atlas stores vectors

Atlas keeps document chunks (`chunks`) and `chunk_embeddings` as separate tables. A
chunk is source content and metadata: document ownership, section, position,
and text. An embedding is derived model output with provider, model, dimension,
and creation metadata. Keeping them separate means a chunk can be re-embedded
or tracked by model without mixing mutable derived data into source content.

The `chunk_embeddings.embedding` column is PostgreSQL's `vector` type, not a
JSON array. The database can therefore compute cosine distance without loading
all embeddings into Python.

## 5. Vector dimensions

A dimension is one numeric coordinate in an embedding. All vectors compared in
a similarity operation must have the same dimension. Atlas records dimensions
with each embedding and filters retrieval to the query's dimension before
pgvector computes distance. This keeps a later model migration safe: index
documents with the new model, then query against its compatible vectors.

`VECTOR_DIMENSIONS` is sent to the selected provider. The default
`text-embedding-3-small` configuration uses 1536 dimensions. Changing the
model or dimension requires re-indexing the documents that should be retrieved
with that new representation.

## 6. How retrieval works now

1. Indexing splits a document into chunks, requests embeddings from the
   configured provider in a batch, and stores them in `chunk_embeddings`.
2. `/rag/search` requests an embedding for the user query from the same
   configured provider.
3. The retrieval repository joins chunks, documents, and embeddings; applies
   the optional collection filter and dimension filter; then orders by
   pgvector cosine distance.
4. It returns the nearest `top_k` chunks and converts cosine distance to the
   existing similarity-score response field.

This preserves the endpoint contract while moving ranking and metadata
filtering into PostgreSQL.

## 7. When would database-side similarity be preferred?

Database-side similarity is preferred when:

- The dataset becomes large.
- Fast retrieval is required.
- Metadata filtering is needed.
- Multiple users perform searches simultaneously.
- Production reliability and scalability matter.

Examples:

- Thousands to millions of chunks.
- Enterprise knowledge bases.
- Production RAG systems.

Benefits:

- Better performance.
- Vector indexing support.
- Lower application memory usage.
- Easier scaling.

Example:

```text
Application
↓
Generate Query Embedding
↓
Database
↓
Vector Search
↓
Top K Results
```

---

## Key Lessons

- SQL LIKE matches text.
- Vector search matches meaning.
- Embeddings should be treated as vectors, not just JSON blobs.
- pgvector enables efficient semantic search inside PostgreSQL.
- Database-side similarity is the preferred approach for production systems.
- Retrieval quality is one of the most important factors in RAG systems.

## Mental Model

```text
Document indexing
↓
Chunk embeddings stored separately
↓
Query embedding
↓
pgvector metadata-filtered search
↓
Top K chunks
```
