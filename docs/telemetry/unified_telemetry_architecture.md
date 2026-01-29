# Unified Telemetry Architecture: Model Metadata & Persistence

This document combines the privacy-focused telemetry payload from `model_telemetry_and_registry.md` with the practical Netlify Function and GitHub NDJSON persistence patterns from `netlify.md` and `netlify-to-github.md`.

---

## 1. Telemetry Payload (Opt-In, Privacy-Safe)

**Fields to Collect:**
- `model_name`
- `model_source` (e.g., sentence-transformers, nomic, openai, local_path)
- `model_version` (if available)
- `embedding_dimension`
- `modalities` (e.g., text, image, multimodal)
- `distance_metric` (if detectable)
- `normalization` (e.g., L2, none)
- `load_success` (true/false)
- `inference_success` (true/false)
- `device_type` (cpu/gpu)
- `local_path_hash` (hash of local model path, if applicable)
- `timestamp`
- `client_id` (locally generated UUID, for deduplication/analytics)

**Principles:**
- Opt-in only, disabled by default
- Never send credentials, file paths, or user content
- User can view, send, or purge queued events

---

## 2. Telemetry Submission Flow

- App POSTs telemetry payload to a Netlify Function endpoint
- Includes a shared secret header: `X-Telemetry-Key: <secret>`
- No user identity, no sensitive data, no complex auth

---

## 3. Netlify Function: Append to GitHub NDJSON

- Accepts POST, validates shared secret
- Parses payload (must match above schema)
- Fetches NDJSON file from GitHub
- Appends new line: `JSON.stringify(payload)`
- Writes updated file back to GitHub

**Example (pseudo-JS):**
```js
// ...existing code for secret validation...
const newLine = JSON.stringify(payload);
const updatedContent = existingContent + "\n" + newLine;
// ...write updatedContent back to GitHub...
```

---

## 4. Implementation Checklist

- [ ] Implement telemetry payload as above
- [ ] Store queued events locally until user opts in
- [ ] POST events to Netlify endpoint with shared secret
- [ ] Netlify Function appends each event as NDJSON line in GitHub file
- [ ] Document opt-in, privacy, and user controls

---

**References:**
- See `model_telemetry_and_registry.md` for payload details
- See `netlify.md` and `netlify-to-github.md` for endpoint and persistence patterns
