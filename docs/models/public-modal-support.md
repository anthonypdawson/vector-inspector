## Recommended Local/Public Embedding Models to Support Out of the Box

### 🔹 1. BAAI / FlagEmbedding (Massively Popular, High Quality)
- **BAAI/bge-small-en-v1.5** (384d)
- **BAAI/bge-base-en-v1.5** (768d)
- **BAAI/bge-large-en-v1.5** (1024d)
- **BAAI/bge-m3** (1024d, multi‑function: dense + sparse)

Why include:
- Industry standard for open-source embeddings
- Strong performance across retrieval benchmarks
- Stable, widely adopted, predictable

---

### 🔹 2. Sentence Transformers (The Classic Workhorses)
- **sentence-transformers/all-MiniLM-L6-v2** (384d)
- **sentence-transformers/all-mpnet-base-v2** (768d)
- **sentence-transformers/multi-qa-MiniLM-L6-cos-v1** (384d)
- **sentence-transformers/e5-base-v2** (768d)
- **sentence-transformers/e5-large-v2** (1024d)

Why include:
- Hugely popular
- Great for backward compatibility
- Many existing collections use these

---

### 🔹 3. Jina AI (Fast, Modern, High‑Quality)
- **jinaai/jina-embeddings-v2-small-en** (512d)
- **jinaai/jina-embeddings-v2-base-en** (768d)
- **jinaai/jina-embeddings-v3** (1536d, multilingual)

Why include:
- Very fast
- High quality
- Strong multilingual support

---

### 🔹 4. Mistral / Voyage‑style Open Models
- **mistralai/mistral-embed** (1024d)
- **intfloat/e5-mistral-7b-instruct** (4096d)

Why include:
- Modern architectures
- Strong performance in semantic search
- Becoming increasingly common

---

### 🔹 5. GTE / Alibaba Models (Lightweight, Strong Baselines)
- **Alibaba-NLP/gte-small** (384d)
- **Alibaba-NLP/gte-base** (768d)
- **Alibaba-NLP/gte-large** (1024d)

Why include:
- Very fast
- Good accuracy for their size
- Common in production pipelines

---

### 🔹 6. Cohere Open Models (When Available Locally)
- **Cohere/embed-english-light-v3.0** (384d)
- **Cohere/embed-multilingual-light-v3.0** (384d)

Why include:
- Cohere is widely used
- These models are often mirrored on HuggingFace

---

### 🔹 7. Misc High‑Value Additions
- **nomic-ai/nomic-embed-text-v1** (768d)
- **thenlper/gte-small** (384d)
- **thenlper/gte-base** (768d)

Why include:
- Popular in open‑source RAG stacks
- Good performance/size tradeoffs

---

## Why This Set Works
- Covers **all major embedding families**
- Includes **small, base, and large** variants
- Covers **384d, 512d, 768d, 1024d, 1536d, 4096d** — the most common dims
- Represents **English, multilingual, dense, and hybrid** models
- Matches what real teams actually use in production

This gives Vector Inspector **maximum compatibility** with minimal bloat.


## Recommended Default Embedding Models by Dimension

### **384 dimensions**
**Default:** `sentence-transformers/all-MiniLM-L6-v2`
Why: Extremely popular, tiny, fast, stable, and widely used in production.

**Alternatives:**
- `BAAI/bge-small-en-v1.5`
- `Alibaba-NLP/gte-small`

---

### **512 dimensions**
**Default:** `jinaai/jina-embeddings-v2-small-en`
Why: Modern, fast, high‑quality, and lightweight.

**Alternatives:**
- `intfloat/e5-small-v2`
- `sentence-transformers/all-MiniLM-L12-v2`

---

### **768 dimensions**
**Default:** `sentence-transformers/all-mpnet-base-v2`
Why: One of the most widely used 768d models; strong performance and stable.

**Alternatives:**
- `BAAI/bge-base-en-v1.5`
- `Alibaba-NLP/gte-base`
- `intfloat/e5-base-v2`

---

### **1024 dimensions**
**Default:** `BAAI/bge-large-en-v1.5`
Why: High‑quality, widely adopted, and a strong “large” model baseline.

**Alternatives:**
- `Alibaba-NLP/gte-large`
- `intfloat/e5-large-v2`

---

### **1536 dimensions**
**Default:** `jinaai/jina-embeddings-v3`
Why: Modern, multilingual, high‑quality, and actively maintained.

**Alternatives:**
- (Few open‑source 1536d models exist; Jina v3 is the best choice.)

---

### **4096 dimensions**
**Default:** `intfloat/e5-mistral-7b-instruct`
Why: Strong performance, widely used in advanced RAG setups, and consistent.

**Alternatives:**
- (Most 4096d models are LLM‑derived; this is the cleanest option.)

---

## Why this list works
- Covers the **most common dimensions** you’ll encounter in real collections
- Uses **models that are easy to load locally**
- Avoids massive downloads or obscure research models
- Gives users a **predictable, high‑quality fallback**
- Keeps your UI clean and your defaults trustworthy