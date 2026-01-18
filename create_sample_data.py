"""Sample script to populate ChromaDB with test data."""

import chromadb
from chromadb.utils import embedding_functions
import argparse
import sys


def create_sample_data_chroma():
    """Create sample data for ChromaDB."""
    print("Creating sample ChromaDB data...")
    import chromadb
    client = chromadb.PersistentClient(path="./chroma_data")
    collection = client.get_or_create_collection(
        name="sample_documents",
        metadata={"description": "Sample documents for testing"}
    )
    documents, metadatas, ids = get_sample_docs()
    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    print(f"Added {len(documents)} documents to collection '{collection.name}'")
    print(f"Collection now contains {collection.count()} items")
    print("\nYou can now:")
    print("1. Run the Vector Viewer application")
    print("2. Connect to Persistent storage with path: ./chroma_data")
    print("3. Select the 'sample_documents' collection")
    print("4. Browse, search, and visualize the data!")


def create_sample_data_qdrant(host="localhost", port=6333, collection_name="sample_documents", vector_size=384):
    """Create sample data for Qdrant."""
    print(f"Creating sample Qdrant data on {host}:{port}...")
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    from sentence_transformers import SentenceTransformer
    
    client = QdrantClient(host=host, port=port, prefer_grpc=False, check_compatibility=False)
    # Delete collection if it exists (to avoid config mismatch)
    try:
        client.delete_collection(collection_name=collection_name)
        print(f"Deleted existing collection '{collection_name}' (if it existed)")
    except Exception as e:
        print(f"Could not delete collection (may not exist): {e}")
    # Try to create collection (ignore if exists)
    try:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
        print(f"Created collection '{collection_name}' with vector size {vector_size}")
    except Exception as e:
        print(f"Collection may already exist: {e}")
    
    documents, metadatas, ids = get_sample_docs()
    # Generate embeddings
    print("Generating embeddings with sentence-transformers (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(documents, show_progress_bar=True).tolist()
    
    # Build points list
    points = []
    for i in range(len(documents)):
        point = PointStruct(
            id=i,  # Use integer IDs for Qdrant compatibility
            vector=embeddings[i],
            payload={
                "doc_id": ids[i],  # Store original string ID in payload
                "document": documents[i],
                **metadatas[i]
            }
        )
        points.append(point)
    
    # Add to Qdrant
    print(f"Upserting {len(points)} points to Qdrant...")
    client.upsert(
        collection_name=collection_name,
        points=points
    )
    print(f"Added {len(documents)} documents to collection '{collection_name}'")
    print("\nYou can now:")
    print(f"1. Run the Vector Viewer application")
    print(f"2. Connect to Qdrant at {host}:{port}")
    print(f"3. Select the '{collection_name}' collection")
    print("4. Browse, search, and visualize the data!")


def get_sample_docs():
    documents = [
        "The quick brown fox jumps over the lazy dog.",
        "Python is a high-level programming language.",
        "Machine learning is a subset of artificial intelligence.",
        "Neural networks are inspired by the human brain.",
        "Data science involves extracting insights from data.",
        "Vector databases store high-dimensional embeddings.",
        "Natural language processing enables computers to understand text.",
        "Deep learning uses multiple layers of neural networks.",
        "Embeddings represent data in continuous vector spaces.",
        "Similarity search finds vectors close to a query vector.",
    ]
    metadatas = [
        {"category": "animals", "length": "short"},
        {"category": "programming", "length": "short"},
        {"category": "ai", "length": "short"},
        {"category": "ai", "length": "short"},
        {"category": "data", "length": "short"},
        {"category": "databases", "length": "short"},
        {"category": "ai", "length": "medium"},
        {"category": "ai", "length": "short"},
        {"category": "vectors", "length": "short"},
        {"category": "vectors", "length": "short"},
    ]
    ids = [f"doc_{i}" for i in range(len(documents))]
    return documents, metadatas, ids


def main():
    parser = argparse.ArgumentParser(description="Create sample data for Vector Viewer.")
    parser.add_argument("--provider", choices=["chroma", "qdrant"], default="chroma", help="Which vector DB to use")
    parser.add_argument("--host", default="localhost", help="Qdrant host (for qdrant)")
    parser.add_argument("--port", type=int, default=6333, help="Qdrant port (for qdrant)")
    parser.add_argument("--vector-size", type=int, default=384, help="Vector size for Qdrant collection")
    parser.add_argument("--collection", default="sample_documents", help="Collection name")
    args = parser.parse_args()

    if args.provider == "chroma":
        create_sample_data_chroma()
    elif args.provider == "qdrant":
        create_sample_data_qdrant(host=args.host, port=args.port, collection_name=args.collection, vector_size=args.vector_size)
    else:
        print("Unknown provider.")
        sys.exit(1)


if __name__ == "__main__":
    main()
