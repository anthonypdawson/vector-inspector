Embedding truthiness checks (NumPy arrays)

Problem

- NumPy arrays and similar array-like types raise a ValueError when used in boolean contexts (e.g., `if embedding:`) because their truth value is ambiguous when they contain more than one element.

Why this matters

- UI code often checks `if embedding:` to decide whether to display an embedding preview. That pattern will raise a runtime error when `embedding` is a NumPy array.

Recommended approach (use the utility function)

**Always use the `has_embedding()` utility function from `vector_inspector.utils`:**

```python
from vector_inspector.utils import has_embedding

embedding = item.get("embedding")
if has_embedding(embedding):
    # show embedding preview
```

This function safely handles:
- None values
- Empty arrays/lists
- NumPy arrays
- Any array-like object with `__len__`

Where we use it in the codebase

The `has_embedding()` utility is now used consistently across the codebase:

**UI Components:**
- `ui/components/item_details_dialog.py` - Checking embeddings in setup and populate (2 uses)
- `ui/views/metadata_view.py` - Preserving existing embeddings on edit

**Core Connections:**
- `core/connections/chroma_connection.py` - Checking first embedding in samples (2 uses)

**Services:**
- `services/backup_restore_service.py` - Inferring dimension from first embedding

**Vector Studio:**
- `vector_studio/features/table_context_menu.py` - Validating embeddings for similarity search (2 uses)

Alternative patterns (if you can't use the utility)

- Safe, dependency-free check:

```python
embedding = item.get("embedding")
has_emb = embedding is not None and (
    hasattr(embedding, "__len__") and len(embedding) > 0
)
if has_emb:
    # show embedding preview
```

- NumPy-friendly check (if you already depend on NumPy):

```python
import numpy as np
if embedding is not None and np.asarray(embedding).size > 0:
    # show embedding preview
```

- Defensive try/except (fallback):

```python
try:
    if len(embedding) > 0:
        # show
except TypeError:
    # embedding is scalar or not-sized
    if embedding is not None:
        # show
```

Tests

- `tests/test_item_details_embedding.py` contains comprehensive tests:
  - `test_has_embedding_utility()` - Tests the utility with various input types
  - `test_item_details_dialog_handles_numpy_embedding()` - Tests dialog with NumPy arrays
  - `test_item_details_dialog_handles_empty_embedding()` - Tests empty/None handling

Notes

- The `has_embedding()` utility is exported from `vector_inspector.utils` and should be used throughout the codebase.
- When adding new UI logic that inspects embeddings, always use `has_embedding()` and add a small unit test to prevent regressions.
- Do NOT use `if embedding:`, `if vector:`, or similar direct truthiness checks on array-like objects.
- Lists of embeddings (e.g., `embeddings: list[list[float]]`) can still use normal truthiness checks - this utility is for individual embedding vectors.
