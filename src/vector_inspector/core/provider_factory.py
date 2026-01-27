"""Factory for creating vector database connections from provider configs."""

from typing import Dict, Any
from vector_inspector.core.connections.base_connection import VectorDBConnection
from vector_inspector.core.connections.chroma_connection import ChromaDBConnection
from vector_inspector.core.connections.qdrant_connection import QdrantConnection
from vector_inspector.core.connections.pinecone_connection import PineconeConnection
from vector_inspector.core.connections.pgvector_connection import PgVectorConnection


class ProviderFactory:
    """Factory for creating database connections from configuration."""

    @staticmethod
    def create(
        provider: str, config: Dict[str, Any], credentials: Dict[str, Any] = None
    ) -> VectorDBConnection:
        """Create a connection object for the specified provider.

        Args:
            provider: Provider type (chromadb, qdrant, pinecone, pgvector)
            config: Provider-specific configuration
            credentials: Optional credentials (API keys, passwords, etc.)

        Returns:
            VectorDBConnection instance

        Raises:
            ValueError: If provider is unsupported or configuration is invalid
        """
        credentials = credentials or {}

        if provider == "chromadb":
            return ProviderFactory._create_chroma(config, credentials)
        elif provider == "qdrant":
            return ProviderFactory._create_qdrant(config, credentials)
        elif provider == "pinecone":
            return ProviderFactory._create_pinecone(config, credentials)
        elif provider == "pgvector":
            return ProviderFactory._create_pgvector(config, credentials)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    def _create_chroma(config: Dict[str, Any], credentials: Dict[str, Any]) -> ChromaDBConnection:
        """Create a ChromaDB connection."""
        conn_type = config.get("type")

        if conn_type == "persistent":
            return ChromaDBConnection(path=config.get("path"))
        elif conn_type == "http":
            return ChromaDBConnection(host=config.get("host"), port=config.get("port"))
        else:  # ephemeral
            return ChromaDBConnection()

    @staticmethod
    def _create_qdrant(config: Dict[str, Any], credentials: Dict[str, Any]) -> QdrantConnection:
        """Create a Qdrant connection."""
        conn_type = config.get("type")
        api_key = credentials.get("api_key")

        if conn_type == "persistent":
            return QdrantConnection(path=config.get("path"))
        elif conn_type == "http":
            return QdrantConnection(
                host=config.get("host"), port=config.get("port"), api_key=api_key
            )
        else:  # ephemeral
            return QdrantConnection()

    @staticmethod
    def _create_pinecone(config: Dict[str, Any], credentials: Dict[str, Any]) -> PineconeConnection:
        """Create a Pinecone connection."""
        api_key = credentials.get("api_key")
        if not api_key:
            raise ValueError("Pinecone requires an API key")

        return PineconeConnection(api_key=api_key)

    @staticmethod
    def _create_pgvector(config: Dict[str, Any], credentials: Dict[str, Any]) -> PgVectorConnection:
        """Create a PgVector/Postgres connection."""
        conn_type = config.get("type")

        if conn_type == "http":
            host = config.get("host", "localhost")
            port = int(config.get("port", 5432))
            database = config.get("database")
            user = config.get("user")
            # Prefer password from credentials
            password = credentials.get("password")

            return PgVectorConnection(
                host=host, port=port, database=database, user=user, password=password
            )

        raise ValueError("Unsupported connection type for PgVector profile")
