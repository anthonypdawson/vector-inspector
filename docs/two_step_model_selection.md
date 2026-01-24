# Two-Step Model Selection Implementation

## Overview

Implemented a two-step dialog flow for selecting embedding models to reduce user overwhelm and improve UX.

## Problem Solved

Previously, users saw **all models** for a dimension in a single dropdown (e.g., 17 models for 768d), making it confusing to choose. The new approach filters by provider type first.

## Implementation

### Step 1: Provider Type Selection (`ProviderTypeDialog`)

**Location**: `src/vector_inspector/ui/dialogs/provider_type_dialog.py`

Shows categorized options with model counts:
- 🤗 Sentence Transformers (Local/HuggingFace)
- 🖼️ CLIP Models (Multimodal)
- ☁️ OpenAI API (Requires API key)
- ☁️ Cohere API (Requires API key)
- ☁️ Google Vertex AI (Requires credentials)
- ☁️ Voyage AI (Requires API key)
- ✏️ Custom Model (Manual entry)

Each category shows:
- Clear description (local vs cloud, requirements)
- Count of available models for the current dimension
- API key/credential requirements clearly stated

### Step 2: Model Selection (`EmbeddingConfigDialog`)

**Location**: `src/vector_inspector/ui/dialogs/embedding_config_dialog.py`

**Updated to:**
- Accept `provider_type` parameter
- Filter models by type + dimension
- Show only relevant models (typically 1-10 instead of 17+)
- Handle "custom" type with dedicated entry form
- Update title to reflect selected provider

### Integration

**Location**: `src/vector_inspector/ui/views/info_panel.py`

Updated `_configure_embedding_model()` method to:
1. Launch `ProviderTypeDialog` first
2. Get user's provider choice
3. Launch `EmbeddingConfigDialog` with filtered results
4. Handle both steps or cancellation

## Benefits

✅ **Reduced Cognitive Load**: 5-7 categories vs 17+ models
✅ **Clear Intent**: User decides local vs cloud first
✅ **Better Discoverability**: Requirements shown upfront
✅ **Organized**: Similar models grouped
✅ **Flexible**: Still supports auto-detection and legacy paths

## Example Flow

```
User wants to configure model for 768d collection:

Step 1: "What type of provider?"
→ User selects "Sentence Transformers"

Step 2: "Which model?" (filtered to 10 sentence-transformer models)
→ User selects "BAAI/bge-base-en-v1.5"

Result: Model saved, user only saw 10 relevant models instead of 17
```

## Special Cases

### Custom Models
If user selects "Custom Model" in Step 1:
- Step 2 shows dedicated entry form
- User enters: name, type, description
- Model saved to custom registry for future use

### Legacy Compatibility
Existing code that calls `EmbeddingConfigDialog` without `provider_type` still works:
- Shows all models for dimension (old behavior)
- No breaking changes

## Testing

Run the test script:
```bash
python test_scripts/test_two_step_dialog.py
```

Tests dialogs with 384d, 768d, and 1536d collections.

## Files Changed

1. **New**: `src/vector_inspector/ui/dialogs/provider_type_dialog.py` (Step 1)
2. **Modified**: `src/vector_inspector/ui/dialogs/embedding_config_dialog.py` (Step 2)
3. **Modified**: `src/vector_inspector/ui/dialogs/__init__.py` (exports)
4. **Modified**: `src/vector_inspector/ui/views/info_panel.py` (integration)
5. **New**: `test_scripts/test_two_step_dialog.py` (testing)

## Future Enhancements

- Add icons/logos for each provider
- Show estimated model download size
- Add "Recently Used" section in Step 2
- Remember last provider choice per user
- Add tooltips with more provider details
