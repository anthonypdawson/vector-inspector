"""Qdrant connection manager."""

from typing import Optional, List, Dict, Any
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, 
    Filter, FieldCondition, MatchValue, Range
)
from qdrant_client.http.models import SearchRequest

from .base_connection import VectorDBConnection


class QdrantConnection(VectorDBConnection):
    """Manages connection to Qdrant and provides query interface."""
    
    def __init__(
        self, 
        path: Optional[str] = None, 
        url: Optional[str] = None,
        host: Optional[str] = None, 
        port: Optional[int] = None,
        api_key: Optional[str] = None,
        prefer_grpc: bool = False
    ):
        """
        Initialize Qdrant connection.
        
        Args:
            path: Path for local/embedded client
            url: Full URL for remote client (e.g., "http://localhost:6333")
            host: Host for remote client
            port: Port for remote client (default: 6333)
            api_key: API key for authentication (Qdrant Cloud)
            prefer_grpc: Use gRPC instead of REST
        """
        self.path = path
        self.url = url
        self.host = host
        self.port = port or 6333
        self.api_key = api_key
        self.prefer_grpc = prefer_grpc
        self._client: Optional[QdrantClient] = None
        
    def connect(self) -> bool:
        """
        Establish connection to Qdrant.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if self.path:
                # Local/embedded mode
                self._client = QdrantClient(path=self.path, check_compatibility=False)
            elif self.url:
                # Full URL provided
                self._client = QdrantClient(
                    url=self.url,
                    api_key=self.api_key,
                    prefer_grpc=self.prefer_grpc,
                    check_compatibility=False
                )
            elif self.host:
                # Host and port provided
                self._client = QdrantClient(
                    host=self.host,
                    port=self.port,
                    api_key=self.api_key,
                    prefer_grpc=self.prefer_grpc,
                    check_compatibility=False
                )
            else:
                # Default to in-memory client
                self._client = QdrantClient(":memory:", check_compatibility=False)
            
            # Test connection
            self._client.get_collections()
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close connection to Qdrant."""
        if self._client:
            self._client.close()
        self._client = None
    
    @property
    def is_connected(self) -> bool:
        """Check if connected to Qdrant."""
        return self._client is not None
    
    def list_collections(self) -> List[str]:
        """
        Get list of all collections.
        
        Returns:
            List of collection names
        """
        if not self._client:
            return []
        try:
            collections = self._client.get_collections()
            return [col.name for col in collections.collections]
        except Exception as e:
            print(f"Failed to list collections: {e}")
            return []
    
    def get_collection_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get collection metadata and statistics.
        
        Args:
            name: Collection name
            
        Returns:
            Dictionary with collection info
        """
        if not self._client:
            return None
        
        try:
            # Get collection info
            collection_info = self._client.get_collection(name)
            
            # Get a sample point to determine metadata fields
            sample = self._client.scroll(
                collection_name=name,
                limit=1,
                with_payload=True,
                with_vectors=False
            )
            
            metadata_fields = []
            if sample[0] and len(sample[0]) > 0:
                point = sample[0][0]
                if point.payload:
                    # Extract metadata fields, excluding 'document' if present
                    metadata_fields = [k for k in point.payload.keys() if k != 'document']
            
            return {
                "name": name,
                "count": collection_info.points_count,
                "metadata_fields": metadata_fields,
            }
        except Exception as e:
            print(f"Failed to get collection info: {e}")
            return None
    
    def _build_qdrant_filter(self, where: Optional[Dict[str, Any]] = None) -> Optional[Filter]:
        """
        Build Qdrant filter from ChromaDB-style where clause.
        
        Args:
            where: ChromaDB-style filter dictionary
            
        Returns:
            Qdrant Filter object or None
        """
        if not where:
            return None
        
        try:
            conditions = []
            for key, value in where.items():
                if isinstance(value, dict):
                    # Handle operators like $eq, $ne, $gt, $gte, $lt, $lte
                    for op, val in value.items():
                        if op == "$eq":
                            conditions.append(FieldCondition(key=key, match=MatchValue(value=val)))
                        elif op == "$ne":
                            conditions.append(FieldCondition(key=key, match=MatchValue(value=val)))
                            # Note: Qdrant doesn't have direct "not equal", would need to use must_not
                        elif op in ["$gt", "$gte", "$lt", "$lte"]:
                            range_args = {}
                            if op == "$gt":
                                range_args["gt"] = val
                            elif op == "$gte":
                                range_args["gte"] = val
                            elif op == "$lt":
                                range_args["lt"] = val
                            elif op == "$lte":
                                range_args["lte"] = val
                            conditions.append(FieldCondition(key=key, range=Range(**range_args)))
                else:
                    # Direct equality match
                    conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
            
            if conditions:
                return Filter(must=conditions)
            return None
        except Exception as e:
            print(f"Failed to build filter: {e}")
            return None
    
    def query_collection(
        self,
        collection_name: str,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Query a collection for similar vectors.
        
        Args:
            collection_name: Name of collection to query
            query_texts: Text queries (Qdrant will embed automatically)
            query_embeddings: Direct embedding vectors to search
            n_results: Number of results to return
            where: Metadata filter
            where_document: Document content filter (limited support)
            
        Returns:
            Query results or None if failed
        """
        if not self._client:
            return None
        
        if not query_texts and not query_embeddings:
            print("Either query_texts or query_embeddings required")
            return None
        
        try:
            # Build filter
            qdrant_filter = self._build_qdrant_filter(where)
            
            # Perform search for each query
            all_results = {
                "ids": [],
                "distances": [],
                "documents": [],
                "metadatas": [],
                "embeddings": []
            }
            
            # Use query_texts if provided (Qdrant handles embedding)
            queries = query_texts if query_texts else []
            
            # If embeddings provided instead, use them
            if query_embeddings and not query_texts:
                queries = query_embeddings
            
            for query in queries:
                # Embed text queries if needed
                if isinstance(query, str):
                    # Generate embeddings for text query
                    try:
                        from sentence_transformers import SentenceTransformer
                        model = SentenceTransformer("all-MiniLM-L6-v2")
                        query_vector = model.encode(query).tolist()
                    except Exception as e:
                        print(f"Failed to embed query text: {e}")
                        continue
                else:
                    query_vector = query
                
                # Use HTTP search API for compatibility with older Qdrant servers
                search_result = self._client._client.http.search_api.search_points(
                    collection_name=collection_name,
                    search_request=SearchRequest(
                        vector=query_vector,
                        limit=n_results,
                        filter=qdrant_filter,
                        with_payload=True,
                        with_vector=True
                    )
                )
                search_results = search_result.result
                
                # Transform results to standard format
                ids = []
                distances = []
                documents = []
                metadatas = []
                embeddings = []
                
                for result in search_results:
                    ids.append(str(result.id))
                    distances.append(result.score)
                    
                    # Extract document and metadata from payload
                    payload = result.payload or {}
                    documents.append(payload.get('document', ''))
                    
                    # Metadata is everything except 'document'
                    metadata = {k: v for k, v in payload.items() if k != 'document'}
                    metadatas.append(metadata)
                    
                    # Extract embedding
                    embeddings.append(result.vector if result.vector else [])
                
                all_results["ids"].append(ids)
                all_results["distances"].append(distances)
                all_results["documents"].append(documents)
                all_results["metadatas"].append(metadatas)
                all_results["embeddings"].append(embeddings)
            
            return all_results
        except Exception as e:
            print(f"Query failed: {e}")
            return None
    
    def get_all_items(
        self,
        collection_name: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get all items from a collection.
        
        Args:
            collection_name: Name of collection
            limit: Maximum number of items to return
            offset: Number of items to skip
            where: Metadata filter
            
        Returns:
            Collection items or None if failed
        """
        if not self._client:
            return None
        
        try:
            # Build filter
            qdrant_filter = self._build_qdrant_filter(where)
            
            # Use scroll to retrieve items
            points, next_offset = self._client.scroll(
                collection_name=collection_name,
                scroll_filter=qdrant_filter,
                limit=limit,
                offset=offset,
                with_payload=True,
                with_vectors=True
            )
            
            # Transform to standard format
            ids = []
            documents = []
            metadatas = []
            embeddings = []
            
            for point in points:
                ids.append(str(point.id))
                
                payload = point.payload or {}
                documents.append(payload.get('document', ''))
                
                # Metadata is everything except 'document'
                metadata = {k: v for k, v in payload.items() if k != 'document'}
                metadatas.append(metadata)
                
                # Extract embedding
                if isinstance(point.vector, dict):
                    # Named vectors - use the first one
                    embeddings.append(list(point.vector.values())[0] if point.vector else [])
                else:
                    embeddings.append(point.vector if point.vector else [])
            
            return {
                "ids": ids,
                "documents": documents,
                "metadatas": metadatas,
                "embeddings": embeddings
            }
        except Exception as e:
            print(f"Failed to get items: {e}")
            return None
    
    def add_items(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ) -> bool:
        """
        Add items to a collection.
        
        Args:
            collection_name: Name of collection
            documents: Document texts
            metadatas: Metadata for each document
            ids: IDs for each document (will generate UUIDs if not provided)
            embeddings: Pre-computed embeddings (required for Qdrant)
            
        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            return False
        
        if not embeddings:
            print("Embeddings are required for Qdrant")
            return False
        
        try:
            # Generate IDs if not provided
            if not ids:
                ids = [str(uuid.uuid4()) for _ in documents]
            
            # Build points
            points = []
            for i, (doc_id, document, embedding) in enumerate(zip(ids, documents, embeddings)):
                # Build payload with document and metadata
                payload = {"document": document}
                if metadatas and i < len(metadatas):
                    payload.update(metadatas[i])
                
                point = PointStruct(
                    id=doc_id,
                    vector=embedding,
                    payload=payload
                )
                points.append(point)
            
            # Upsert points
            self._client.upsert(
                collection_name=collection_name,
                points=points
            )
            return True
        except Exception as e:
            print(f"Failed to add items: {e}")
            return False
    
    def update_items(
        self,
        collection_name: str,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ) -> bool:
        """
        Update items in a collection.
        
        Args:
            collection_name: Name of collection
            ids: IDs of items to update
            documents: New document texts
            metadatas: New metadata
            embeddings: New embeddings
            
        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            return False
        
        try:
            # For Qdrant, we need to retrieve existing points, update them, and upsert
            for i, point_id in enumerate(ids):
                # Get existing point
                existing = self._client.retrieve(
                    collection_name=collection_name,
                    ids=[point_id],
                    with_payload=True,
                    with_vectors=True
                )
                
                if not existing:
                    continue
                
                point = existing[0]
                payload = point.payload or {}
                vector = point.vector
                
                # Update fields as provided
                if documents and i < len(documents):
                    payload['document'] = documents[i]
                
                if metadatas and i < len(metadatas):
                    # Update metadata, keeping 'document' field
                    doc = payload.get('document', '')
                    payload = metadatas[i].copy()
                    payload['document'] = doc
                
                if embeddings and i < len(embeddings):
                    vector = embeddings[i]
                
                # Upsert updated point
                self._client.upsert(
                    collection_name=collection_name,
                    points=[PointStruct(id=point_id, vector=vector, payload=payload)]
                )
            
            return True
        except Exception as e:
            print(f"Failed to update items: {e}")
            return False
    
    def delete_items(
        self,
        collection_name: str,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Delete items from a collection.
        
        Args:
            collection_name: Name of collection
            ids: IDs of items to delete
            where: Metadata filter for items to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            return False
        
        try:
            if ids:
                # Delete by IDs
                self._client.delete(
                    collection_name=collection_name,
                    points_selector=ids
                )
            elif where:
                # Delete by filter
                qdrant_filter = self._build_qdrant_filter(where)
                if qdrant_filter:
                    self._client.delete(
                        collection_name=collection_name,
                        points_selector=qdrant_filter
                    )
            return True
        except Exception as e:
            print(f"Failed to delete items: {e}")
            return False
    
    def delete_collection(self, name: str) -> bool:
        """
        Delete an entire collection.
        
        Args:
            name: Collection name
            
        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            return False
        
        try:
            self._client.delete_collection(collection_name=name)
            return True
        except Exception as e:
            print(f"Failed to delete collection: {e}")
            return False
    
    def create_collection(
        self, 
        name: str, 
        vector_size: int,
        distance: str = "Cosine"
    ) -> bool:
        """
        Create a new collection.
        
        Args:
            name: Collection name
            vector_size: Dimension of vectors
            distance: Distance metric ("Cosine", "Euclid", "Dot")
            
        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            return False
        
        try:
            # Map distance string to Qdrant Distance enum
            distance_map = {
                "Cosine": Distance.COSINE,
                "Euclid": Distance.EUCLID,
                "Euclidean": Distance.EUCLID,
                "Dot": Distance.DOT,
            }
            
            qdrant_distance = distance_map.get(distance, Distance.COSINE)
            
            self._client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=qdrant_distance
                )
            )
            return True
        except Exception as e:
            print(f"Failed to create collection: {e}")
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """
        Get information about the current connection.
        
        Returns:
            Dictionary with connection details
        """
        info = {
            "provider": "Qdrant",
            "connected": self.is_connected,
        }
        
        if self.path:
            info["mode"] = "local"
            info["path"] = self.path
        elif self.url:
            info["mode"] = "remote"
            info["url"] = self.url
        elif self.host:
            info["mode"] = "remote"
            info["host"] = self.host
            info["port"] = self.port
        else:
            info["mode"] = "memory"
        
        return info
