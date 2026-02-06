"""Controller for managing connection lifecycle and threading."""

from typing import Optional

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QMessageBox, QWidget

from vector_inspector.core.connection_manager import ConnectionManager, ConnectionState
from vector_inspector.core.connections.base_connection import VectorDBConnection
from vector_inspector.core.provider_factory import ProviderFactory
from vector_inspector.services.profile_service import ProfileService
from vector_inspector.ui.components.loading_dialog import LoadingDialog


class ConnectionThread(QThread):
    """Background thread for connecting to database."""

    finished = Signal(bool, list, str)  # success, collections, error_message

    def __init__(self, connection: VectorDBConnection):
        super().__init__()
        self.connection = connection

    def run(self):
        """Connect to database and get collections."""
        try:
            success = self.connection.connect()
            if success:
                collections = self.connection.list_collections()
                self.finished.emit(True, collections, "")
            else:
                self.finished.emit(False, [], "Connection failed")
        except Exception as e:
            self.finished.emit(False, [], str(e))


class ConnectionController(QObject):
    """Controller for managing connection operations and lifecycle.

    This handles:
    - Creating connections from profiles
    - Starting connection threads
    - Handling connection results
    - Managing loading dialogs
    - Emitting signals for UI updates
    """

    connection_completed = Signal(
        str, bool, list, str
    )  # connection_id, success, collections, error

    def __init__(
        self,
        connection_manager: ConnectionManager,
        profile_service: ProfileService,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.connection_manager = connection_manager
        self.profile_service = profile_service
        self.parent_widget = parent

        # State
        self._connection_threads: dict[str, ConnectionThread] = {}
        self.loading_dialog = LoadingDialog("Loading...", parent)

    def connect_to_profile(self, profile_id: str) -> bool:
        """Connect to a profile.

        Args:
            profile_id: ID of the profile to connect to

        Returns:
            True if connection initiated successfully, False otherwise
        """
        profile_data = self.profile_service.get_profile_with_credentials(profile_id)
        if not profile_data:
            QMessageBox.warning(self.parent_widget, "Error", "Profile not found.")
            return False

        # Check connection limit
        if self.connection_manager.get_connection_count() >= ConnectionManager.MAX_CONNECTIONS:
            QMessageBox.warning(
                self.parent_widget,
                "Connection Limit",
                f"Maximum number of connections ({ConnectionManager.MAX_CONNECTIONS}) reached. "
                "Please close a connection first.",
            )
            return False

        # Create connection
        provider = profile_data["provider"]
        config = profile_data["config"]
        credentials = profile_data.get("credentials", {})

        try:
            # Create connection object using factory
            connection = ProviderFactory.create(provider, config, credentials)

            # Register with connection manager, using profile_id as connection_id for persistence
            connection_id = self.connection_manager.create_connection(
                name=profile_data["name"],
                provider=provider,
                connection=connection,
                config=config,
                connection_id=profile_data["id"],
            )

            # Update state to connecting
            self.connection_manager.update_connection_state(
                connection_id, ConnectionState.CONNECTING
            )

            # Connect in background thread
            thread = ConnectionThread(connection)
            thread.finished.connect(
                lambda success, collections, error: self._on_connection_finished(
                    connection_id, success, collections, error
                )
            )
            self._connection_threads[connection_id] = thread
            thread.start()

            # Show loading dialog
            self.loading_dialog.show_loading(f"Connecting to {profile_data['name']}...")
            return True

        except Exception as e:
            QMessageBox.critical(
                self.parent_widget, "Connection Error", f"Failed to create connection: {e}"
            )
            return False

    def _on_connection_finished(
        self, connection_id: str, success: bool, collections: list, error: str
    ):
        """Handle connection thread completion."""
        self.loading_dialog.hide_loading()

        # Clean up thread
        thread = self._connection_threads.pop(connection_id, None)
        if thread:
            thread.wait()  # Wait for thread to fully finish
            thread.deleteLater()

        if success:
            # Update state to connected
            self.connection_manager.update_connection_state(
                connection_id, ConnectionState.CONNECTED
            )

            # Mark connection as opened first (will show in UI)
            self.connection_manager.mark_connection_opened(connection_id)

            # Then update collections (UI item now exists to receive them)
            self.connection_manager.update_collections(connection_id, collections)
        else:
            # Update state to error
            self.connection_manager.update_connection_state(
                connection_id, ConnectionState.ERROR, error
            )

            QMessageBox.warning(
                self.parent_widget, "Connection Failed", f"Failed to connect: {error}"
            )

            # Remove the failed connection
            self.connection_manager.close_connection(connection_id)

        # Emit signal for UI updates
        self.connection_completed.emit(connection_id, success, collections, error)

    def cleanup(self):
        """Clean up connection threads on shutdown."""
        for thread in list(self._connection_threads.values()):
            if thread.isRunning():
                thread.quit()
                thread.wait(1000)  # Wait up to 1 second
