# Checklist: Adding and Managing Public Embedding Models

## 1. Model Integration
- [ ] Check if the model is already supported (avoid duplicates)
- [ ] Confirm model is available on HuggingFace or compatible source
- [ ] Add model name and metadata (dimension, language, provider) to allowlist/catalog
- [ ] Test loading with `from_pretrained` (or equivalent)
- [ ] Validate embedding output shape and type
- [ ] Handle any special requirements (e.g., dense+sparse, multilingual)
- [ ] Add/verify required dependencies (e.g., transformers, sentence-transformers, torch)

## 2. User Experience
- [ ] Update UI to display all available models, grouped by provider/source
- [ ] Implement search/filter functionality for model selection (by name, dimension, language, provider, etc.)
- [ ] Allow users to select or enter a custom model name
- [ ] Show model details (dimension, language, provider, etc.) on selection

## 3. Testing & Validation
- [ ] Test batch and single inference for each model
- [ ] Validate error handling for missing/invalid models
- [ ] Confirm metadata extraction (dimension, provider, etc.)
- [ ] Ensure compatibility with telemetry payload (model_name, source, etc.)

## 4. Maintenance
- [ ] Periodically review and update the allowlist/catalog as new models become popular
- [ ] Add ability to fetch model metadata dynamically (optional, for very large lists)
- [ ] Document any model-specific quirks or requirements

---

**Scalability Note:**
As the list grows, prioritize:
- Efficient search/filter in the UI
- Grouping by provider/source
- Optionally, lazy loading or paginating large model lists

---

This checklist will help ensure smooth expansion and management of supported public embedding models.
