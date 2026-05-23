# Implementation Note: Code Reuse and Consistency

All logic for displaying embedding model metadata, handling model selection (including custom models), and surfacing model info in collection details must reuse and extend the existing model registry, settings, and collection info code paths. No duplicate or parallel implementations should be introduced. This ensures consistency, maintainability, and a single source of truth for model-related features across the application.

---

# Feature: Model‑Aware Ingestion & Modality‑Restricted Text Search

## Overview
This feature ensures that Vector Inspector always uses the correct embedding model for the data being ingested, and only enables text search when the selected embedding model actually supports text embeddings. It prevents invalid operations (like trying to run a text query against an image‑only model) and keeps the system’s behavior explicit, predictable, and forensically correct.

---

## 1. Model Selection at Collection Creation
When creating a collection, the user selects an embedding model from the Model Registry or provides a custom model.

Each model entry includes:
- Name  
- Provider (HF local, OpenAI, Cohere, custom, etc.)  
- Modality (text, image, multimodal)  
- Capabilities (`supports_text`, `supports_image`)  
- Embedding dimension  
- Normalization rules  
- Preprocessing rules  

### Custom Models
Users may add custom models with the same metadata fields as built‑in models. These models appear in the registry and can be selected during collection creation.

### Collection Details
The embedding model used for a collection is always shown in the collection details panel, including all relevant metadata. This ensures transparency and traceability.

This metadata drives ingestion and search behavior throughout the application.

---

## 2. Ingestion: Automatically Use the Correct Encoder

When the user imports data into a collection:

### Valid ingestion combinations
- Text file + text model → OK  
- Image file + image model → OK  
- Text file + multimodal model → OK  
- Image file + multimodal model → OK  

### Invalid ingestion combinations
- Text file + image‑only model → blocked  
- Image file + text‑only model → blocked  

### Batch Imports
Batch imports are always single‑modality, so mixed‑modality conflicts do not occur within a batch.

### UI Behavior
> “This model does not support this data type. Choose a multimodal model to ingest this file.”

This guarantees that every collection remains internally consistent.

---

## 3. Text Search: Enabled Only When Supported

When viewing a collection, Vector Inspector inspects the model’s capabilities and configures the UI accordingly.

### If the model supports text embeddings
- Enable the text search bar  
- Enable “Ask the AI”  
- Allow text‑based filters and queries  

### If the model does *not* support text embeddings
- Disable the text search bar  
- Tooltip:  
  **“This collection uses an image‑only embedding model. Text search is unavailable.”**

No silent fallbacks.  
No cross‑model embedding hacks.  
No mixing embedding spaces.

This preserves the forensic integrity of the tool.

---

## 4. Multimodal Models Unlock Everything

If the selected model is multimodal (e.g., CLIP, SigLIP):

- Text ingestion → allowed  
- Image ingestion → allowed  
- Text search → enabled  
- Cross‑modal behavior → correct by design  

### Examples
- **CLIP:**  
  - Text and images can be ingested into the same collection.  
  - Text queries can retrieve images, and image queries can retrieve text.  

- **SigLIP:**  
  - Supports both modalities for ingestion and search.  
  - Enables cross‑modal retrieval in a shared embedding space.

This is the “full capability” mode.

---

## 5. No Silent Fallbacks or Hidden Behavior

Vector Inspector never:
- embeds text using a different model than the collection  
- embeds images using a fallback encoder  
- mixes embedding spaces  
- guesses or infers user intent  

If the model cannot perform an operation, the UI disables the feature and explains why.

---

## 6. Why This Matters

This design:
- prevents invalid embeddings  
- prevents dimension mismatches  
- prevents meaningless search results  
- makes model behavior explicit  
- keeps collections internally consistent  
- supports custom and future models  
- aligns with Vector Inspector’s identity as a forensic vector debugging tool  

It forms the foundation for a truly model‑agnostic, provider‑agnostic Vector Inspector.