"""Test embedding handling in UI components."""

import numpy as np
from PySide6.QtWidgets import QApplication

from vector_inspector.ui.components.item_details_dialog import ItemDetailsDialog
from vector_inspector.utils import has_embedding


def test_has_embedding_utility():
    """Ensure has_embedding() handles various input types safely."""
    # Test None
    assert has_embedding(None) is False

    # Test empty list
    assert has_embedding([]) is False

    # Test list with values
    assert has_embedding([0.1, 0.2, 0.3]) is True

    # Test NumPy arrays (the key case that triggers ValueError with direct truthiness)
    assert has_embedding(np.zeros(16)) is True
    assert has_embedding(np.array([])) is False

    # Test single-element arrays
    assert has_embedding(np.array([1.0])) is True


def test_item_details_dialog_handles_numpy_embedding():
    """Ensure ItemDetailsDialog can be created with a NumPy embedding without error."""
    app = QApplication.instance() or QApplication([])

    embedding = np.zeros(16)
    item = {
        "id": "test-1",
        "document": "hello world",
        "metadata": {"foo": "bar"},
        "embedding": embedding,
    }

    dlg = ItemDetailsDialog(None, item_data=item, show_search_info=False)

    # Populate fields (constructor already calls it) and ensure vector_display exists and contains a dimension hint
    if dlg.vector_display is None:
        # If embedding widget wasn't created, that's unexpected for this test
        raise AssertionError("vector_display should be present for embedding")

    text = dlg.vector_display.toPlainText()
    assert "Dimension" in text or "dimension" in text.lower()

    # Clean up
    dlg.accept()
    try:
        app.quit()
    except Exception:
        pass


def test_item_details_dialog_handles_empty_embedding():
    """Ensure ItemDetailsDialog handles empty/None embeddings gracefully."""
    app = QApplication.instance() or QApplication([])

    # Test with None embedding
    item_none = {
        "id": "test-2",
        "document": "hello",
        "metadata": {},
        "embedding": None,
    }

    dlg_none = ItemDetailsDialog(None, item_data=item_none, show_search_info=False)
    # vector_display should not be created for None embedding
    assert dlg_none.vector_display is None
    dlg_none.accept()

    # Test with empty array
    item_empty = {
        "id": "test-3",
        "document": "world",
        "metadata": {},
        "embedding": np.array([]),
    }

    dlg_empty = ItemDetailsDialog(None, item_data=item_empty, show_search_info=False)
    # vector_display should not be created for empty embedding
    assert dlg_empty.vector_display is None
    dlg_empty.accept()

    try:
        app.quit()
    except Exception:
        pass
