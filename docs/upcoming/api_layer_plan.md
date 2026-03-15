# Vector Inspector API Layer: Implementation Plan

## 1. API Framework Selection

- **Framework:** Use FastAPI (recommended for async support, auto-docs, and modern Python).
- **Dependency:** Add FastAPI and Uvicorn to your dev dependencies via PDM:
  ```bash
  pdm add fastapi uvicorn -d
  ```

---

## 2. Project Structure

- **Recommended structure:**
  ```
  vector_inspector/
    api/
      __init__.py
      server.py
      routers/
        providers.py
        collections.py
        items.py
        search.py
        compare.py
  ```

- **api/server.py:** FastAPI app creation, main entrypoint, and router registration.
- **api/routers/**: Each file defines a logical group of endpoints.
- **Keep API logic separate** from UI and CLI logic.

This structure is modular, mirrors the existing service/core separation, and will scale as the API grows.

---

## 3. Command-Line Integration

Add real server options to the CLI using the existing `argparse` parser.

### CLI Options
- `--server`: Run the API server instead of the desktop UI.
- `--port`: Port for the API server (default: 8000).
- `--host`: Host for the API server (default: 127.0.0.1).
- `--reload`: Enable auto-reload for development.
- `--no-ui`: (Future) Run in headless mode.

### Example Integration
```python
# In _build_parser():
parser.add_argument("--server", action="store_true")
parser.add_argument("--port", type=int, default=8000)
parser.add_argument("--host", type=str, default="127.0.0.1")
parser.add_argument("--reload", action="store_true")
parser.add_argument("--no-ui", action="store_true")

# In console_entry():
if args.server:
    from vector_inspector.api.server import run_api_server
    run_api_server(host=args.host, port=args.port, reload=args.reload)
    return
```

---

## 4. API Server Implementation

### server.py
```python
from fastapi import FastAPI
from vector_inspector.api.routers import (
    providers,
    collections,
    items,
    search,
    compare,
)

app = FastAPI()

app.include_router(providers.router, prefix="/providers", tags=["providers"])
app.include_router(collections.router, tags=["collections"])
app.include_router(items.router, tags=["items"])
app.include_router(search.router, tags=["search"])
app.include_router(compare.router, prefix="/compare", tags=["compare"])

def run_api_server(host: str, port: int, reload: bool):
    import uvicorn
    uvicorn.run("vector_inspector.api.server:app", host=host, port=port, reload=reload)
```

---

## 5. REST API Layout (Hierarchical)

### Providers
- `GET /providers`
- `GET /providers/{provider_id}`

### Collections
- `GET /providers/{provider_id}/collections`
- `GET /providers/{provider_id}/collections/{collection_id}`

### Items
- `GET /providers/{provider_id}/collections/{collection_id}/items`
- `GET /providers/{provider_id}/collections/{collection_id}/items/{item_id}`

### Query
- `POST /providers/{provider_id}/collections/{collection_id}/query`

This structure mirrors your internal architecture exactly.

---

## 6. Cross‑Provider & Cross‑Collection Comparison API

### 6.1 Compare Two Providers
**POST** `/compare/providers`
```json
{
  "query": { "text": "example", "top_k": 10 },
  "left": {
    "provider_id": "pinecone",
    "collection_id": "index_a"
  },
  "right": {
    "provider_id": "qdrant",
    "collection_id": "collection_b"
  }
}
```

### 6.2 Compare Two Collections (Same Provider)
**POST** `/compare/collections`
```json
{
  "query": { "text": "example", "top_k": 10 },
  "left": {
    "provider_id": "chroma",
    "collection_id": "v1_embeddings"
  },
  "right": {
    "provider_id": "chroma",
    "collection_id": "v2_embeddings"
  }
}
```

### 6.3 Compare Two Embedding Models
**POST** `/compare/models`
```json
{
  "query": { "text": "example", "top_k": 10 },
  "left": {
    "provider_id": "local",
    "collection_id": "docs",
    "model": "text-embedding-3-small"
  },
  "right": {
    "provider_id": "local",
    "collection_id": "docs",
    "model": "text-embedding-3-large"
  }
}
```

### 6.4 Compare Arbitrary Configurations
**POST** `/compare`
```json
{
  "query": { "text": "example", "top_k": 10 },
  "left": {
    "provider_id": "pinecone",
    "collection_id": "index_a",
    "model": "openai-3-small"
  },
  "right": {
    "provider_id": "qdrant",
    "collection_id": "collection_b",
    "model": "voyage-lite"
  }
}
```

### Comparison Response Shape
```json
{
  "query": "...",
  "left_results": [...],
  "right_results": [...],
  "diff": {
    "overlap": [...],
    "unique_left": [...],
    "unique_right": [...],
    "score_delta": [...]
  },
  "metadata": {
    "latency_left_ms": 12,
    "latency_right_ms": 18,
    "provider_left": "...",
    "provider_right": "..."
  }
}
```

---

## 7. Service/Core Integration

- Reuse existing provider adapters, collection abstractions, and query services.
- No UI imports or Qt dependencies in API code.

---

## 8. State & Session Management

- **Initial version:** Single-user, in-memory state.
- **Future:** Per-session or stateless mode.

---

## 9. Error Handling

Use FastAPI’s exception system and wrap internal errors:

```python
from fastapi import HTTPException
from vector_inspector.core.errors import (
    ProviderConnectionError,
    CollectionNotFound,
    QueryError,
)

try:
    ...
except ProviderConnectionError as e:
    raise HTTPException(status_code=400, detail=str(e))
except CollectionNotFound as e:
    raise HTTPException(status_code=404, detail=str(e))
except QueryError as e:
    raise HTTPException(status_code=422, detail=str(e))
```

### Optional: Global Exception Handlers

If many endpoints share the same error‑mapping logic, consider registering FastAPI global exception handlers in `server.py` or a dedicated `errors.py` module:

```python
@app.exception_handler(ProviderConnectionError)
async def provider_error_handler(_, exc):
    return JSONResponse(status_code=400, content={"detail": str(exc)})
```

This keeps routers clean and ensures consistent HTTP responses.

---

## 10. Authentication (Optional)

Add API key or OAuth if exposing beyond localhost.

---

## 11. Testing

- Use pytest + httpx for endpoint tests.
- API tests should live under `tests/api/` for consistency.
- Aim for coverage parity with service/core (≈85–90%).
- Include regression tests for comparison endpoints.
- FastAPI auto-generates Swagger docs at `/docs`.

---

## 12. Documentation

Add instructions to README:

```
pdm run python -m vector_inspector --server
```

## 13. OpenAPI Specification

FastAPI automatically generates a full OpenAPI 3.1 schema for all endpoints, available at:

- `/openapi.json` — machine‑readable schema
- `/docs` — Swagger UI
- `/redoc` — ReDoc UI

This schema is the authoritative contract for SDKs, clients, and automated tooling.

### Customizing the OpenAPI Schema (Optional)

If you need custom tags, examples, metadata, or vendor extensions (e.g., embedding model metadata, provider capabilities), you can override the schema generator:

```python
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title="Vector Inspector API",
        version="1.0.0",
        description="API for interacting with providers, collections, items, and comparison operations.",
        routes=app.routes,
    )

    # Example vendor extension
    schema["x-vector-inspector"] = {
        "supportsComparison": True,
        "providers": ["pinecone", "qdrant", "chroma", "local"]
    }

    app.openapi_schema = schema
    return schema

app.openapi = custom_openapi
```

### Why Customize?

- Add richer examples for query and comparison endpoints  
- Provide metadata for SDK generators (TypeScript, Python, etc.)  
- Document provider capabilities or embedding model options  
- Improve discoverability for contributors  
- Support future versioning (e.g., `/v1`, `/v2`)  

### Notes for Contributors

- The OpenAPI schema is generated at runtime; do not manually edit `openapi.json`.
- If you add new routers or endpoints, they will automatically appear in the schema.
- If you modify the custom schema, ensure it remains valid OpenAPI 3.1.

This enables deeper integration with SDK generators and API tools.

---

## Implementation Steps Checklist

1. [ ] Add FastAPI and Uvicorn as dev dependencies  
2. [ ] Create `vector_inspector/api/` directory  
3. [ ] Implement routers  
4. [ ] Register routers in `server.py`  
5. [ ] Add CLI flags for server mode  
6. [ ] Implement endpoints using service/core layer  
7. [ ] Add error handling  
8. [ ] Add optional authentication  
9. [ ] Add tests  
10. [ ] Update documentation  