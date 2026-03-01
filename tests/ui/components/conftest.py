import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture
def qapp():
    """Ensure a QApplication exists for Qt widget/thread tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
