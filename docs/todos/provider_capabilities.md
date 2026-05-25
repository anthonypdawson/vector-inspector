# ProviderCapabilities — UI Feature Gating Per Provider

## Purpose

Add a `ProviderCapabilities` dataclass that answers the question:
**"Does this provider have the feature that this UI control requires?"**

The UI should never hard-code provider names to decide what panels or controls
to show. Instead, each provider returns a `ProviderCapabilities` instance and
the UI reads from it to show, hide, or disable panels and controls accordingly.

## Proposed Structure

```python
@dataclass
class ProviderCapabilities:
    can_show_metadata_panel: bool = True
    can_show_scalar_fields_panel: bool = False  # typed columns beyond text/metadata
    can_show_partitions_panel: bool = False      # sub-collection sharding (Milvus server)
    can_show_index_config: bool = False          # index type selection (HNSW, IVF_FLAT, etc.)
    can_show_search_params: bool = False         # nprobe, ef, etc.
    can_show_filters: bool = True
```

## Implementation Notes

- Define `ProviderCapabilities` in `core/connections/base_connection.py`
- `VectorDBConnection` exposes a `capabilities` property returning a
  `ProviderCapabilities` instance with sensible defaults (most things `False`)
- Each provider overrides only what it actually supports
- The UI reads `app_state.provider.capabilities` once per connection and drives
  all panel visibility from that object — no `isinstance` checks against provider types
- Milvus already has individual `supports_*` properties (added in feat/milvus-final)
  that should be refactored into this pattern when implemented

## Provider Matrix (Expected)

| Capability                     | ChromaDB | LanceDB | Qdrant | Milvus Lite | Milvus Server | PgVector | Pinecone |
|--------------------------------|----------|---------|--------|-------------|---------------|----------|----------|
| `can_show_metadata_panel`      | ✅       | ✅      | ✅     | ✅          | ✅            | ✅       | ✅       |
| `can_show_scalar_fields_panel` | ❌       | ✅      | ✅     | ❌          | ✅            | ✅       | ❌       |
| `can_show_partitions_panel`    | ❌       | ❌      | ❌     | ❌          | ✅            | ❌       | ❌       |
| `can_show_index_config`        | ❌       | ✅      | ✅     | ❌          | ✅            | ✅       | ❌       |
| `can_show_search_params`       | ❌       | ❌      | ✅     | ❌          | ✅            | ❌       | ❌       |
| `can_show_filters`             | ✅       | ✅      | ✅     | ✅          | ✅            | ✅       | ✅       |
