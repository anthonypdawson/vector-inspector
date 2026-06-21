"""Connection managers for vector databases.

IMPORTANT: Connection classes are imported lazily to avoid import errors
when database providers are not installed. Use get_connection_class() to
retrieve a connection class safely.
"""

from typing import TYPE_CHECKING, Literal, overload

from .base_connection import VectorDBConnection

if TYPE_CHECKING:
    from typing import Type

    from .chroma_connection import ChromaDBConnection
    from .lancedb_connection import LanceDBConnection
    from .milvus_connection import MilvusConnection
    from .pgvector_connection import PgVectorConnection
    from .pinecone_connection import PineconeConnection
    from .qdrant_connection import QdrantConnection
    from .weaviate_connection import WeaviateConnection

__all__ = [
    "VectorDBConnection",
    "get_connection_class",
]


@overload
def get_connection_class(provider: Literal["chromadb"]) -> "type[ChromaDBConnection]": ...


@overload
def get_connection_class(provider: Literal["qdrant"]) -> "type[QdrantConnection]": ...


@overload
def get_connection_class(provider: Literal["pinecone"]) -> "type[PineconeConnection]": ...


@overload
def get_connection_class(provider: Literal["lancedb"]) -> "type[LanceDBConnection]": ...


@overload
def get_connection_class(provider: Literal["pgvector"]) -> "type[PgVectorConnection]": ...


@overload
def get_connection_class(provider: Literal["weaviate"]) -> "type[WeaviateConnection]": ...


@overload
def get_connection_class(provider: Literal["milvus"]) -> "type[MilvusConnection]": ...


def get_connection_class(provider: str) -> "type[VectorDBConnection]":
    """Get connection class for a provider, with lazy import.

    Args:
        provider: Provider name (chromadb, qdrant, pinecone, etc.)

    Returns:
        Connection class for the provider

    Raises:
        ImportError: If provider package is not installed
        ValueError: If provider is not supported
    """
    # Lazy imports - only import when actually needed
    if provider == "chromadb":
        from .chroma_connection import ChromaDBConnection

        return ChromaDBConnection
    if provider == "qdrant":
        from .qdrant_connection import QdrantConnection

        return QdrantConnection
    if provider == "pinecone":
        from .pinecone_connection import PineconeConnection

        return PineconeConnection
    if provider == "lancedb":
        from .lancedb_connection import LanceDBConnection

        return LanceDBConnection
    if provider == "pgvector":
        from .pgvector_connection import PgVectorConnection

        return PgVectorConnection
    if provider == "weaviate":
        from .weaviate_connection import WeaviateConnection

        return WeaviateConnection
    if provider == "milvus":
        # Milvus is experimental: wrap ImportError explicitly to give a clear
        # user-facing message.  All other providers let ImportError propagate
        # naturally — do not mimic this pattern for new providers.
        try:
            from .milvus_connection import MilvusConnection

            return MilvusConnection
        except ImportError:
            raise ImportError("Milvus provider is not installed. Install with: pip install vector-inspector[milvus]")
    else:
        raise ValueError(f"Unsupported provider: {provider}")
