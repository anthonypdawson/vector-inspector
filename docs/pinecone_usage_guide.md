# Pinecone Integration Guide

This document describes how to use Vector Inspector with Pinecone, a cloud-hosted vector database service.

## Overview

Vector Inspector now supports Pinecone as a vector database provider. Pinecone is a fully managed vector database service that offers high-performance similarity search at scale.

## Prerequisites

1. A Pinecone account (free tier available at [pinecone.io](https://www.pinecone.io))
2. A Pinecone API key (available in your Pinecone console)
3. Vector Inspector installed with Pinecone support

## Connecting to Pinecone

### Using the Connection Dialog

1. Launch Vector Inspector
2. Click **"Connect"** to open the connection dialog
3. Select **"Pinecone"** from the provider dropdown
4. Enter your Pinecone API key
5. Click **"Connect"**

### Using Connection Profiles

1. Go to the **"Profiles"** tab
2. Click **"+"** to create a new profile
3. Enter a profile name (e.g., "My Pinecone Account")
4. Select **"Pinecone"** as the provider
5. Enter your Pinecone API key
6. Click **"Save"**
7. Double-click the profile to connect

### API Key Security

- API keys are stored securely using your system's keyring (Windows Credential Manager, macOS Keychain, Linux Secret Service)
- Keys are never stored in plain text
- To update an API key, edit the profile and enter a new key

## Features

### Supported Operations

Pinecone integration in Vector Inspector supports:

- ✅ Listing all indexes in your account
- ✅ Viewing index metadata (dimension, metric, size, status)
- ✅ Querying vectors by similarity (requires embeddings)
- ✅ Adding vectors with metadata
- ✅ Updating vectors
- ✅ Deleting vectors (by ID or filter)
- ✅ Creating new indexes
- ✅ Deleting indexes
- ✅ Metadata filtering
- ✅ Retrieving vectors by ID

### Known Limitations

Due to Pinecone API constraints, the following features have limitations:

- ⚠️ **List All Vectors**: Pinecone does not provide an API to enumerate all vectors in an index. Use query operations to retrieve vectors.
- ⚠️ **Text Search**: You must provide pre-computed embeddings for queries. Vector Inspector will use dimension-aware embedding models when available.
- ⚠️ **Pagination**: Limited support for browsing large indexes systematically.
- ⚠️ **Count by Metadata**: Total vector count is available, but counts filtered by metadata require queries.

### Pinecone-Specific Features

The info panel displays Pinecone-specific information:

- Index host URL
- Index status (ready, initializing, etc.)
- Serverless or pod-based spec
- Cloud provider and region (when available)

## Usage Examples

### Creating an Index

```python
# In the Data Management tab
1. Click "Create Collection"
2. Enter index name (e.g., "my-embeddings")
3. Specify vector dimension (e.g., 384 for all-MiniLM-L6-v2)
4. Select distance metric (Cosine, Euclidean, DotProduct)
5. Click "Create"
```

### Adding Vectors

```python
# Pinecone requires embeddings for all vectors
1. Navigate to your index
2. Click "Add Vectors"
3. Provide:
   - Vector IDs
   - Embeddings (required)
   - Metadata (optional)
   - Document text (stored in metadata)
4. Click "Add"
```

### Querying Vectors

```python
# Vector similarity search
1. Go to the Search tab
2. Select your index
3. Enter query text or provide a query embedding
4. Adjust top-k results
5. Add metadata filters if needed
6. Click "Search"
```

### Metadata Filtering

Pinecone supports rich metadata filtering:

```python
# Examples of supported filters:
- Equality: {"category": "news"}
- Inequality: {"price": {"$gt": 10}}
- Range: {"date": {"$gte": "2024-01-01", "$lt": "2024-02-01"}}
- In: {"status": {"$in": ["active", "pending"]}}
- Not In: {"status": {"$nin": ["deleted"]}}
```

## Best Practices

### API Key Management

- Never commit API keys to version control
- Use environment variables or secure vaults for automation
- Rotate API keys regularly
- Use read-only keys for inspection-only workflows

### Performance

- Pinecone queries are subject to API rate limits (varies by plan)
- Use appropriate batch sizes (100 vectors per upsert is optimal)
- Leverage metadata filters to reduce result set sizes
- Cache frequently accessed vectors client-side

### Cost Optimization

- Use the free tier for development and testing
- Monitor vector counts to stay within plan limits
- Delete unused indexes to free up resources
- Use namespaces to organize vectors within an index

## Troubleshooting

### "Connection Failed"

- Verify your API key is correct
- Check your internet connection
- Ensure your Pinecone account is active
- Check Pinecone status page for service issues

### "Failed to list indexes"

- Verify API key has appropriate permissions
- Check for network firewall restrictions
- Ensure you haven't exceeded API rate limits

### "Query failed"

- Ensure query embeddings match index dimension
- Verify metadata filter syntax
- Check that index exists and is ready
- Confirm API key permissions include query access

### "Rate limit exceeded"

- Reduce query frequency
- Implement backoff/retry logic (Vector Inspector handles this automatically)
- Consider upgrading your Pinecone plan
- Use batch operations instead of individual calls

## API Rate Limits

Pinecone enforces rate limits based on your plan:

- Free tier: Limited requests per minute
- Paid tiers: Higher limits based on plan

Vector Inspector implements automatic retry with exponential backoff for rate-limited requests.

## Additional Resources

- [Pinecone Documentation](https://docs.pinecone.io/)
- [Pinecone Python Client](https://github.com/pinecone-io/pinecone-python-client)
- [Vector Inspector GitHub](https://github.com/anthonypdawson/vector-inspector)
- [Report Issues](https://github.com/anthonypdawson/vector-inspector/issues)

## Migration from Other Providers

### From ChromaDB

```python
# Export from ChromaDB
collections = chroma_conn.list_collections()
for coll_name in collections:
    items = chroma_conn.get_all_items(coll_name)
    
# Import to Pinecone
# Note: You'll need to create the index with matching dimensions first
pinecone_conn.create_collection(coll_name, vector_size=dimension)
pinecone_conn.add_items(
    coll_name,
    documents=items['documents'],
    embeddings=items['embeddings'],
    ids=items['ids'],
    metadatas=items['metadatas']
)
```

### From Qdrant

Similar process - export from Qdrant and import to Pinecone, ensuring:
- Vector dimensions match
- Metadata schemas are compatible
- Distance metrics are equivalent

## Support

For Pinecone-specific issues in Vector Inspector:

1. Check this documentation
2. Review [GitHub Issues](https://github.com/anthonypdawson/vector-inspector/issues)
3. Open a new issue with:
   - Vector Inspector version
   - Pinecone plan (free/paid)
   - Error messages
   - Steps to reproduce

For Pinecone platform issues, contact [Pinecone Support](https://support.pinecone.io/).

---

**Last Updated**: January 2026
