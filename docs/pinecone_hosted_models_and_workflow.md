# Pinecone Hosted Models & Workflow Integration

**Last updated:** January 24, 2026

## Overview

Pinecone now offers hosted embedding and reranking models that change the upsert and query workflow. When using a Pinecone-hosted model, you send raw text to Pinecone, and it handles embedding and vectorization internally. This is different from the traditional workflow, where you generate embeddings client-side.

This document summarizes:
- The list of Pinecone-hosted models (as of Jan 2026)
- How to detect and handle hosted models in code
- The required changes to upsert and query logic
- UI/UX and documentation recommendations

---

## Pinecone Hosted Models (Jan 2026)

| Model Name                      | Provider                   | Type       | Modality | Vector Type | Max Input      | Starter Limits |
|---------------------------------|----------------------------|------------|----------|-------------|----------------|----------------|
| llama-text-embed-v2             | NVIDIA - NV-Embed-v2       | Embedding  | Text     | Dense       | 2,048 tokens   | 5M tokens      |
| multilingual-e5-large           | BGE-M3-557 - HGS162        | Embedding  | Text     | Dense       | 507 tokens     | 5M tokens      |
| pinecone-sparse-english-v0      | PINECONE - HGS162          | Embedding  | Text     | Sparse      | 512 tokens     | Not available  |
| bge-reranker-v2-m3              | BAAI - HGS162              | Reranking  | Text     | Dense       | 1,024 tokens   | 500 Req        |
| cohere-rerank-3.5               | COHERE                     | Reranking  | Text     | Dense       | 40,000 tokens  | Not available  |
| pinecone-rerank-v0              | PINECONE - HGS162          | Reranking  | Text     | Dense       | 512 tokens     | Not available  |

*Source: Pinecone Inference UI, Jan 2026*

---

## Workflow Differences

### 1. Hosted Model Indexes
- **Upsert:**
  - Send text records: `{ "id": ..., "text": ... }`
  - Use `index.upsert_records()`
- **Query:**
  - Send text query: `{ "inputs": { "text": ... } }`
  - Use `index.search()`
- **No need to generate embeddings client-side.**

### 2. External/Custom Model Indexes
- **Upsert:**
  - Generate embeddings client-side
  - Use `index.upsert()` with vectors
- **Query:**
  - Generate embedding for query
  - Use `index.query()` with vector

---

## Example: Hosted Model Upsert & Query

```python
from pinecone import Pinecone

pc = Pinecone(api_key="YOUR_API_KEY")
index = pc.Index("pinecone-sparse-english-v0-index")

# Upsert text records
records = [
    {"id": "vec1", "text": "Apple is a popular fruit known for its sweetness and crisp texture."},
    {"id": "vec2", "text": "The tech company Apple is known for its innovative products like the iPhone."},
    # ...
]
index.upsert_records(namespace="example-namespace", records=records)

# Query with text
query = "Tell me about the tech company known as Apple."
results = index.search(
    namespace="example-namespace",
    query={"inputs": {"text": query}, "top_k": 3}
)
```

---

## Integration Recommendations

### 1. Detection
- **Maintain a list of known Pinecone-hosted models** (see above table)
- **Detect hosted model usage** by index name, metadata, or user selection

### 2. Code Path
- **If hosted model:**
  - Upsert: Accept text, use `upsert_records`
  - Query: Accept text, use `search`
- **If external model:**
  - Upsert: Accept embeddings, use `upsert`
  - Query: Accept embeddings, use `query`

### 3. UI/UX
- When a Pinecone-hosted model is detected:
  - Hide embedding model selection (model is fixed)
  - Show message: "This index uses a Pinecone-hosted embedding model. Text will be embedded automatically."

### 4. Documentation
- Clearly document the difference in workflow for users
- Add help panel/README section for Pinecone-hosted model support

---

## Future Work
- Consider auto-detecting hosted models via Pinecone API (if/when supported)
- Keep hosted model list up to date as Pinecone adds new models
- Add support for new modalities (e.g., image, audio) if Pinecone introduces them

---

## References
- [Pinecone Inference UI](https://app.pinecone.io/)
- [Pinecone Docs](https://docs.pinecone.io/)
