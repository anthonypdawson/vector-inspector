## Minimal Cloud Embedding Models to Test

### 1. OpenAI
- **text-embedding-3-small**
- **text-embedding-3-large**

Covers:
- API-only models
- OpenAI-style request/response patterns
- Dimension detection
- Rate limits & batching behavior

---

### 2. Cohere
- **embed-english-v3.0**
- **embed-multilingual-v3.0**

Covers:
- Non-OpenAI API semantics
- Different embedding shapes & metadata
- Error patterns unique to Cohere

---

### 3. Pinecone Serverless
- **pne-embedding-3-large** (or whatever is current in their serverless catalog)

Covers:
- Provider-hosted embeddings
- Models without traditional “names”
- Cloud-managed vector generation

---

### 4. Qdrant Cloud
- **qdrant/text-embedding-001** (or the current default)

Covers:
- Provider-specific quirks
- Multi-tenant API behavior
- Models that are named but not downloadable

---

## Why These Four Cover ~90% of Cloud Models
- OpenAI → the dominant API pattern
- Cohere → alternative API shape + multilingual
- Pinecone → cloud-managed embeddings
- Qdrant → provider-specific hosted models

Once these work, every other cloud-only embedding model will follow the same patterns.


## Cloud Embedding Model Test Harness Checklist

### 1. Basic Connectivity
- [ ] API key loaded from environment or config
- [ ] Test request succeeds (200 OK)
- [ ] Error handling works (invalid key, missing key, rate limit)

---

### 2. Embedding Request Validation
- [ ] Single‑text embedding request works
- [ ] Batch embedding request works (2–5 items)
- [ ] Response contains vector(s)
- [ ] Vector dimension matches provider documentation
- [ ] Response latency handled without blocking UI

---

### 3. Metadata Extraction
- [ ] Model name captured (if provided)
- [ ] Provider name stored
- [ ] Dimension inferred from returned vector
- [ ] Any provider‑specific metadata parsed safely

---

### 4. Error & Edge Case Handling
- [ ] Network failure handled gracefully
- [ ] Timeout handled cleanly
- [ ] Rate limit error produces a readable message
- [ ] Invalid input returns a user‑friendly error
- [ ] Empty string input handled without crashing

---

### 5. Override & Fallback Behavior
- [ ] Custom Model Override correctly routes to this provider
- [ ] Unknown model names still work via manual override
- [ ] UI shows “External / Cloud Model” when appropriate
- [ ] Features requiring local models are disabled cleanly

---

### 6. UX Confirmation
- [ ] Model appears in the model selector
- [ ] Model displays correct dimension and provider
- [ ] Re‑embedding workflow works with this model
- [ ] Errors surface in the UI without breaking the session

---

### 7. Logging & Debugging
- [ ] API request/response logged in debug mode only
- [ ] Sensitive data never logged
- [ ] Provider errors captured with context

---

### 8. Performance & Limits
- [ ] Batch size auto‑adjusts if provider has limits
- [ ] Backoff or retry logic works (if implemented)
- [ ] UI remains responsive during embedding calls