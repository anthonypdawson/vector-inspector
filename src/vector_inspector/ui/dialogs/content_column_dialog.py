"""Dialog for selecting content column from schema."""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QButtonGroup,
    QGroupBox,
    QScrollArea,
    QWidget,
)
from PySide6.QtCore import Qt


class ContentColumnDialog(QDialog):
    """Dialog for selecting which column contains the document content."""

    def __init__(
        self,
        collection_name: str,
        schema: dict[str, str],
        detected_column: str,
        parent=None,
    ):
        super().__init__(parent)
        self.collection_name = collection_name
        self.schema = schema
        self.detected_column = detected_column
        self.selected_column = detected_column

        self.setWindowTitle("Select Content Column")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self._setup_ui()

    def _setup_ui(self):
        """Setup dialog UI."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("<h3>Select Content Column</h3>")
        layout.addWidget(header)

        info = QLabel(
            f"<b>Collection:</b> {self.collection_name}<br>"
            f"<b>Auto-detected:</b> <code>{self.detected_column}</code><br><br>"
            "Select the column that contains the document text/content:"
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        # Scroll area for columns
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(5)

        # Radio button group
        self.button_group = QButtonGroup(self)

        # Reserved columns that are NOT content
        reserved = {"id", "embedding", "vector", "metadata", "_distance"}

        # Create radio buttons for each column
        for i, (col_name, col_type) in enumerate(sorted(self.schema.items())):
            if col_name in reserved:
                continue  # Skip obviously non-content columns

            # Create group box for this column
            group = QGroupBox()
            group_layout = QVBoxLayout()

            # Radio button
            radio = QRadioButton(col_name)
            radio.setProperty("column_name", col_name)
            self.button_group.addButton(radio, i)
            group_layout.addWidget(radio)

            # Column type info
            type_label = QLabel(f"<i>Type:</i> <code>{col_type}</code>")
            type_label.setStyleSheet("color: gray; margin-left: 25px; font-size: 11px;")
            group_layout.addWidget(type_label)

            # Mark if this is the detected column
            if col_name == self.detected_column:
                detected_label = QLabel("✓ Auto-detected as content column")
                detected_label.setStyleSheet("color: green; margin-left: 25px; font-size: 11px;")
                group_layout.addWidget(detected_label)
                radio.setChecked(True)

            group.setLayout(group_layout)
            scroll_layout.addWidget(group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Note
        note = QLabel(
            "💡 <b>Tip:</b> The content column contains the actual text/document data "
            "that was embedded. It's typically named 'document', 'text', or 'content'."
        )
        note.setWordWrap(True)
        note.setStyleSheet("background-color: #2a2a2a; padding: 10px; border-radius: 4px; font-size: 11px;")
        layout.addWidget(note)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._on_save)
        save_btn.setDefault(True)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _on_save(self):
        """Save the selected column."""
        # Get the checked radio button
        checked_button = self.button_group.checkedButton()
        if checked_button:
            self.selected_column = checked_button.property("column_name")
        self.accept()

    def get_selected_column(self) -> Optional[str]:
        """Get the user's selected content column."""
        return self.selected_column
