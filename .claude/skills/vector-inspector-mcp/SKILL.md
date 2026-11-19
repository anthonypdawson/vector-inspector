---
name: vector-inspector-mcp
description: Work with vector databases (ChromaDB, Qdrant, Pinecone, LanceDB, pgvector, Weaviate, Milvus) through the Vector Inspector MCP server — start it, connect, create collections, add/search/get items, and filter with provider-native syntax. Use when the user asks to inspect, search, or manage a vector database via MCP, or when a task needs embeddings or similarity search over one of these providers.
---

# Vector Inspector MCP Server

One MCP tool surface (`vi_*`, stdio) over seven vector databases.
Full reference: `docs/mcp-server.md`. The server is a **spike** on
branch `feat/mcp-server-spike` — **not published to PyPI yet**, so
`uvx` install does not work until the first publish; run it from a
repo checkout (below).

## Starting the server

From a checkout (until PyPI publish):

```bash
pip install -e ".[mcp,chromadb,lancedb]"   # mcp extra + the providers you use
vector-inspector-mcp \
  --connection local@chromadb?type=persistent&path=./chroma \
  --connection lance@lancedb?path=./lancedb
# or: python -m vector_inspector.mcp --connection ...
```

Once published, the one-command form is:

```bash
uvx --from vector-inspector[mcp,chromadb,lancedb] vector-inspector-mcp \
  --connection local@chromadb?type=persistent&path=./chroma
```

Claude Code (`.mcp.json` in the project root):

```json
{
  "mcpServers": {
    "vector-inspector": {
      "command": "vector-inspector-mcp",
      "args": [
        "--connection", "local@chromadb?type=persistent&path=./chroma",
        "--connection", "lance@lancedb?path=./lancedb"
      ]
    }
  }
}
```

Connections are named specs: `name@provider?key=value&key=value`,
repeatable `--connection`, or semicolon-separated in
`VI_MCP_CONNECTIONS` (`--connection` wins on name conflicts).
Connections saved in the desktop GUI are also loaded
automatically from `~/.vector-inspector/profiles.json`, and a
profile saved in the GUI mid-session is usable without
restarting. A launch spec wins when it shares a profile's name.
Connections open **lazily on first use** and stay open for the
server lifetime.

**Secrets are env-first, keychain-second.** In a launch spec a
value of the form `env:VARNAME` is resolved from the process
environment at connect time. A GUI profile's credential is checked
against its well-known environment variable first
(`PINECONE_API_KEY`, `QDRANT_API_KEY`, `WEAVIATE_API_KEY`,
`PGPASSWORD`), then the OS keychain entry the GUI wrote. A literal
secret in a spec is refused outright (it would leak into `ps`
output and shell history). The server never writes credentials
anywhere, and tool output never includes them.

Other flags: `--read-only` (below), `--log-level` (default
`WARNING`, logs to stderr — stdout is the MCP protocol wire).

## Tools (13)

All tools take a `connection` name, except `vi_list_providers` and
`vi_list_connections`. Results are JSON text.

| Tool | Args | What it does |
|---|---|---|
| `vi_list_providers` | — | Supported providers and whether each client library is installed. |
| `vi_list_connections` | — | Every connection available (launch specs + GUI profiles): name, provider, source, credential fields, connected state. |
| `vi_connect` | `connection` | Open a named connection (or confirm it is already open). |
| `vi_list_collections` | `connection` | Collection names on a connection. |
| `vi_collection_info` | `connection`, `collection` | Schema, vector size, distance, item count, supported filter operators. |
| `vi_search` | `connection`, `collection`, `query_texts` **or** `query_embeddings`, `n_results` (default 10), `where`, `where_document` | Search by text (embedded server-side) or raw vectors. Exactly one of `query_texts` / `query_embeddings`. |
| `vi_get_items` | `connection`, `collection`, `ids`, `limit` (default 50, capped at 100), `offset` | Fetch by id, or page through a collection. No `where` param. |
| `vi_add_items` | `connection`, `collection`, `documents`, `metadatas`, `ids`, `embeddings` | Add items. Documents are embedded server-side when no `embeddings` are given. |
| `vi_update_items` | `connection`, `collection`, `ids`, `documents`, `metadatas`, `embeddings` | Update items by id. |
| `vi_delete_items` | `connection`, `collection`, `ids`, `where` | Delete by id or metadata filter. Requires one — never deletes blindly. |
| `vi_create_collection` | `connection`, `collection`, `vector_size`, `distance` (default `"Cosine"`) | Create a collection. |
| `vi_delete_collection` | `connection`, `collection` | Delete a whole collection. Destructive. |
| `vi_connection_info` | `connection` | Provider and connected state. Never includes credentials. |

## Workflow

1. `vi_list_connections` — see what is available and switch
   between connections; every other tool takes the connection
   name per call.
2. `vi_list_providers` — confirm the provider's client is
   installed (unavailable providers report the exact extra to
   install; the server never crashes on a missing client).
3. `vi_connect` — optional health check; any tool opens its
   connection lazily anyway.
4. `vi_create_collection` with the collection's `vector_size`
   (must match the embedding dimension — 384 for the default
   model, below).
5. `vi_add_items` in batches (hundreds of documents per call, not
   thousands). Pass `embeddings` only when you already have
   vectors; otherwise documents are embedded server-side.
6. `vi_search` with `query_texts`, then `vi_get_items` by id for
   full records. Page large collections with `vi_get_items`
   (`limit`/`offset`), never in one call.

## Embeddings (text search)

The default model is `all-MiniLM-L6-v2` (384 dims) via
**fastembed** (ONNX, no torch). `vector-inspector[mcp]`
includes fastembed, so a bare MCP install embeds text out of the
box. Same model and dimension as the old sentence-transformers
default, so existing collections keep working.

Resolution order, per collection: (1) an explicitly recorded model
(desktop app: embedding settings for the collection); (2)
dimension lookup — 384 dims resolves to `all-MiniLM-L6-v2` via
sentence-transformers **when that library is installed**; when it
is not installed the lookup falls back to the fastembed default,
but only when the dimensions match (a 512-dim CLIP collection
never silently gets 384-dim vectors — it errors instead);
(3) the fastembed default.

- **Opt into sentence-transformers**: install
  `vector-inspector[embeddings]` (sentence-transformers +
  fastembed). With it installed, the dimension lookup uses it for
  384-dim collections, as before.
- **No model at all**: `vi_search` with `query_texts` fails with a
  clear error ("install fastembed … or pass `query_embeddings`
  instead") — it never silently falls back to a different model.
  Passing `query_embeddings` (raw vectors) always works with no
  model installed.
- **Text-only add embeds**: `add_items` with documents and no
  embeddings computes them with the configured model for the
  collection (LanceDB and Milvus included — they used to store zero
  vectors). If embedding fails, or the computed dimension does not
  match the collection, the add fails loudly instead of storing
  unsearchable data.

## Filter syntax: provider-native, passed raw

`vi_search` and `vi_delete_items` take `where` / `where_document`
as a dict and pass it straight to the provider — the server does
not normalize, validate, or translate filters. Never invent
syntax: read it from the connection code (or `docs/mcp-server.md`,
which did), and check `vi_collection_info`'s operator list first.
A bad filter surfaces the provider's error verbatim.

- **ChromaDB** — Mongo-style, passed to the client as-is:
  `{"group": {"$eq": "a"}}`, `{"$and": [...]}`, `$or`, `$gt`,
  `$gte`, `$lt`, `$lte`, `$in`, `$nin`. `where_document`:
  `{"$contains": "text"}`.
- **Qdrant** — Mongo-style dict, translated by the repo's
  `build_filter` helper into a Qdrant `Filter`:
  `{"group": {"$eq": "a"}}`.
- **Pinecone** — Mongo-style metadata filter:
  `{"group": {"$eq": "a"}}`.
- **LanceDB** — `where` is accepted but **currently ignored by
  `query_collection`** (the query body never applies it). Do not
  rely on server-side filtering for LanceDB.
- **pgvector** — dict of column:value pairs, translated to SQL
  equality (`WHERE "group" = 'a'`). `where_document` is not
  implemented.
- **Weaviate** — `{"field": value}` for equality, or
  `{"field": {"$eq"/"$ne"/"$gt"/"$gte"/"$lt"/"$lte"/"$in": value}}`;
  multiple fields are combined with AND.
- **Milvus** — dict translated to a Milvus filter expression on the
  `metadata` field: `{"group": "a"}` becomes
  `metadata["group"] == "a"`; multiple entries are joined with `&&`.
  Equality only.

## Read-only mode

`--read-only` blocks all five mutating tools with a clear error:
`vi_add_items`, `vi_update_items`, `vi_delete_items`,
`vi_create_collection`, `vi_delete_collection`. Reads
(`vi_search`, `vi_get_items`, `vi_list_*`, `vi_*_info`,
`vi_connect`) still work. Restart without `--read-only` to allow
writes. `vi_delete_items` always requires `ids` or `where`;
`vi_delete_collection` is destructive in either mode.

## Telemetry (privacy)

- **App telemetry is forced off** in the server process: the CLI
  sets `VI_NO_TELEMETRY=1` and startup neutralises
  `TelemetryService.send_event` in-process.
- **ONNX Runtime telemetry is off by default**: the CLI sets
  `ORT_DISABLE_TELEMETRY=1` before any ONNX Runtime import, and
  the FastEmbed provider does the same before importing fastembed.
  ONNX Runtime 1.29+ ships telemetry ON by default on Linux and
  POSTs trace events (including a persistent device ID, launch
  path, and model names) to Microsoft's 1DS backend
  (`mobile.events.data.microsoft.com`). The library's own
  `disable_telemetry_events()` does not stop it, and it ignores
  `DO_NOT_TRACK`. The variable must be set **before launch** — it
  is read when ONNX Runtime initializes. To opt back in, set
  `ORT_DISABLE_TELEMETRY=0` before launching; the CLI and the
  provider respect an explicit setting and never override it.
