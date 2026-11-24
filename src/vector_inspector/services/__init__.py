"""Services for embeddings, visualization, and data processing.

Names are resolved lazily (PEP 562) so importing the
``vector_inspector.services`` package does not pull in optional
dependencies such as the Qt GUI stack. For example, importing
``vector_inspector.services.telemetry_service`` (needed by the
provider layer and the headless MCP server) no longer imports
``task_runner``, which requires PySide6. Accessing a name still
imports its real module on first use, so
``from vector_inspector.services import TaskRunner`` behaves exactly
as before when PySide6 is installed.
"""

from typing import Any

__all__ = [
    "ClusterRunner",
    "CollectionLoader",
    "MetadataLoader",
    "ProviderManager",
    "SearchRunner",
    "TaskRunner",
    "ThreadedTaskRunner",
    "VectorLoader",
]

_LAZY_IMPORTS = {
    "ClusterRunner": "vector_inspector.services.cluster_runner",
    "CollectionLoader": "vector_inspector.services.data_loaders",
    "MetadataLoader": "vector_inspector.services.data_loaders",
    "VectorLoader": "vector_inspector.services.data_loaders",
    "ProviderManager": "vector_inspector.services.provider_manager",
    "SearchRunner": "vector_inspector.services.search_runner",
    "TaskRunner": "vector_inspector.services.task_runner",
    "ThreadedTaskRunner": "vector_inspector.services.task_runner",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
