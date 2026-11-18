"""MCP server package for Vector Inspector.

Exposes the provider layer (``vector_inspector.core``) as MCP tools
over stdio. This package must import without PySide6: it only touches
the Qt-free provider layer, never ``core/connection_manager.py`` or
any ``ui`` module.
"""

__all__ = ["create_server"]


def create_server(*args, **kwargs):  # lazy import, keeps `import vector_inspector.mcp` cheap
    from vector_inspector.mcp.server import create_server as _create_server

    return _create_server(*args, **kwargs)
