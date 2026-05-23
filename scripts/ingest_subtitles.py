#!/usr/bin/env python3
"""Ingest a subtitles (.srt) file into the project's ChromaDB collection.

Usage: run from project root:
    pdm run python scripts/ingest_subtitles.py
"""

import argparse
import re
from pathlib import Path

from vector_inspector.core.provider_factory import ProviderFactory
from vector_inspector.core.sample_data.text_generator import generate_subtitles_from_file


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Ingest a subtitles (.srt) file into the project's ChromaDB collection."
    )
    parser.add_argument("srt", nargs="?", help="Path to .srt file (defaults to data/Back.to.the.Future.srt)")
    parser.add_argument("--collection", "-c", help="Optional collection name override")
    args = parser.parse_args()

    if args.srt:
        srt_path = Path(args.srt)
        if not srt_path.is_absolute():
            srt_path = (project_root / args.srt).resolve()
    else:
        srt_path = project_root / "data" / "Back.to.the.Future.srt"
    if not srt_path.exists():
        print(f"Subtitles file not found: {srt_path}")
        return 2

    # Create a persistent ChromaDB connection in project data directory
    # Use a project-local persistent directory for ChromaDB
    chroma_config = {"type": "persistent", "path": str(project_root / "data" / "chroma_db")}
    conn = ProviderFactory.create("chromadb", chroma_config)
    ok = conn.connect()
    if not ok:
        print("Failed to connect to ChromaDB")
        return 3

    # Derive a friendly movie title and a safe collection name from the
    # subtitles filename when not explicitly provided.
    if args.collection:
        collection_name = args.collection
    else:
        # Get stem (filename without suffix) and normalize separators to spaces
        stem = srt_path.stem
        title = re.sub(r"[._]+", " ", stem).strip()
        # Create a safe collection name by removing non-alphanumeric chars
        collection_name = re.sub(r"[^0-9A-Za-z]+", "", title)
    # Create collection (vector_size is a convenience parameter; collection metadata
    # will be inferred when embeddings are added)
    created = conn.create_collection(collection_name, vector_size=1536)
    if not created:
        print(f"Failed to create/get collection {collection_name}")
        return 4

    print(f"Using subtitles file: {srt_path}")
    print(f"Movie title: {title if 'title' in locals() else srt_path.stem}")
    print(f"Collection name: {collection_name}")

    samples = generate_subtitles_from_file(str(srt_path), count=0, randomize=False)
    if not samples:
        print("No cues parsed from subtitles file")
        return 5

    documents = [s["text"] for s in samples]
    metadatas = [s["metadata"] for s in samples]
    # Use a short, stable prefix derived from the collection name for ids
    prefix = collection_name[:8].lower() or "doc"
    ids = [f"{prefix}-{m['cue_index']}" for m in metadatas]

    print(f"Adding {len(documents)} documents to collection '{collection_name}'...")
    success = conn.add_items(collection_name, documents=documents, metadatas=metadatas, ids=ids)
    if not success:
        print("Failed to add items to collection")
        return 6

    count = conn.count_collection(collection_name)
    print(f"Ingestion complete. Collection '{collection_name}' now has {count} items.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
