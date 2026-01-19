# Database Provider Abstraction

## Overview

Vector Inspector now uses an abstract base class (`VectorDBConnection`) to support multiple vector database providers. This allows the application to work with different vector databases (ChromaDB, Pinecone, Weaviate, Qdrant, etc.) without modifying the core UI code.

## Architecture

### Base Class: `VectorDBConnection`

Located at: `src/vector_viewer/core/connections/base_connection.py`

This abstract base class defines the interface that all vector database providers must implement:

#### Required Methods

- **Connection Management**
  - `connect() -> bool`: Establish connection to the database
  - `disconnect()`: Close the connection
  - `is_connected -> bool`: Check connection status (property)

- **Collection Operations**
  - `list_collections() -> List[str]`: Get all collection/index names
  - `get_collection_info(name: str) -> Optional[Dict[str, Any]]`: Get metadata and statistics
  - `delete_collection(name: str) -> bool`: Delete entire collection

- **Data Operations**
  - `query_collection(...)`: Perform similarity search
  - `get_all_items(...)`: Retrieve items with pagination
  - `add_items(...)`: Add new items to a collection
  - `update_items(...)`: Update existing items
  - `delete_items(...)`: Delete specific items

- **Optional Methods**
  - `get_connection_info() -> Dict[str, Any]`: Get provider-specific connection details

### Current Implementation: `ChromaDBConnection`

Located at: `src/vector_viewer/core/connections/chroma_connection.py`

The existing ChromaDB implementation now inherits from `VectorDBConnection` and provides full compatibility with the abstract interface.

## Adding a New Database Provider

To add support for a new vector database:

1. **Create a new connection class** in `src/vector_viewer/core/connections/`
   
   ```python
   from .base_connection import VectorDBConnection
   
   class NewDBConnection(VectorDBConnection):
       def __init__(self, ...):
           # Initialize provider-specific parameters
           pass
       
       def connect(self) -> bool:
           # Implement connection logic
           pass
       
       # Implement all other abstract methods...
   ```

2. **Export the new class** in `__init__.py`
   
   ```python
   from .new_db_connection import NewDBConnection
   
   __all__ = ["VectorDBConnection", "ChromaDBConnection", "NewDBConnection"]
   ```

3. **Update the UI** to allow provider selection (in `connection_view.py`)
   
   - Add radio button or dropdown for provider selection
   - Show provider-specific configuration fields
   - Instantiate the appropriate connection class

4. **Test the implementation** thoroughly with your provider

## Method Return Formats

### `get_collection_info`

```python
{
    "name": str,           # Collection name
    "count": int,          # Number of items
    "metadata_fields": List[str]  # Available metadata field names
}
```

### `query_collection` and `get_all_items`

```python
{
    "ids": List[str],                      # Item IDs
    "distances": List[float],              # Similarity scores (query_collection only)
    "documents": List[str],                # Document texts
    "metadatas": List[Dict[str, Any]],     # Metadata dictionaries
    "embeddings": List[List[float]]        # Vector embeddings
}
```

## Benefits

1. **Extensibility**: Add new database providers without modifying existing code
2. **Type Safety**: All views use `VectorDBConnection` type hints
3. **Consistency**: Standard interface across all providers
4. **Maintainability**: Changes to the interface are enforced at the abstract level
5. **Testing**: Easy to create mock providers for testing

## Migration Path

The codebase has been fully migrated to use the abstract class:

- ✅ `VectorDBConnection` abstract base class created
- ✅ `ChromaDBConnection` inherits from base class
- ✅ All UI views use `VectorDBConnection` type hints
- ✅ Exports updated in `__init__.py`

## Next Steps

To add support for additional databases:

1. **Pinecone**: Create `PineconeConnection` class
2. **Weaviate**: Create `WeaviateConnection` class
3. **Qdrant**: Create `QdrantConnection` class
4. **Milvus**: Create `MilvusConnection` class
5. **Provider Selection UI**: Add a dropdown/dialog to select provider on connection

## Example: Adding Pinecone Support

```python
# File: src/vector_viewer/core/connections/pinecone_connection.py

from typing import Optional, List, Dict, Any
import pinecone
from .base_connection import VectorDBConnection

class PineconeConnection(VectorDBConnection):
    """Pinecone vector database connection."""
    
    def __init__(self, api_key: str, environment: str):
        self.api_key = api_key
        self.environment = environment
        self._index = None
        
    def connect(self) -> bool:
        try:
            pinecone.init(api_key=self.api_key, environment=self.environment)
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        self._index = None
        pinecone.deinit()
    
    @property
    def is_connected(self) -> bool:
        return pinecone.list_indexes() is not None
    
    # ... implement remaining methods
```

## Qdrant Vector Size Guidance

When creating a collection in Qdrant, you must specify the vector size (dimension). This value must match the dimensionality of the embeddings you plan to store in the collection. If you use the wrong size, you will get errors when adding or querying vectors.

**Common vector sizes:**
- 384: all-MiniLM-L6-v2 (default for many sentence-transformers)
- 512: Universal Sentence Encoder
- 768: BERT-base, RoBERTa-base
- 1024: BERT-large, RoBERTa-large
- 1536: OpenAI text-embedding-ada-002
- 2048+: Some custom or large models

**How to choose:**
- Check your embedding model's documentation for its output dimension.
- Always use the same vector size for all items in a collection.
- If unsure, 384 is a safe default for most sentence-transformers.

**Example:**
If you use OpenAI's ada-002 embeddings, set vector size to 1536. If you use all-MiniLM-L6-v2, set it to 384.

If you change embedding models, you may need to create a new collection with the appropriate size.

## Notes

- The abstraction maintains backward compatibility with existing ChromaDB functionality
- Provider-specific features can be added as optional methods on individual implementations
- The abstract class enforces a minimum set of required functionality
- Type hints ensure compile-time checking where possible
