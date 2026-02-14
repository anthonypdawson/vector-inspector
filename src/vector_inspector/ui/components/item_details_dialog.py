"""Dialog for viewing item details (read-only)."""

import json
from typing import Any, Optional

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from vector_inspector.utils import has_embedding


class ItemDetailsDialog(QDialog):
    """Dialog for viewing vector item details (read-only)."""

    item_data: dict[str, Any]
    id_label: QLabel
    document_display: QTextEdit
    metadata_display: QTextEdit
    distance_label: Optional[QLabel]
    rank_label: Optional[QLabel]
    vector_display: Optional[QTextEdit]

    def __init__(
        self,
        parent=None,
        item_data: Optional[dict[str, Any]] = None,
        show_search_info: bool = False,
    ):
        """Initialize the details dialog.

        Args:
            parent: Parent widget
            item_data: Dictionary containing item data with keys:
                - id: Item ID
                - document: Document text
                - metadata: Metadata dictionary
                - distance: (optional) Search distance/similarity score
                - rank: (optional) Search result rank
                - embedding: (optional) Vector embedding
            show_search_info: If True, show distance and rank fields
        """
        super().__init__(parent)
        self.item_data = item_data or {}
        self.show_search_info = show_search_info
        self.setWindowTitle("Item Details")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self._setup_ui()
        self._populate_fields()

    def _setup_ui(self):
        """Setup dialog UI."""
        layout = QVBoxLayout(self)

        # Form layout
        form_layout = QFormLayout()

        # ID field
        self.id_label = QLabel()
        self.id_label.setStyleSheet("font-weight: bold;")
        form_layout.addRow("ID:", self.id_label)

        # Search-specific fields (if applicable)
        if self.show_search_info:
            self.rank_label = QLabel()
            form_layout.addRow("Rank:", self.rank_label)

            self.distance_label = QLabel()
            form_layout.addRow("Distance:", self.distance_label)

        # Document field
        form_layout.addRow("Document:", QLabel(""))
        self.document_display = QTextEdit()
        self.document_display.setReadOnly(True)
        self.document_display.setMaximumHeight(150)
        form_layout.addRow(self.document_display)

        # Metadata field
        form_layout.addRow("Metadata:", QLabel(""))
        self.metadata_display = QTextEdit()
        self.metadata_display.setReadOnly(True)
        self.metadata_display.setMaximumHeight(150)
        form_layout.addRow(self.metadata_display)

        # Vector embedding field (collapsible)
        # Use safe check to avoid "ambiguous truth value" error with arrays
        embedding = self.item_data.get("embedding")
        if has_embedding(embedding):
            form_layout.addRow("Vector Embedding:", QLabel(""))
            self.vector_display = QTextEdit()
            self.vector_display.setReadOnly(True)
            self.vector_display.setMaximumHeight(100)
            form_layout.addRow(self.vector_display)
        else:
            self.vector_display = None

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_button.setDefault(True)

        button_layout.addStretch()
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def _populate_fields(self):
        """Populate fields with item data."""
        # ID
        self.id_label.setText(str(self.item_data.get("id", "")))

        # Search-specific fields
        if self.show_search_info:
            if hasattr(self, "rank_label") and self.rank_label:
                rank = self.item_data.get("rank", "")
                self.rank_label.setText(str(rank) if rank else "N/A")

            if hasattr(self, "distance_label") and self.distance_label:
                distance = self.item_data.get("distance", "")
                if distance:
                    self.distance_label.setText(f"{distance:.4f}")
                else:
                    self.distance_label.setText("N/A")

        # Document
        document = self.item_data.get("document", "")
        self.document_display.setPlainText(str(document) if document else "(No document)")

        # Metadata
        metadata = self.item_data.get("metadata", {})
        if metadata:
            metadata_text = json.dumps(metadata, indent=2)
            self.metadata_display.setPlainText(metadata_text)
        else:
            self.metadata_display.setPlainText("(No metadata)")

        # Vector embedding
        if self.vector_display:
            embedding = self.item_data.get("embedding")
            # Safe check: avoid "ambiguous truth value" error with numpy arrays
            if has_embedding(embedding):
                try:
                    # Handle different vector types
                    vector_list = (
                        embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
                    )
                    dimension = len(vector_list)

                    # Show first few and last few dimensions
                    if dimension > 10:
                        preview = [*vector_list[:5], "...", *vector_list[-5:]]
                        preview_text = f"Dimension: {dimension}\n{preview}"
                    else:
                        preview_text = f"Dimension: {dimension}\n{vector_list}"

                    self.vector_display.setPlainText(preview_text)
                except Exception as e:
                    self.vector_display.setPlainText(f"(Error displaying vector: {e})")
            else:
                self.vector_display.setPlainText("(No embedding)")
