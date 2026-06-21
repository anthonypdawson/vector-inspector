import logging

import pytest


@pytest.fixture(autouse=True)
def suppress_pymilvus_logging():
    """Silence pymilvus internal RPC error tracebacks.

    pymilvus logs full stack traces at ERROR level for expected error conditions
    (e.g. describing a nonexistent collection, drop_collection on Windows). These
    are handled gracefully by MilvusConnection, but the raw tracebacks flood the
    terminal and make test output very hard to parse — particularly when running
    via an IDE or AI assistant that reads terminal I/O.
    """
    loggers_to_silence = [
        "pymilvus",
        "pymilvus.client",
        "pymilvus.decorators",
        "pymilvus.milvus_client",
    ]
    previous_levels = {}
    for name in loggers_to_silence:
        logger = logging.getLogger(name)
        previous_levels[name] = logger.level
        logger.setLevel(logging.CRITICAL)

    yield

    for name, level in previous_levels.items():
        logging.getLogger(name).setLevel(level)
