"""Background threads for metadata view operations."""

from typing import Any

from PySide6.QtCore import QThread, Signal


class DataLoadThread(QThread):
    """Background thread for loading collection data."""

    finished = Signal(dict)
    error = Signal(str)
    connection: Any
    collection: Any
    page_size: int
    offset: int
    server_filter: Any

    def __init__(self, connection, collection, page_size, offset, server_filter):
        super().__init__()
        self.connection = connection
        self.collection = collection
        self.page_size = page_size
        self.offset = offset
        self.server_filter = server_filter

    def run(self):
        """Load data from database."""
        try:
            data = self.connection.get_all_items(
                self.collection, limit=self.page_size, offset=self.offset, where=self.server_filter
            )
            if data:
                self.finished.emit(data)
            else:
                self.error.emit("Failed to load data")
        except Exception as e:
            self.error.emit(str(e))
