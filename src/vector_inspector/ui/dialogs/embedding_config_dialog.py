"""Dialog for configuring embedding models for collections."""

from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QPushButton, QGroupBox, QTextEdit,
    QMessageBox
)
from PySide6.QtCore import Qt

from vector_inspector.core.embedding_utils import get_available_models_for_dimension, DIMENSION_TO_MODEL


class EmbeddingConfigDialog(QDialog):
    """Dialog for selecting embedding model for a collection."""
    
    def __init__(self, collection_name: str, vector_dimension: int, 
                 current_model: Optional[str] = None, 
                 current_type: Optional[str] = None,
                 parent=None):
        super().__init__(parent)
        self.collection_name = collection_name
        self.vector_dimension = vector_dimension
        self.current_model = current_model
        self.current_type = current_type
        self.selected_model = None
        self.selected_type = None
        
        self.setWindowTitle(f"Configure Embedding Model - {collection_name}")
        self.setMinimumWidth(500)
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup dialog UI."""
        layout = QVBoxLayout(self)
        
        # Info section
        info_group = QGroupBox("Collection Information")
        info_layout = QVBoxLayout()
        
        info_layout.addWidget(QLabel(f"<b>Collection:</b> {self.collection_name}"))
        info_layout.addWidget(QLabel(f"<b>Vector Dimension:</b> {self.vector_dimension}"))
        
        if self.current_model:
            info_layout.addWidget(QLabel(f"<b>Current Model:</b> {self.current_model} ({self.current_type})"))
        else:
            warning = QLabel("⚠️ No embedding model configured - using automatic detection")
            warning.setStyleSheet("color: orange;")
            info_layout.addWidget(warning)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Model selection section
        model_group = QGroupBox("Embedding Model Selection")
        model_layout = QVBoxLayout()
        
        # Get available models for this dimension
        available_models = get_available_models_for_dimension(self.vector_dimension)
        
        if available_models:
            model_layout.addWidget(QLabel(f"Available models for {self.vector_dimension}-dimensional vectors:"))
            
            self.model_combo = QComboBox()
            for model_name, model_type, description in available_models:
                display_text = f"{model_name} ({model_type}) - {description}"
                self.model_combo.addItem(display_text, (model_name, model_type))
            
            # Set current selection if it matches
            if self.current_model and self.current_type:
                for i in range(self.model_combo.count()):
                    model_name, model_type = self.model_combo.itemData(i)
                    if model_name == self.current_model and model_type == self.current_type:
                        self.model_combo.setCurrentIndex(i)
                        break
            
            model_layout.addWidget(self.model_combo)
            
            # Description area
            desc_label = QLabel("<b>About the selected model:</b>")
            model_layout.addWidget(desc_label)
            
            self.description_text = QTextEdit()
            self.description_text.setReadOnly(True)
            self.description_text.setMaximumHeight(100)
            self.description_text.setStyleSheet("background-color: #f5f5f5; border: 1px solid #ccc; color: #000000;")
            model_layout.addWidget(self.description_text)
            
            # Update description when selection changes
            self.model_combo.currentIndexChanged.connect(self._update_description)
            self._update_description()
            
        else:
            # No known models for this dimension
            warning = QLabel(f"⚠️ No pre-configured models available for {self.vector_dimension} dimensions.")
            warning.setWordWrap(True)
            model_layout.addWidget(warning)
            
            # Show all available dimensions
            dims_text = "Available dimensions: " + ", ".join(str(d) for d in sorted(DIMENSION_TO_MODEL.keys()))
            model_layout.addWidget(QLabel(dims_text))
            
            self.model_combo = None
        
        model_group.setLayout(model_layout)
        layout.addWidget(model_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_btn = QPushButton("Save Configuration")
        self.save_btn.clicked.connect(self.accept)
        self.save_btn.setEnabled(available_models and len(available_models) > 0)
        
        self.clear_btn = QPushButton("Clear Configuration")
        self.clear_btn.clicked.connect(self._clear_config)
        self.clear_btn.setEnabled(self.current_model is not None)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _update_description(self):
        """Update the description text based on selected model."""
        if not self.model_combo:
            return
        
        model_name, model_type = self.model_combo.currentData()
        
        descriptions = {
            "sentence-transformer": (
                "Sentence-Transformers are text-only embedding models optimized for semantic similarity. "
                "They work well for text search, clustering, and classification tasks."
            ),
            "clip": (
                "CLIP (Contrastive Language-Image Pre-training) is a multi-modal model that can embed both "
                "text and images into the same vector space. This allows text queries to find semantically "
                "similar images, and vice versa. Perfect for image search with text descriptions."
            )
        }
        
        desc = descriptions.get(model_type, "Embedding model for vector similarity search.")
        self.description_text.setPlainText(
            f"Model: {model_name}\n"
            f"Type: {model_type}\n"
            f"Dimension: {self.vector_dimension}\n\n"
            f"{desc}"
        )
    
    def _clear_config(self):
        """Clear the embedding model configuration."""
        reply = QMessageBox.question(
            self,
            "Clear Configuration",
            "This will remove the custom embedding model configuration and use automatic detection. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.selected_model = None
            self.selected_type = None
            self.done(2)  # Custom code for "clear"
    
    def get_selection(self) -> Optional[Tuple[str, str]]:
        """Get the selected model and type."""
        if not self.model_combo:
            return None
        
        model_name, model_type = self.model_combo.currentData()
        return (model_name, model_type)
