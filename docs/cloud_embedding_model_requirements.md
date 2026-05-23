# Requirements: Cloud Embedding Model Selection and API Key Management

## Overview
This document outlines the requirements for enabling users to select and use cloud-provided embedding models (e.g., OpenAI, Cohere, Azure, etc.) in the custom model selection UI. These models require API keys for access. The system must support secure API key management, model discovery, and restrict actions when credentials are missing.

## Functional Requirements

### 1. Model Selection UI
- Users can select from a list of available embedding models, including cloud-based models.
- The UI should clearly indicate which models require API keys.
- Models should be gr
ouped or labeled by provider (e.g., OpenAI, Cohere, Azure).

### 2. API Key Management
- Users can securely enter and store API keys for each supported provider.
- The settings UI must provide fields for entering/updating API keys.
- API keys must be stored securely (e.g., encrypted on disk, or using OS keyring).
- The system should never display API keys in plain text after entry.
- Users can remove or update API keys at any time.

### 3. Model Registry/Discovery
- The application maintains a registry of available embedding models, including:
  - Model name
  - Provider
  - Required API key (yes/no)
  - Model description and capabilities
- The registry can be updated to add new models/providers.
- The system can auto-detect available models based on present API keys and provider availability.
- Models with missing API keys are shown as unavailable or disabled in the UI.

### 4. Usage Restrictions
- Actions that require a cloud embedding model (e.g., semantic search, embedding new data) are disabled or prompt for API key if not present.
- The UI provides clear feedback when an action is blocked due to missing credentials.
- If a user attempts to use a model without a valid API key, the system prompts for the key or directs them to settings.

### 5. Reuse and Integration
- Once an API key is provided, the model becomes available for all relevant features (semantic search, batch embedding, etc.).
- The system reuses the configured model and credentials for all applicable workflows.
- The model registry is used to populate selection lists and validate model availability.

## Non-Functional Requirements
- API keys must be handled securely and never logged or exposed.
- The system should be extensible to support new providers/models in the future.
- Documentation should clearly explain how to add API keys and select cloud models.

## Example Workflow
1. User opens the custom model selection UI.
2. User sees a list of local and cloud models. Cloud models requiring API keys are marked.
3. User selects a cloud model (e.g., OpenAI Ada).
4. If no API key is present, the UI prompts the user to enter one in settings.
5. Once the key is entered, the model is enabled and can be used for semantic search and embedding.
6. If the key is removed, the model becomes unavailable and related actions are disabled.

## Open Questions
- Should API keys be scoped per user or per project?
- Should the system support multiple keys per provider (e.g., for different accounts)?
- How should errors from invalid/expired API keys be handled in the UI?

---

This document should be updated as requirements evolve or new providers are added.
