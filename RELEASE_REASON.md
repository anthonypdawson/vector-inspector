# Latest updates

## Pinecone Hosted Model Support Improvements
  - Direct Text Search: Added full support for Pinecone indexes with integrated (hosted) embedding models. You can now perform semantic search using plain text queries—no local embedding required.
  - Accurate Model Detection: The app now detects and displays the hosted model name (e.g., llama-text-embed-v2) in the info panel for Pinecone indexes.
  - Robust Query Handling: The search logic now uses Pinecone’s search() API for hosted models, with correct response parsing and error handling.
  - Future-Proof: Retained the ability to generate embeddings via Pinecone’s inference API for future features or advanced workflows.
  - Improved Error Handling: Added better checks and debug logging for Pinecone API responses.
  - These changes make Pinecone integration seamless and future-ready for both text and vector search scenarios.
---