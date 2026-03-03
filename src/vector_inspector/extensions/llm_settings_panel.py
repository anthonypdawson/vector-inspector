"""Free-tier LLM provider status panel for the Settings dialog.

This panel is registered automatically via ``settings_panel_hook`` when
``vector_inspector.extensions`` is imported.  It shows the currently
configured LLM provider and a live availability check button.

Vector Studio injects the full configuration section (provider dropdown,
model picker, etc.) alongside this panel via its own settings hook handler.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from vector_inspector.extensions import settings_panel_hook


class _StatusCheckThread(QThread):
    """Background thread to probe LLM provider availability."""

    result_ready = Signal(bool, str, str)  # (available, provider_name, model_name)

    def __init__(self, settings, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings

    def run(self) -> None:
        try:
            from vector_inspector.core.llm_providers import LLMProviderFactory

            provider = LLMProviderFactory.create_from_settings(self._settings)
            if provider is None:
                self.result_ready.emit(False, "none", "none")
                return
            available = provider.is_available()
            self.result_ready.emit(
                available,
                provider.get_provider_name(),
                provider.get_model_name() if available else "—",
            )
        except Exception as exc:
            self.result_ready.emit(False, "error", str(exc))


def _add_llm_status_section(parent_layout, settings_service, dialog=None) -> None:
    """Hook handler: adds the LLM Provider Status group box to the settings dialog."""
    group = QGroupBox("LLM Provider")
    group.setObjectName("llm_status_group")
    layout = QVBoxLayout()

    configured = settings_service.get_llm_provider()
    config_row = QHBoxLayout()
    config_row.addWidget(QLabel("Configured:"))
    config_label = QLabel(f"<b>{configured}</b>")
    config_label.setObjectName("llm_configured_label")
    config_row.addWidget(config_label)
    config_row.addStretch()
    layout.addLayout(config_row)

    status_row = QHBoxLayout()
    status_row.addWidget(QLabel("Status:"))
    status_label = QLabel("Not checked")
    status_label.setObjectName("llm_status_label")
    status_row.addWidget(status_label)
    status_row.addStretch()

    check_btn = QPushButton("Check Availability")
    check_btn.setObjectName("llm_check_btn")
    status_row.addWidget(check_btn)
    layout.addLayout(status_row)

    # Disabled "Configure…" stub — Vector Studio enables and replaces this.
    configure_btn = QPushButton("Configure LLM…")
    configure_btn.setObjectName("llm_configure_btn")
    configure_btn.setEnabled(False)
    configure_btn.setToolTip("Requires Vector Studio")
    layout.addWidget(configure_btn)

    group.setLayout(layout)
    parent_layout.addWidget(group)

    # Keep thread alive by attaching to the group widget
    _thread_holder: list[_StatusCheckThread] = []

    def _on_check_clicked() -> None:
        check_btn.setEnabled(False)
        status_label.setText("Checking…")
        thread = _StatusCheckThread(settings_service, parent=group)

        def _on_result(available: bool, provider_name: str, model_name: str) -> None:
            if available:
                status_label.setText(f"<font color='green'>Available — {provider_name} ({model_name})</font>")
            else:
                status_label.setText("<font color='red'>Not available</font>")
            check_btn.setEnabled(True)
            if thread in _thread_holder:
                _thread_holder.remove(thread)

        thread.result_ready.connect(_on_result)
        _thread_holder.append(thread)
        thread.start()

    check_btn.clicked.connect(_on_check_clicked)


settings_panel_hook.register(_add_llm_status_section)
