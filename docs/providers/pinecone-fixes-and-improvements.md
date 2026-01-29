# Pinecone Integration Model for Vector Studio / Inspector

## Core Mapping

- **Connection** = one Pinecone index
- **Collections** = namespaces inside that index
- **Environment** = physical cluster (e.g., `us-east-1`)
- **Index** = logical database
- **Namespace** = logical table inside an index
- **Vector** = row (id + embedding + metadata)

This preserves the global rule: one connection → many collections (namespaces).


## Pinecone Index Dimension (Important)

- Pinecone indexes have a fixed embedding dimension set at creation.
- When connecting, always fetch the index’s dimension.
- Validate that the embedding model’s dimension matches the index’s dimension.
- If there is a mismatch, disable semantic search and show a clear warning to the user.

## Connection Setup (UI Flow)

1. **API Key** — Required for all Pinecone operations.
2. **Environment** — Required; Pinecone indexes are environment-scoped (e.g., `us-east-1`).
3. **Index Name** — Required; the “database” you’re connecting to. After selecting the environment, fetch and list available indexes.
4. **Namespace (optional)** — Defaults to `""` (empty). Users can override, but all namespaces appear as collections.

## Collections Inside the Connection

- Call `describe_index_stats` to extract all namespaces.
- Each namespace becomes a collection in the UI.
- Show vector counts next to each namespace.
- If the default namespace is empty but others have vectors, show a warning.

Example:

my-pinecone-index/
- default (0 vectors)
- docs (12,430 vectors)
- training (3,102 vectors)

## Semantic Search Capability

Semantic search is enabled only if:
- The model is recognized
- The model’s embedding dimension matches the index dimension
- The provider supports search embeddings

If not, disable the feature and show a clear message:
> Semantic search isn’t available for this embedding model.


## Visualization Behavior

- If vectorCount > 0: visualize normally
- If vectorCount = 0: show “This namespace contains no vectors”
- If other namespaces have vectors: offer to switch
- Visualization should always work in “raw mode” even if the model is unknown.

### Raw Mode Visualization
- Raw mode = visualize embeddings even if the embedding model is unknown.
- No semantic search, no normalization assumptions, and no metadata-based labeling are performed in this mode—just display the raw vectors.
# Pinecone Search API: Key Integration Details

## Metadata Filtering

Pinecone supports metadata filters, but:
- The filter syntax differs from Qdrant and other providers.
- Capabilities and supported operators may differ.
Metadata filtering is provider-specific; Pinecone filters should be normalized into the generic filter model used by Vector Inspector.

## Summary

- **Connection = Pinecone index**
- **Collections = namespaces**
- **Environment + Index are required**
- **Namespace is optional but auto-discovered**
- **No special-casing Pinecone**
- **Consistent with all other providers**

---

# Describe Your Collection

When importing a collection not created by Vector Inspector, provide details so the app can correctly interpret your data. These settings ensure accurate search, visualization, backup, and migration.

## 1. Embedding Model
- Which model produced these embeddings? (e.g., OpenAI, Cohere, HuggingFace, Custom)
- Used for semantic search compatibility checks and dimension validation.

## 2. Embedding Provider
- Where were the embeddings generated? (e.g., OpenAI, Cohere, HuggingFace, Local/Custom, Unknown)
- Determines whether semantic search can be enabled.

## 3. Primary Data Field
- Which metadata field contains the main content? (e.g., `text`, `content`, `body`, `image_url`, etc.)
- Used for labeling, previews, search results, and visualization context.

## 4. Label Field (Optional)
- Which field should be used as the display label? If not provided, the primary data field is used.

## 5. Namespace (Provider-Specific)
- Namespace name (default: `""`). Namespaces behave like tables inside the index.

## 6. Notes / Provenance (Optional)
- Any additional context about how this collection was created (e.g., “Embeddings generated using a fine-tuned model.”)

## Summary

Vector Inspector will auto-detect:
- vector dimension
- metadata keys
- vector count
- embedding shape

But it cannot infer:
- the embedding model
- the provider
- the primary data field
- the intended label field
- the correct namespace (for some providers)

Providing this information ensures full compatibility across:
- semantic search
- visualization
- backup & restore
- migration
- metadata inspection

---

# Advanced Collection Settings (Optional)

Vector Inspector will infer as much as possible about your collection. If any details are incorrect—or if your data was created outside Vector Inspector—you can override them here.

## Embedding Model
- Auto-detected or override (OpenAI, Cohere, HuggingFace, Custom)
- Used for semantic search compatibility and dimension validation.

## Embedding Provider
- Auto-detected or override (OpenAI, Cohere, HuggingFace, Local/Custom, Unknown)
- Determines whether semantic search can be enabled.

## Primary Data Field
- Auto-detected or override (e.g., `text`, `content`, `body`, etc.)
- Used for labeling, previews, search results, and visualization context.

## Label Field (Optional)
- Auto-detected or override (any metadata key). If not provided, the primary data field is used.

## Namespace (Provider-Specific)
- Auto-detected or override (list of namespaces from `describe_index_stats`).
- Namespaces behave like tables inside the index.

## Notes / Provenance (Optional)
- Additional context about how this collection was created.

## Summary

Vector Inspector will infer:
- vector dimension
- metadata keys
- vector count
- embedding shape

But it cannot infer:
- the embedding model
- the provider
- the primary data field
- the intended label field
- the correct namespace (for some providers)

Use these fields to correct or refine the metadata when needed.

---

# Pinecone Search API: Key Integration Details

Pinecone now has two incompatible search APIs:

| API      | Works When                        | Accepts Vector? | Accepts Text? | Typical Failure Mode |
|----------|-----------------------------------|:--------------:|:-------------:|---------------------|
| search() | Index has integrated embedding    |       ❌        |      ✅       | Hangs/errors if model not integrated |
| query()  | Any dense index                   |       ✅        |      ❌       | Works reliably      |

- `search()` is for indexes with an integrated model (e.g., text-embedding-3-large). Pinecone embeds the query text for you. If the index was created manually, `search()` will not work and may hang or error.
- `query()` is for raw vector search (the only correct path for custom embeddings, e.g., OpenAI, Cohere, Nomic, etc.).

**Fix for Vector Studio / Inspector:**
- Detect the index type and route accordingly:
  - If index has integrated model → use `search()` (user enters text, Pinecone embeds)
  - If index does not have integrated model → use `query()` (you embed text yourself, pass the vector)

**How to detect integrated model automatically:**
- Call `describe_index_stats`
- If the response includes `model: "text-embedding-3-large"`, use `search()`
- Otherwise, use `query()`


## Pagination

Pinecone uses cursor-based pagination (via `next_page_token`), not offset-based pagination. Do not assume offset pagination is available; always use the provided cursor for paging through results.

## Rate Limits

Pinecone enforces strict rate limits on API usage. Consider adding retry and exponential backoff logic for rate-limited operations to ensure reliability.

This approach keeps your UX unified and avoids special-casing Pinecone everywhere.

---

# Implementation Suggestions & Gaps

## Validation
- Ensure the UI validates that required metadata (embedding model, provider, primary data field) is provided or inferred. If not, prompt the user to supply missing information before enabling advanced features.

## User Feedback
- Implement clear error and warning messages as described above (e.g., when semantic search is unavailable, or when a namespace is empty but others have vectors).

## Extensibility
- The structure allows for easy extension to other providers. Keep Pinecone logic mapped to general concepts, not hardcoded, to support future providers.

## Error Handling
- Add robust error handling for API failures, including:
  - Timeouts
  - Permission/authentication errors
  - Network issues
  - Unexpected API responses
- Display actionable error messages to users and log errors for diagnostics.

## Batch Operations
- If users can select or operate on multiple namespaces or indexes, clarify and implement how the UI and backend should handle these cases (e.g., batch selection, bulk actions, or multi-namespace queries).

## Performance
- For large numbers of namespaces or vectors, consider:
  - Lazy loading or pagination in the UI
  - Efficient backend queries
  - Caching frequently accessed metadata

## Testing
- Test both integrated and non-integrated Pinecone indexes to ensure the API routing logic works as described.
- Add tests for error scenarios and edge cases (e.g., missing metadata, empty namespaces, API failures).

---

**Summary:**
These implementation notes supplement the main Pinecone integration guide, ensuring robust, user-friendly, and extensible support in Vector Inspector.
