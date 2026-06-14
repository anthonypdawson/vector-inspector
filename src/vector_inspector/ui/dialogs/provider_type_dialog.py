"""Dialog for selecting embedding provider type (Step 1 of model selection)."""

from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QRadioButton, QButtonGroup, QGroupBox,
    QScrollArea, QWidget
)
from PySide6.QtCore import Qt

from vector_inspector.core.model_registry import get_model_registry


class ProviderTypeDialog(QDialog):
    """Dialog for selecting the provider/type category before choosing specific model."""
    
    # Provider categories with display info
    PROVIDER_CATEGORIES = [
        {
            "id": "sentence-transformer",
            "name": "🤗 Sentence Transformers",
            "description": "Local models from HuggingFace\nNo API key required, runs on your machine",
            "filter_type": "sentence-transformer",
            "icon": "📦"
        },
        {
            "id": "clip",
            "name": "🖼️ CLIP Models",
            "description": "Multimodal embeddings (text + images)\nLocal models, no API key required",
            "filter_type": "clip",
            "icon": "🎨"
        },
        {
            "id": "ollama",
            "name": "🦙 Ollama",
            "description": "Local models via Ollama server\nNo API key required, requires Ollama running",
            "filter_type": "ollama",
            "icon": "💻"
        },
        {
            "id": "openai",
            "name": "☁️ OpenAI API",
            "description": "Cloud-based embeddings\nRequires OpenAI API key",
            "filter_type": "openai",
            "icon": "🔑"
        },
        {
            "id": "cohere",
            "name": "☁️ Cohere API",
            "description": "Cloud-based embeddings\nRequires Cohere API key",
            "filter_type": "cohere",
            "icon": "🔑"
        },
        {
            "id": "vertex-ai",
            "name": "☁️ Google Vertex AI",
            "description": "Cloud-based embeddings\nRequires Google Cloud credentials",
            "filter_type": "vertex-ai",
            "icon": "🔑"
        },
        {
            "id": "voyage",
            "name": "☁️ Voyage AI",
            "description": "Cloud-based embeddings\nRequires Voyage API key",
            "filter_type": "voyage",
            "icon": "🔑"
        },
        {
            "id": "custom",
            "name": "✏️ Custom Model",
            "description": "Enter your own model name\nFor models not in the registry",
            "filter_type": None,  # Special case
            "icon": "⚙️"
        }
    ]
    
    def __init__(self, collection_name: str, vector_dimension: int, parent=None):
        super().__init__(parent)
        self.collection_name = collection_name
        self.vector_dimension = vector_dimension
        self.selected_type = None
        
        self.setWindowTitle("Select Embedding Provider Type")
        self.setMinimumWidth(550)
        self.setMinimumHeight(500)
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup dialog UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel(f"<h3>Select Provider Type</h3>")
        layout.addWidget(header)
        
        info = QLabel(f"<b>Collection:</b> {self.collection_name}<br>"
                     f"<b>Vector Dimension:</b> {self.vector_dimension}")
        layout.addWidget(info)
        
        layout.addWidget(QLabel("<i>Choose the type of embedding provider to use:</i>"))
        
        # Scroll area for provider options
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)
        
        # Radio button group
        self.button_group = QButtonGroup(self)
        
        # Get registry to count models
        registry = get_model_registry()
        
        # Create radio buttons for each provider type
        for i, category in enumerate(self.PROVIDER_CATEGORIES):
            provider_id = category["id"]
            
            # Count available models for this type + dimension
            if provider_id == "custom":
                count_text = "Enter manually"
            else:
                filter_type = category["filter_type"]
                models = registry.get_models_by_dimension(self.vector_dimension)
                matching = [m for m in models if m.type == filter_type]
                count = len(matching)
                
                if count == 0:
                    continue  # Skip categories with no models for this dimension
                
                count_text = f"{count} model{'s' if count != 1 else ''} available"
            
            # Create group box for this option
            group = QGroupBox()
            group_layout = QVBoxLayout()
            
            # Radio button
            radio = QRadioButton(category["name"])
            radio.setProperty("provider_id", provider_id)
            self.button_group.addButton(radio, i)
            group_layout.addWidget(radio)
            
            # Description
            desc_label = QLabel(category["description"])
            desc_label.setStyleSheet("color: gray; margin-left: 25px;")
            desc_label.setWordWrap(True)
            group_layout.addWidget(desc_label)
            
            # Count
            count_label = QLabel(f"<b>{count_text}</b>")
            count_label.setStyleSheet("margin-left: 25px; color: #0066cc;")
            group_layout.addWidget(count_label)
            
            group.setLayout(group_layout)
            scroll_layout.addWidget(group)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        self.next_btn = QPushButton("Next →")
        self.next_btn.clicked.connect(self._on_next)
        self.next_btn.setEnabled(False)
        self.next_btn.setDefault(True)
        
        # Enable Next when selection is made
        self.button_group.buttonClicked.connect(lambda: self.next_btn.setEnabled(True))
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(self.next_btn)
        
        layout.addLayout(button_layout)
    
    def _on_next(self):
        """Handle Next button click."""
        selected_button = self.button_group.checkedButton()
        if selected_button:
            self.selected_type = selected_button.property("provider_id")
            self.accept()
    
    def get_selected_type(self) -> Optional[str]:
        """Get the selected provider type ID.
        
        Returns:
            Provider type ID or None if cancelled
        """
        return self.selected_type
