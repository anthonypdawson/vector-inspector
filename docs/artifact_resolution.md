# Hybrid Artifact Resolution — Product Requirements Document (PRD)

## 1. Overview
Vector Inspector needs to support multimodal similarity explanations (text, image, audio later) across multiple vector providers (Chroma, Qdrant, pgvector, etc.) and multiple model providers (OpenAI, Google, Anthropic, local models).
To do this, the system must determine **where the original artifact lives** and **what type it is**.

The hybrid approach combines:

- Automatic artifact resolution (best effort)
- Manual user‑provided artifact upload (fallback)

This ensures a smooth experience without brittle assumptions.

## 2. Goals

### Primary Goals
- Automatically infer artifact type (text, image, audio) from metadata, URLs, or payload structure.
- Automatically retrieve artifacts when possible.
- Gracefully request user input when automatic resolution fails.
- Provide a unified interface for multimodal similarity explanations.

### Secondary Goals
- Maintain provider‑agnostic architecture.
- Support future modalities (video, documents).
- Preserve the forensic, artifact‑driven philosophy of the tool.

## 3. Non‑Goals
- No attempt to reverse‑engineer embeddings.
- No requirement to store or cache large artifacts permanently.
- No assumption that vector DBs contain complete or correct metadata.
- No automatic downloading of unknown or unsafe URLs without user confirmation.

## 4. User Stories

### 4.1 Automatic Resolution
- As a user, when I click a datapoint, I want the Inspector to automatically show me the original text or image if it can be resolved from metadata or URLs.

### 4.2 Manual Fallback
- As a user, if the Inspector cannot locate the artifact, I want it to clearly show me the metadata and allow me to upload the missing file.

### 4.3 Multimodal Explanation
- As a user, when comparing two datapoints, I want the Inspector to explain their similarity using the correct model (text LLM, vision LLM, audio LLM later).

### 4.4 Transparency
- As a user, I want to know how the Inspector determined the artifact type and whether it was automatically resolved or manually provided.

## 5. System Architecture

### 5.1 Source Resolver (new component)
A deterministic inference engine that attempts to identify:

- modality (text, image, audio)
- source type (inline metadata, URL, file path)
- retrieval method (fetch, local read, user upload)
- confidence score

#### Inference Layers
1. Explicit metadata (type, mime_type, content_type)
2. File extension (.jpg, .mp3, .srt)
3. URL pattern recognition
4. Payload structure (presence of text, caption, duration, etc.)
5. Content signature (magic bytes) if fetched

#### Output Example (escaped so it doesn't break the block)
\{
  "modality": "image",
  "source_type": "url",
  "source": "https://example.com/frame_42.png",
  "confidence": 0.93
\}

### 5.2 Artifact Retrieval Layer
Given a Source Resolver result:

- If source_type = inline_metadata → return content directly
- If source_type = url → attempt fetch
- If source_type = file_path → attempt local read
- If retrieval fails → trigger user upload flow

### 5.3 Model Provider Router
Selects the correct model based on modality:

- Text → text LLM
- Image → vision LLM
- Audio → audio LLM (future)

Supports multiple providers:

- OpenAI
- Google
- Anthropic
- Local models

### 5.4 Similarity Explanation Engine
Combines:

1. Structural evidence (vector DB)
2. Artifact evidence (LLM or vision model)
3. Metadata evidence (payload)

Produces a unified explanation.

## 6. UX Flow

### 6.1 Automatic Success Path
1. User selects datapoint
2. Source Resolver identifies artifact
3. Artifact is retrieved
4. Inspector displays preview
5. Similarity explanation uses correct model

### 6.2 Fallback Path
1. Source Resolver fails or retrieval fails
2. Inspector displays metadata
3. Inspector prompts user:
   “Artifact not accessible. Provide the file to enable preview and similarity explanations.”
4. User uploads file
5. Inspector continues normally

## 7. Edge Cases
- Broken URLs
- Missing metadata
- Mixed‑modality collections
- Incorrect file extensions
- Private or authenticated URLs
- Large files (audio/video)
- User uploads wrong file type

System must fail gracefully and clearly.

## 8. Performance Requirements
- Source Resolver must complete inference in < 50ms.
- Artifact retrieval must timeout gracefully.
- Similarity explanations must complete within model provider limits.
- No blocking UI during resolution.

## 9. Security & Privacy
- Never auto‑download from unknown domains without user confirmation.
- Never store user‑uploaded artifacts beyond session unless explicitly saved.
- Respect provider API limits and privacy constraints.

## 10. Future Extensions
- Video modality
- Document modality (PDF, DOCX)
- Batch artifact resolution
- Provenance tracing
- “Reconstruct missing artifacts” workflow
