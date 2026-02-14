"""Utilities for safely handling array-like objects (embeddings, vectors, numpy arrays)."""

from typing import Any


def has_embedding(embedding: Any) -> bool:
    """Safely check if an embedding value exists and is non-empty.

    This function avoids the "ambiguous truth value" ValueError that occurs
    when checking numpy arrays or similar array-like objects in boolean contexts.

    Args:
        embedding: The embedding/vector to check. Can be None, a list, numpy array,
                   or any array-like object.

    Returns:
        True if embedding is not None and has at least one element, False otherwise.

    Example:
        >>> import numpy as np
        >>> emb = np.zeros(128)
        >>> has_embedding(emb)  # True
        >>> has_embedding(None)  # False
        >>> has_embedding([])  # False
        >>> has_embedding([0.1, 0.2])  # True

    Note:
        Always use this function instead of `if embedding:` when working with
        embeddings that might be numpy arrays or similar types.
    """
    if embedding is None:
        return False

    # Check if it has a length attribute and use it
    if hasattr(embedding, "__len__"):
        try:
            return len(embedding) > 0
        except Exception:
            # If len() fails for some reason, fall back to truthiness check
            pass

    # Fallback: use try/except for truthiness (shouldn't reach here in normal cases)
    try:
        return bool(embedding)
    except ValueError:
        # If truthiness check fails (e.g., numpy array), assume it exists
        # since we already passed the None check
        return True
