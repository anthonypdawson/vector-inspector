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
        current_column: str,
        parent=None,
        auto_detected_column: Optional[str] = None,
    ):
        super().__init__(parent)
        self.collection_name = collection_name
        self.schema = schema
        self.current_column = current_column
        # If auto_detected not provided, assume current is auto-detected
        self.auto_detected_column = auto_detected_column or current_column
        self.selected_column = current_column

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

        # Show both auto-detected and currently selected
        is_override = self.current_column != self.auto_detected_column
        info_lines = [
            f"<b>Collection:</b> {self.collection_name}",
            f"<b>VI recommends:</b> <code>{self.auto_detected_column}</code> (auto-detected)",
        ]
        if is_override:
            info_lines.append(f"<b>Currently using:</b> <code>{self.current_column}</code> (your choice)")
        info_lines.append("")
        info_lines.append("Select the column that contains the document text/content:")

        info = QLabel("<br>".join(info_lines))
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

            # Mark special columns
            if col_name == self.auto_detected_column:
                detected_label = QLabel("✓ VI recommends this column (auto-detected)")
                detected_label.setStyleSheet("color: #4CAF50; margin-left: 25px; font-size: 11px;")
                group_layout.addWidget(detected_label)

            if col_name == self.current_column:
                current_label = QLabel("● Currently selected")
                current_label.setStyleSheet("color: #2196F3; margin-left: 25px; font-size: 11px; font-weight: bold;")
                group_layout.addWidget(current_label)
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
