# Atlas v1

## Goal

Upload documents and ask questions over them.

## Architecture

User
↓
Upload Document
↓
Document Storage
↓
Chunking
↓
Embeddings
↓
Vector Store
↓
Retrieval
↓
LLM
↓
Answer with Citations

## Core Components

### Document Service

Responsible for:

- storing documents
- extracting text

### Chunking Service

Responsible for:

- splitting documents into chunks

### Embedding Service

Responsible for:

- generating embeddings

### Retrieval Service

Responsible for:

- similarity search

### LLM Service

Responsible for:

- answer generation

## Learning Goals

- FastAPI
- Python
- RAG
- Embeddings
- pgvector
- Retrieval
- AI System Design
