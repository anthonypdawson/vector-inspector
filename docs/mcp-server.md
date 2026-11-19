# Vector Inspector MCP Server

A Model Context Protocol server that exposes the Vector Inspector
provider layer as MCP tools over stdio. One server, one tool surface,
any supported vector database: ChromaDB, Qdrant, Pinecone, LanceDB,
pgvector, Weaviate, and Milvus (experimental).

Status: **spike** on the `feat/mcp-server-spike` branch. No PyPI
publish. The design, tool table, and decisions are in the PRD
(`~/workspace/your_files/vector-mcp-server-prd.md` in the author's
workspace; not in this repo).

## Install

```bash
pip install vector-inspector[mcp,chromadb,lancedb]
```

The `mcp` extra is the official MCP Python SDK v2 (`mcp>=2.0`) **plus
fastembed** (`fastembed>=0.7.4`) — the default embedding runtime, so
a bare MCP install embeds text out of the box with no torch.
Provider clients are opt-in extras, mirroring the app:
`chromadb`, `qdrant`, `pinecone`, `lancedb`, `pgvector`,
`weaviate`, `milvus`. The `embeddings` extra
(sentence-transformers + fastembed) is the desktop app's text-search
extra: install it to opt into the sentence-transformers runtime
(see "Text search and embeddings"). A provider whose client is not
installed reports as unavailable from `vi_list_providers` with the
exact extra to install — it never crashes the server.

```bash
# one-command launch, the way MCP servers are installed:
uvx --from vector-inspector[mcp,chromadb,lancedb] vector-inspector-mcp \
  --connection local@chromadb?type=persistent&path=./chroma \
  --connection lance@lancedb?path=./lancedb
```

## Configure

Connections are named with repeatable `--connection` specs, or in
the `VI_MCP_CONNECTIONS` environment variable (semicolon-separated
specs; `--connection` wins on name conflicts):

```
name@provider?key=value&key=value
```

Examples:

```
local@chromadb?type=persistent&path=./chroma
lance@lancedb?path=./lancedb-data
qdrant@qdrant?type=http&host=localhost&port=6333&api_key=env:QDRANT_API_KEY
pine@pinecone?api_key=env:PINECONE_API_KEY
pg@pgvector?type=http&host=localhost&port=5432&database=vdb&user=postgres&password=env:PG_PASS
```

Secrets are never written in a spec. A value of the form
`env:VARNAME` is resolved from the process environment at connect
time; a literal secret in a spec is refused outright (it would leak
into `ps` output and shell history). The server never writes
credentials anywhere.

Connections open **lazily on first use** and stay open for the
server's lifetime. Nothing connects at startup, so one bad
credential cannot kill the server at launch. `vi_connect` opens a
connection explicitly to surface errors early, but tools do not
require it. A failed connect is not cached — the next call retries.

## Host configuration

Claude Code (`.mcp.json` in your project, or `~/.claude.json`):

```json
{
  "mcpServers": {
    "vector-inspector": {
      "command": "uvx",
      "args": [
        "--from", "vector-inspector[mcp,chromadb,lancedb]",
        "vector-inspector-mcp",
        "--connection", "local@chromadb?type=persistent&path=./chroma",
        "--connection", "lance@lancedb?path=./lancedb"
      ]
    }
  }
}
```

Claude Desktop (`claude_desktop_config.json`) uses the same
`mcpServers` block. For Cursor, the same block goes in
`.cursor/mcp.json`.

> Snippet status: the shape above follows the standard MCP host
> config format. It has **not** yet been verified by pasting it into
> Claude Code and listing the tools — that is success criterion 4 in
> the PRD and is still open for the spike.

## Tools

All tools take a `connection` name. Tool results are JSON text.

| Tool | What it does |
|---|---|
| `vi_list_providers` | Supported providers and whether each client library is installed. |
| `vi_connect` | Open a named connection (or confirm it is open). Never returns credentials. |
| `vi_list_collections` | Collection names on a connection. |
| `vi_collection_info` | Schema, vector size, distance, item count, supported filter operators. |
| `vi_search` | Search by text (embedded server-side) or raw vectors, with metadata filters. |
| `vi_get_items` | Fetch by id, or page through a collection (limit default 50, capped at 100). |
| `vi_add_items` | Add documents / metadata / ids / embeddings. |
| `vi_update_items` | Update items by id. |
| `vi_delete_items` | Delete by id or metadata filter (requires one — never deletes blindly). |
| `vi_create_collection` | Create a collection (vector size + distance). |
| `vi_delete_collection` | Delete a whole collection. |
| `vi_connection_info` | Provider and connected state. Never includes credentials. |

Mutating tools (`vi_add_items`, `vi_update_items`,
`vi_delete_items`, `vi_create_collection`, `vi_delete_collection`)
are blocked with a clear error when the server runs with
`--read-only`.

## Filter syntax: provider-native, passed raw

`vi_search` (and `vi_delete_items`) take `where` / `where_document`
as a dict and pass it straight to the provider — the server does
not normalize, validate, or translate filters. Each provider has
its own syntax (read from the connection code, Nov 2026):

- **ChromaDB** — Mongo-style, passed to the client as-is:
  `{"group": {"$eq": "a"}}`, `{"$and": [...]}`, `$or`, `$gt`,
  `$gte`, `$lt`, `$lte`, `$in`, `$nin`. `where_document`:
  `{"$contains": "text"}`. (Verified by the spike's tool tests.)
- **Qdrant** — Mongo-style dict, translated by the repo's
  `build_filter` helper into a Qdrant `Filter`:
  `{"group": {"$eq": "a"}}`.
- **Pinecone** — Mongo-style metadata filter:
  `{"group": {"$eq": "a"}}`.
- **LanceDB** — `where` is accepted but **currently ignored by
  `query_collection`** (the query body never applies it). Do not
  rely on server-side filtering for LanceDB in this spike.
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

A bad filter surfaces the provider's error verbatim as the tool
error. `vi_collection_info` returns each provider's supported
operator list (`get_supported_filter_operators`) so an agent can
check before filtering.

## Text search and embeddings

`vi_search` takes `query_texts` (embedded server-side) or
`query_embeddings` (raw vectors) — exactly one of the two. The
embedding path reuses the app's existing layer. The default model
is `all-MiniLM-L6-v2` (384 dims) via **fastembed**
(`vector-inspector[mcp]` includes it), the ONNX runtime — no torch
install, so a bare `uvx vector-inspector-mcp` embeds text out of
the box. Same model and dimension as the old sentence-transformers
default, so existing collections keep working.

Resolution order for both add and search, per collection:

1. An explicitly recorded model (desktop app: embedding settings
   for the collection, saved in SettingsService).
2. Dimension lookup: the registry maps the collection's vector
   dimension to a model — 384 dims resolves to
   `all-MiniLM-L6-v2` via sentence-transformers *when that library
   is installed*. When it is not installed, the lookup falls back
   to the fastembed default, but only when the dimensions match
   (a 512-dim CLIP collection never silently gets 384-dim
   vectors; it errors instead).
3. The fastembed default (`DEFAULT_MODEL`).

So in a bare MCP install everything resolves to fastembed, and in
the desktop app with sentence-transformers installed, 384-dim
collections keep using the sentence-transformers runtime — same
model, same dimensions, same results.

- **Opt into sentence-transformers**: install
  `vector-inspector[embeddings]` (which also includes fastembed).
  With it installed, the dimension lookup uses it for 384-dim
  collections, as before. To force a specific runtime for one
  collection, record it in the desktop app's embedding settings
  for that collection.
- **No model at all**: `vi_search` with `query_texts` fails with a
  clear error telling the agent to install fastembed
  (`pip install vector-inspector[mcp]`) or pass `query_embeddings`
  instead — it never silently falls back to a different model.
- **LanceDB caveat**: `add_items` never computes embeddings for
  LanceDB — a text-only add stores zero vectors and "succeeds", so
  search over such a collection returns all-tied distances and
  meaningless ranking. Add explicit embeddings for LanceDB, or use
  Chroma, until that is fixed.

## Safety

- **Telemetry is forced off** in the server process: the CLI sets
  `VI_NO_TELEMETRY=1`, and server startup additionally neutralises
  `TelemetryService.send_event` in-process. This is necessary
  because the telemetry service defaults to enabled when its
  setting is unset, and the env var alone does not cover the
  `log_tracked_error` path the provider layer uses. The patch is
  process-local and touches no user settings.
- **ONNX Runtime telemetry is off by default**: the CLI sets
  `ORT_DISABLE_TELEMETRY=1` before any ONNX Runtime import, and
  the FastEmbed provider does the same before importing fastembed.
  ONNX Runtime 1.29+ ships telemetry ON by default on Linux and
  POSTs trace events (including a persistent device ID, launch
  path, and model names) to Microsoft's 1DS backend
  (`mobile.events.data.microsoft.com`). The library's own
  `disable_telemetry_events()` does not stop it, and it ignores
  `DO_NOT_TRACK`. The env var must be set **before launch** — it
  is read when ONNX Runtime initializes. To opt back in, set
  `ORT_DISABLE_TELEMETRY=0` before launching the server; the CLI
  and provider both respect an explicit setting and never override
  it.
- **`--read-only`** blocks all five mutating tools.
- **`vi_get_items` pages with a capped limit** (default 50, max
  100) — no unbounded collection dumps into an agent's context.
- **No secrets in tool output**: connection info and errors are
  stripped of `api_key` / `password` / `token` / `secret` keys.
- **stdout is the protocol wire**: the server never `print()`s
  while serving; logging goes to stderr. (Note: one provider
  module, `lancedb_connection`, still has a `print()` on a failure
  path; the MCP SDK diverts flushed stdout to stderr while serving,
  so the wire is protected — see the spike's Inspector
  verification notes.)

## Tests

```bash
# Qt-free venv (no PySide6): the MCP tests only.
pytest tests/test_mcp_config.py tests/test_mcp_import_no_qt.py tests/test_mcp_server.py \
  --noconftest -o addopts=""

# Full dev env (with PySide6 + provider extras): runs under the
# repo's conftest like everything else.
pytest tests/test_mcp_config.py tests/test_mcp_import_no_qt.py tests/test_mcp_server.py
```

- `test_mcp_import_no_qt.py` — the gate test, kept permanently: the
  provider layer and the MCP server import in a subprocess with
  PySide6 blocked, and the server lists exactly the 12 `vi_*` tools.
- `test_mcp_server.py` — every tool's result shape plus one
  realistic failure each, against local Chroma (persistent) and
  LanceDB fixtures, through real MCP dispatch (`server.call_tool`).
  No test needs cloud credentials.
- `test_mcp_config.py` — connection-spec parsing, including the
  refusal of literal secrets.

## What changed to get Qt-free imports (spike)

Two files, lazy/deferred imports only — no provider code changed,
no abstraction rewritten:

- `src/vector_inspector/services/__init__.py` — names now resolve
  lazily (PEP 562 `__getattr__`). Importing the package no longer
  pulls in `task_runner`, which subclasses `QThread` at module
  level. `from vector_inspector.services import TaskRunner` behaves
  exactly as before when PySide6 is installed.
- `src/vector_inspector/services/settings_service.py` — the
  module-level `PySide6.QtCore` import (used only for a
  settings-changed signal emitter the UI consumes) is deferred into
  `SettingsService.__init__`, with a no-op `_NullSignals` fallback
  when Qt is unavailable.
