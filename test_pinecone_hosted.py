"""
Test script to check Pinecone hosted model detection and optionally add sample data.
"""

import os

from pinecone import Pinecone

# Get API key from environment
api_key = os.environ.get("PINECONE_API_KEY")
if not api_key:
    print("ERROR: PINECONE_API_KEY environment variable not set")
    exit(1)

# Initialize client
pc = Pinecone(api_key=api_key)

# Check the index
index_name = "pinecone-hosted"

print(f"\n=== Checking index: {index_name} ===\n")

try:
    # Get index description
    desc = pc.describe_index(index_name)

    print(f"Index name: {desc.name}")
    print(f"Dimension: {desc.dimension}")
    print(f"Metric: {desc.metric}")
    print(f"Host: {desc.host}")
    print(f"Status: {desc.status}")
    print(f"\nSpec type: {type(desc.spec)}")
    print(f"Spec: {desc.spec}")

    # Check for model
    if hasattr(desc.spec, "model"):
        print(f"\n✓ spec.model exists: {desc.spec.model}")
    else:
        print("\n✗ spec.model does NOT exist")

    if hasattr(desc.spec, "index_config"):
        print(f"✓ spec.index_config exists: {desc.spec.index_config}")
        if hasattr(desc.spec.index_config, "model"):
            print(f"  ✓ spec.index_config.model: {desc.spec.index_config.model}")
    else:
        print("✗ spec.index_config does NOT exist")

    # Get stats
    index = pc.Index(index_name)
    stats = index.describe_index_stats()

    print("\n=== Index Stats ===")
    print(f"Total vectors: {stats.get('total_vector_count', 0)}")
    print(f"Namespaces: {list(stats.get('namespaces', {}).keys())}")

    # Check if we should add sample data
    if stats.get("total_vector_count", 0) == 0:
        print("\n=== Index is empty ===")
        add_data = input("Would you like to add sample data? (yes/no): ").strip().lower()

        if add_data == "yes":
            # Check if this index supports text queries (has hosted model)
            if hasattr(desc.spec, "model") and desc.spec.model:
                print(f"\n✓ Index uses hosted model: {desc.spec.model}")
                print("Adding sample data using text-based upsert...")

                # For hosted models, we can upsert with text directly
                # Note: The exact API depends on Pinecone SDK version
                try:
                    # Try newer API with data parameter
                    index.upsert(
                        vectors=[
                            {
                                "id": "doc1",
                                "values": [],  # Empty for text-based
                                "metadata": {
                                    "text": "This is a sample document about artificial intelligence."
                                },
                            },
                            {
                                "id": "doc2",
                                "values": [],
                                "metadata": {"text": "Machine learning is a subset of AI."},
                            },
                            {
                                "id": "doc3",
                                "values": [],
                                "metadata": {
                                    "text": "Vector databases store high-dimensional embeddings."
                                },
                            },
                        ]
                    )
                    print("✓ Sample data added!")
                except Exception as e:
                    print(f"✗ Failed to add data: {e}")
                    print("\nNote: For Pinecone-hosted models, you typically need to use")
                    print("the Pinecone console or specific API endpoints to add data.")
            else:
                print("\n✗ No hosted model detected")
                print("You'll need to provide embeddings to add data to this index.")
    else:
        print(f"\n✓ Index has {stats.get('total_vector_count', 0)} vectors")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()

print("\n=== Done ===\n")
