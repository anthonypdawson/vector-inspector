# Ollama Embedding Setup

## Overview

Vector Inspector supports using local Ollama models for embeddings, allowing you to work with collections that were embedded using Ollama models without requiring HuggingFace access.

## Prerequisites

1. **Ollama running locally**: Ensure Ollama is installed and running at `http://localhost:11434`
   ```bash
   ollama serve
   ```

2. **Model pulled**: Pull the embedding model you want to use
   ```bash
   ollama pull nomic-embed-text
   # or
   ollama pull mxbai-embed-large
   ```

## Configuration

### Via UI

1. Open your collection in Vector Inspector
2. In the **Info Panel**, find the "Embedding Model" section
3. Click **Configure...**
4. Select or enter:
   - **Model Type**: `ollama`
   - **Model Name**: Your Ollama model name (e.g., `nomic-embed-text`, `mxbai-embed-large`)

### Via Settings (Programmatic)

```python
from vector_inspector.services.settings_service import SettingsService

settings = SettingsService()
settings.save_embedding_model(
    connection_id="your-connection-id",
    collection_name="your-collection",
    model_name="nomic-embed-text",
    model_type="ollama"
)
```

## Supported Ollama Embedding Models

Common Ollama embedding models that work well:

- **nomic-embed-text** - 768 dimensions, general purpose
- **mxbai-embed-large** - 1024 dimensions, high quality
- **all-minilm** - 384 dimensions, fast and compact
- **snowflake-arctic-embed** - 1024 dimensions, strong performance

Check available models:
```bash
ollama list
```

## How It Works

1. **No Dependencies**: Uses Ollama's HTTP API directly (same as LLM provider)
2. **Endpoint**: `POST http://localhost:11434/api/embed`
3. **Request**: `{"model": "model-name", "input": "text"}`
4. **Response**: `{"embeddings": [[...]]}`
5. **Timeout**: 30 seconds default (configurable via `OLLAMA_TIMEOUT` environment variable)

## Configuration Options

### Timeout

The default timeout for Ollama embedding requests is 30 seconds. You can override this using an environment variable:

```bash
# Set custom timeout (in seconds)
export OLLAMA_TIMEOUT=60

# Run Vector Inspector with custom timeout
./scripts/run.sh
```

This is useful for:
- **Large models**: Some Ollama models take longer to generate embeddings
- **Slow hardware**: Adjust for CPU-only or older systems
- **Network latency**: If Ollama is running on a remote machine

## Troubleshooting

### "Failed to get embedding from Ollama"

**Cause**: Ollama server not running or model not available

**Solutions**:
1. Start Ollama: `ollama serve`
2. Verify it's running: `curl http://localhost:11434/api/tags`
3. Pull the model: `ollama pull <model-name>`

### "Connection refused"

**Cause**: Ollama not listening on default port

**Solutions**:
1. Check Ollama is running: `ps aux | grep ollama`
2. Verify port: Ollama typically runs on `11434`
3. Restart Ollama if needed

### Dimension Mismatch

**Cause**: Collection was created with a different embedding dimension

**Solution**:
- Make sure your Ollama model produces vectors of the same dimension as your collection
- Check model dimension: Different models produce different dimensions
- If migrating from HuggingFace model, ensure dimensions match

### Timeout Errors

**Cause**: Ollama embedding request exceeds 30-second timeout

**Symptoms**:
```
URLError: <urlopen error [Errno 60] Operation timed out>
```

**Solutions**:
1. **Increase timeout**: Set `OLLAMA_TIMEOUT` environment variable
   ```bash
   export OLLAMA_TIMEOUT=60  # 60 seconds
   ```
2. **Check model performance**: Some large models are slower
   ```bash
   # Test embedding speed manually
   time curl -X POST http://localhost:11434/api/embed \
     -d '{"model": "mxbai-embed-large", "input": "test"}'
   ```
3. **Use faster model**: Consider switching to a smaller model like `all-minilm`

## Example Workflow

### Existing Collection (Embedded with Ollama)

If your collection was already embedded using Ollama:

1. Start Ollama with the same model you used to create the collection
   ```bash
   ollama pull nomic-embed-text
   ollama serve
   ```

2. Configure the collection in Vector Inspector to use that model
   - Set model_type: `ollama`
   - Set model_name: `nomic-embed-text`

3. Queries will now use your local Ollama instead of HuggingFace!

### New Collection with Ollama

1. Start Ollama and pull your preferred embedding model
2. Create collection in Vector Inspector
3. Configure embedding: model_type=`ollama`, model_name=`your-model`
4. Ingest documents - they'll be embedded using Ollama

## Performance Notes

- **Speed**: Local Ollama is typically faster than HuggingFace downloads
- **Privacy**: All embeddings happen locally, no data sent to external services
- **Reliability**: Works offline, no internet dependency
- **Resources**: Requires local compute resources for embedding generation

## Integration with LLM Console

Vector Inspector already uses Ollama for LLM operations. This embedding support completes the integration, allowing fully local operation:

- **LLM**: Ollama for chat/completions
- **Embeddings**: Ollama for semantic search
- **Storage**: Local vector database

Perfect for air-gapped or privacy-sensitive environments!
