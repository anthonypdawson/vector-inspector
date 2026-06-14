"""Dialog for configuring embedding models for collections (Step 2: Model Selection)."""

from typing import Optional, Tuple
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QGroupBox,
    QTextEdit,
    QMessageBox,
    QLineEdit,
    QFormLayout,
)
from PySide6.QtCore import Qt, QThread, Signal

from vector_inspector.core.embedding_utils import get_available_models_for_dimension
from vector_inspector.core.model_registry import get_model_registry


class EmbeddingConfigDialog(QDialog):
    """Dialog for selecting embedding model for a collection."""

    def __init__(
        self,
        collection_name: str,
        vector_dimension: int,
        provider_type: Optional[str] = None,
        current_model: Optional[str] = None,
        current_type: Optional[str] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.collection_name = collection_name
        self.vector_dimension = vector_dimension
        self.provider_type = provider_type  # Filter by this type
        self.current_model = current_model
        self.current_type = current_type
        self.selected_model = None
        self.selected_type = None

        # Determine title based on provider type
        if provider_type == "custom":
            title = "Enter Custom Model"
        elif provider_type:
            type_names = {
                "sentence-transformer": "Sentence Transformers",
                "clip": "CLIP Models",
                "ollama": "Ollama",
                "openai": "OpenAI API",
                "cohere": "Cohere API",
                "vertex-ai": "Google Vertex AI",
                "voyage": "Voyage AI",
            }
            type_name = type_names.get(provider_type, provider_type.title())
            title = f"Select Model: {type_name}"
        else:
            title = f"Configure Embedding Model - {collection_name}"

        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self._setup_ui()

    def _setup_ui(self):
        """Setup dialog UI."""
        layout = QVBoxLayout(self)

        # Handle custom model entry case (including Ollama)
        if self.provider_type in ("custom", "ollama"):
            self._setup_custom_ui(layout)
            return

        # Info section
        info_group = QGroupBox("Collection Information")
        info_layout = QVBoxLayout()

        info_layout.addWidget(QLabel(f"<b>Collection:</b> {self.collection_name}"))
        info_layout.addWidget(QLabel(f"<b>Vector Dimension:</b> {self.vector_dimension}"))

        if self.current_model:
            info_layout.addWidget(
                QLabel(f"<b>Current Model:</b> {self.current_model} ({self.current_type})")
            )
        else:
            warning = QLabel("⚠️ No embedding model configured - using automatic detection")
            warning.setStyleSheet("color: orange;")
            info_layout.addWidget(warning)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Model selection section
        model_group = QGroupBox("Embedding Model Selection")
        model_layout = QVBoxLayout()

        # Get available models for this dimension, filtered by provider type
        if self.provider_type:
            registry = get_model_registry()
            registry_models = registry.get_models_by_dimension(self.vector_dimension)
            filtered_models = [m for m in registry_models if m.type == self.provider_type]
            available_models = [(m.name, m.type, m.description) for m in filtered_models]

            # Add custom models from settings
            try:
                from vector_inspector.services.settings_service import SettingsService

                settings = SettingsService()
                custom_models = settings.get_custom_embedding_models(self.vector_dimension)
                for model in custom_models:
                    if model["type"] == self.provider_type:
                        available_models.append(
                            (model["name"], model["type"], f"{model['description']} (custom)")
                        )
            except Exception:
                pass
        else:
            available_models = get_available_models_for_dimension(self.vector_dimension)

        if available_models:
            model_layout.addWidget(
                QLabel(f"Available models for {self.vector_dimension}-dimensional vectors:")
            )

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
            self.description_text.setStyleSheet(
                "background-color: #f5f5f5; border: 1px solid #ccc; color: #000000;"
            )
            model_layout.addWidget(self.description_text)

            # Update description when selection changes
            self.model_combo.currentIndexChanged.connect(self._update_description)
            self._update_description()

        else:
            # No models for this type + dimension
            type_name = self.provider_type or "any type"
            warning = QLabel(
                f"⚠️ No models of type '{type_name}' available for {self.vector_dimension} dimensions."
            )
            warning.setWordWrap(True)
            model_layout.addWidget(warning)

            registry = get_model_registry()
            all_dims = registry.get_all_dimensions()
            dims_text = "Available dimensions: " + ", ".join(str(d) for d in sorted(all_dims))
            model_layout.addWidget(QLabel(dims_text))

            self.model_combo = None

        model_group.setLayout(model_layout)
        layout.addWidget(model_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_btn = QPushButton("Save Configuration")
        self.save_btn.clicked.connect(self._on_save)
        # Always enabled - user can choose from combo OR enter custom
        self.save_btn.setEnabled(True)

        self.clear_btn = QPushButton("Clear Configuration")
        self.clear_btn.clicked.connect(self._clear_config)
        self.clear_btn.setEnabled(self.current_model is not None)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def _setup_custom_ui(self, layout):
        """Setup UI for custom model entry."""
        # Info section
        info_group = QGroupBox("Collection Information")
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel(f"<b>Collection:</b> {self.collection_name}"))
        info_layout.addWidget(QLabel(f"<b>Vector Dimension:</b> {self.vector_dimension}"))
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Custom model entry section
        custom_group = QGroupBox("Enter Custom Model Details")
        custom_layout = QFormLayout()

        # For Ollama, use a combo box that fetches available models
        if self.provider_type == "ollama":
            self.custom_name_combo = QComboBox()
            self.custom_name_combo.setEditable(True)
            self.custom_name_combo.setPlaceholderText("Loading models...")
            self.custom_name_combo.lineEdit().setPlaceholderText("e.g., nomic-embed-text")
            custom_layout.addRow("Model Name:", self.custom_name_combo)
            self.custom_name_input = None  # Not used for Ollama

            # Fetch Ollama models in background
            self._fetch_ollama_models()
        else:
            self.custom_name_input = QLineEdit()
            self.custom_name_input.setPlaceholderText("e.g., sentence-transformers/all-mpnet-base-v2")
            custom_layout.addRow("Model Name:", self.custom_name_input)
            self.custom_name_combo = None  # Not used for non-Ollama

        self.custom_type_combo = QComboBox()
        self.custom_type_combo.addItems(
            ["sentence-transformer", "clip", "ollama", "openai", "cohere", "vertex-ai", "voyage", "custom"]
        )
        # Pre-select the provider type if specified
        if self.provider_type and self.provider_type != "custom":
            index = self.custom_type_combo.findText(self.provider_type)
            if index >= 0:
                self.custom_type_combo.setCurrentIndex(index)
        custom_layout.addRow("Model Type:", self.custom_type_combo)

        self.custom_desc_input = QLineEdit()
        self.custom_desc_input.setPlaceholderText("Brief description (optional)")
        custom_layout.addRow("Description:", self.custom_desc_input)

        custom_note = QLabel(
            "💡 Custom models will be saved and available for future use with this dimension."
        )
        custom_note.setWordWrap(True)
        custom_note.setStyleSheet("color: #666; font-size: 10px; padding: 4px;")
        custom_layout.addRow(custom_note)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        # Buttons for custom entry
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_custom_model)
        save_btn.setDefault(True)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

        # No combo or description for custom mode
        self.model_combo = None

    def _save_custom_model(self):
        """Save custom model entry."""
        # Get model name from appropriate input (combo for Ollama, input for others)
        if self.provider_type == "ollama" and self.custom_name_combo:
            custom_name = self.custom_name_combo.currentText().strip()
        elif self.custom_name_input:
            custom_name = self.custom_name_input.text().strip()
        else:
            custom_name = ""

        custom_desc = self.custom_desc_input.text().strip()
        custom_type = self.custom_type_combo.currentText()

        if not custom_name:
            QMessageBox.warning(self, "Invalid Input", "Please enter a model name.")
            return

        # Save custom model to registry
        from vector_inspector.services.settings_service import SettingsService

        settings = SettingsService()

        settings.add_custom_embedding_model(
            model_name=custom_name,
            dimension=self.vector_dimension,
            model_type=custom_type,
            description=custom_desc if custom_desc else f"Custom {custom_type} model",
        )

        # Set selection to custom model
        self.selected_model = custom_name
        self.selected_type = custom_type
        self.accept()

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
            ),
        }

        desc = descriptions.get(model_type, "Embedding model for vector similarity search.")
        self.description_text.setPlainText(
            f"Model: {model_name}\nType: {model_type}\nDimension: {self.vector_dimension}\n\n{desc}"
        )

    def _on_save(self):
        """Handle save button click."""
        if self.model_combo and self.model_combo.currentData():
            # Use combo selection
            model_name, model_type = self.model_combo.currentData()
            self.selected_model = model_name
            self.selected_type = model_type
        else:
            QMessageBox.warning(self, "No Selection", "Please select a model from the list.")
            return

        self.accept()

    def _clear_config(self):
        """Clear the embedding model configuration."""
        reply = QMessageBox.question(
            self,
            "Clear Configuration",
            "This will remove the custom embedding model configuration and use automatic detection. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.selected_model = None
            self.selected_type = None
            self.done(2)  # Custom code for "clear"

    def get_selection(self) -> Optional[Tuple[str, str]]:
        """Get the selected model and type (from either combo or custom entry)."""
        if self.selected_model and self.selected_type:
            return (self.selected_model, self.selected_type)
        return None

    def _fetch_ollama_models(self):
        """Fetch available Ollama models in background."""
        self._ollama_thread = _OllamaModelFetchThread(self)
        self._ollama_thread.models_ready.connect(self._on_ollama_models_loaded)
        self._ollama_thread.error.connect(self._on_ollama_models_error)
        self._ollama_thread.start()

    def _on_ollama_models_loaded(self, models: list[str]):
        """Handle Ollama models loaded."""
        if self.custom_name_combo:
            self.custom_name_combo.clear()
            if models:
                self.custom_name_combo.addItems(models)
                self.custom_name_combo.setPlaceholderText("Select or enter model name")
            else:
                self.custom_name_combo.setPlaceholderText("No models found - enter manually")
            # Allow manual entry even if models were found
            self.custom_name_combo.setEditable(True)

    def _on_ollama_models_error(self, error: str):
        """Handle error fetching Ollama models."""
        if self.custom_name_combo:
            self.custom_name_combo.setPlaceholderText("Ollama unavailable - enter manually")
            self.custom_name_combo.setEditable(True)


class _OllamaModelFetchThread(QThread):
    """Background thread to fetch available Ollama models."""

    models_ready = Signal(list)  # list[str]
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        """Fetch models from Ollama API."""
        try:
            import json
            import urllib.request

            url = "http://localhost:11434/api/tags"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})

            with urllib.request.urlopen(req, timeout=2) as response:
                data = json.loads(response.read().decode("utf-8"))
                models = [m["name"] for m in data.get("models", [])]
                self.models_ready.emit(models)
        except Exception as e:
            self.error.emit(str(e))
