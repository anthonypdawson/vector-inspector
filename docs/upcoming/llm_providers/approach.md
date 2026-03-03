---
title: LLM Providers — Consolidated Design
---

# LLM Providers — Consolidated Design

This document captures the recommendations for the `llm-providers` branch: a minimal, consistent provider interface, a model manager separation, normalized errors and capabilities, and a deterministic, debuggable runtime.

Purpose: provide a single, well-documented provider layer for Vector Inspector / Vector Studio that is pluggable, testable, and consistent across local (llama-cpp), self-hosted (Ollama), and cloud (OpenAI-compatible) providers.

Audience: maintainers of `src/**` provider code, Vector Studio integration engineers, and UI authors.

---

## Quickstart (short)

See `docs/llm_providers/quickstart.md` for full examples. Example selection environment variables:

- `VI_LLM_PROVIDER` — preferred provider id (`llama-cpp`, `ollama`, `openai`).
- `VI_LLM_MODEL` — default model name.
- `VI_OLLAMA_URL` — Ollama endpoint (e.g., `http://localhost:11434`).

Enable debug selection with `VI_LLM_DEBUG=1`.

---

## Design Principles

- Keep the provider layer narrowly scoped to text generation and model metadata.
- Separate provider lifecycle and selection from model file management and caching.
- Normalize surface area: capabilities, health checks, a unified `generate()` signature, and a streaming contract.
- Treat optional deps (e.g., `llama-cpp`) as feature flags with runtime checks and clear warnings.

---

## Responsibility Matrix

Who owns what (high-level):

- Runtime Manager: provider selection, `selection_debug`, global retries and circuit-breaking orchestration, traffic shaping/rate-limiting orchestration, provider instance lifecycle.
- Provider: transport-level retries, error normalization, per-request timeouts, connection/session management.
- Model Manager: model artifact lifecycle (download, verify, eviction), per-model locks, capacity-aware loading.
- Pipeline / UI: high-level retry policies, user-facing fallbacks, budget/cost decisions.

This table is authoritative: implement behavior in code and update docs when changing responsibilities.

---

## Provider Interface (canonical)

Provide a minimal provider API surface so upper layers do not need provider-specific logic.

- `generate(messages, model, stream=False, **kwargs)` — single canonical call for completions/chat.
- `stream(messages, model, **kwargs)` — returns an async iterator or sync generator per runtime.
- `models()` — list available models + metadata.
- `capabilities()` — `ProviderCapabilities` object describing streaming, max context, tokenizer info, roles, concurrency.
- `health()` — lightweight probe of connectivity and model availability.

Keep the interface small so consumers only rely on stable, well-tested primitives.

### Concrete `generate()` example

```python
resp = provider.generate(
    messages=[{"role": "user", "content": "Explain vector search"}],
    model="llama-3.1",
    stream=False,
    temperature=0.2,
)
```

If `stream=True`, the caller receives an iterator (sync or async depending on runtime) that yields normalized streaming events.

---

## Provider vs Model

- Provider identity: the runtime integration (llama-cpp process, Ollama HTTP endpoint, OpenAI-compatible HTTP).
- Model identity: a model artifact available through a provider (e.g., `ggml-vicuna-13b-q4_0`).

Providers should expose available models via `models()` and include per-model metadata such as `context_window`, tokenizer hints, optional `rate_limit` and `cost_estimate_per_token`. Keep provider logic focused on runtime behavior and model metadata, and move artifact lifecycle (download, cache, verify) to the model manager.

Do not conflate provider selection with model artifact management; this separation keeps providers lightweight and easier to test.


## Capabilities Schema

Include a small, versioned capabilities object so the UI/runtime can adapt safely when schema evolves.

Suggested `ProviderCapabilities` fields:
- `schema_version: str`
- `provider_name: str`
- `supports_streaming: bool`
- `supports_tools: bool` — supports tool invocation / JSON mode
- `concurrency: str` — `"single-threaded" | "multi" | "process-isolated"`
- `max_context_tokens: int`
- `roles_supported: list[str]` (e.g. `["system","user","assistant"]`)
- `model_list: list[ModelMetadata]`
- `tokenizer: TokenizerInfo | None`

`ModelMetadata` should include `model_name`, `context_window`, optional `rate_limit`, and `cost_estimate_per_token` when available.

### TokenizerInfo

Provide a small tokenizer adapter returning:
- encoding name
- a `count_tokens(messages)` helper
- encode/decode hooks (optional)

This lets RAG and UI reliably budget token usage across providers.

---

## Streaming & Error Model

Standardize streaming event shape and error normalization so consumers can be provider-agnostic.

Canonical event shape (recommended):

```json
{ "type": "delta" | "done" | "error", "content": "...", "meta": { ... } }
```

- Make `delta` the canonical stream type for incremental text fragments; `token` is optional for providers emitting discrete tokens.
- `meta` MUST include `request_id` or `trace_id` for log correlation and may include `timestamp` and `index`/`seq` for ordering.

Example event sequence:

```json
{ "type": "delta", "content": "vec", "meta": {"request_id": "r-123", "index": 0} }
{ "type": "delta", "content": "tor", "meta": {"request_id": "r-123", "index": 1} }
{ "type": "done",  "content": "",    "meta": {"request_id": "r-123", "finish_reason": "stop"} }
```

Error normalization:
- All provider exceptions must be normalized to a `ProviderError` hierarchy with fields: `provider_name`, `model_name`, `underlying_error`, `retryable: bool`, `code`/`http_status`, and `remediation_hint`.

Include short `remediation_hint` strings and `retryable` booleans to help runtime manager and UI make consistent decisions.

---

## Lifecycle & Concurrency

Clarify provider lifetime and state expectations to avoid ambiguity:

- Long‑lived singletons: providers are expected to be long‑lived instances managed by the runtime manager in most cases. This allows providers to maintain internal state such as HTTP sessions, cached auth tokens, and connection pools.
- Recreated per request: only allowed for lightweight providers where construction is cheap; avoid per-request recreation for providers that manage native resources.
- Internal state: providers MAY maintain internal state but MUST document thread-safety guarantees and expose a `close()`/`shutdown()` method when applicable.

Runtime manager behavior: the runtime manager decides whether to reuse or recreate providers; implementations should assume providers are reusable unless explicitly documented otherwise. Surface `concurrency` in `capabilities()` so the runtime knows whether to serialize requests or allow concurrent calls.

Model manager locking: provide per-model locks to ensure only one load/eviction operation occurs concurrently for a model.

Provider-specific concurrency notes (example):
- `llama-cpp` may be single-threaded or process-isolated depending on build — document this in the provider implementation and capabilities.

---

## Runtime Manager: Selection & Health

Discovery precedence (deterministic):
1. Explicit application config (highest precedence)
2. Environment variables (`VI_LLM_PROVIDER`, `VI_LLM_MODEL`, `VI_OLLAMA_URL`)
3. Auto-detection (reachable endpoints, local runtime availability)
4. Fallback default (e.g., `openai` when API key present)

Structured selection reason schema (example):

```json
{
  "source": "env", "key": "VI_LLM_PROVIDER", "value": "ollama",
  "timestamp": "2026-03-03T12:00:00Z", "precedence_rank": 1
}
```

`selection_debug` SHOULD contain a small structured object like the above (or an array of candidate reasons) so humans and machines can parse the decision path. Redact secrets.

Health checks:
- `health()` should be fast and predictable; runtime manager may expose cached `health()` and an active `probe()` for on-demand checks.
- Suggested `health()` return shape includes `ok`, `provider`, `models`, `version`, `last_checked`, `retryable`.

---

## Provider Factory vs Runtime Manager

- Factory: the provider factory should be pure and side-effect-free. Its job is to map configuration and discovery inputs to a provider descriptor or class without performing I/O or starting network/native resources.
- Runtime Manager: the runtime manager owns stateful concerns — creating, caching, and tearing down provider instances, performing health polling, credential refresh, and selection debugging. It should also own deterministic provider selection and record a structured `selection_debug` explaining why a provider and model were chosen (env, config, autodetect, fallback).

Include a machine-parseable `selection_debug` entry that records the exact decision path (which env var or config key, auto-detect result, fallback), the timestamp, and the precedence rank. Redact secrets but keep non-sensitive values.


## Model Manager (responsibilities)

- Download and verify model artifacts
- Maintain filesystem layout and consistent paths
- LRU eviction / disk-space policy
- Per-model locks for concurrent load/preload
- Provide preloaded model handles to in-process providers (llama-cpp)
- Expose metrics (load time, size, last_used)

Model manager responsibilities are intentionally separate from providers to avoid mixing artifact lifecycle with runtime integration.

---

## Optional Dependencies & Runtime Checks

- Keep heavy LLM runtime dependencies optional and grouped under an `llm` extras group in packaging.
- Runtime manager must perform runtime checks: if a provider is selected but required optional dependencies are missing (for example selecting `llama-cpp` without the native bindings installed), do not crash the process. Instead:
    - mark the provider `health().ok == false`
    - include a `remediation_hint` in the health output (e.g., install instructions or link to docs)
    - record the issue in `selection_debug` so the user can see why selection failed and what remediation is suggested

Example: when `VI_LLM_PROVIDER=llama-cpp` but `llama-cpp` bindings are not importable, runtime manager logs a structured message and returns a helpful `health()` response rather than raising an uncaught ImportError.


## Fake Provider (tests & demos)

See `docs/llm_providers/fake_provider.md` for full spec. Summary:
- Modes: `echo`, `streaming`, `error_inject`
- Config: `seed`, `fragment_size`, `latency_ms`, `error_rate`, `default_model`
- Implements `generate()`, `stream()`, `models()`, `capabilities()`, `health()` so CI can run without external deps.

Use the fake provider to validate runtime manager selection, retry behavior, and streaming conformance in CI.

---

## Migration & Testing

Migration shim (recommended while rolling out):

```python
def legacy_generate(provider, prompt: str, **kwargs):
    messages = [{"role": "user", "content": prompt}]
    model = kwargs.pop("model", None) or provider.default_model()
    return provider.generate(messages=messages, model=model, **kwargs)
```

Tests to add:
- capabilities schema conformance
- streaming iterator conformance across providers (mocked)
- model manager locking / eviction tests
- provider factory deterministic selection tests
- shim mapping tests and backward-compat smoke tests

---

## Quick Example (python dataclasses)

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class TokenizerInfo:
    encoding: str
    def count_tokens(self, texts: List[str]) -> int: ...

@dataclass
class ModelMetadata:
    model_name: str
    context_window: int
    cost_estimate_per_1k: Optional[float] = None

@dataclass
class ProviderCapabilities:
    schema_version: str
    provider_name: str
    supports_streaming: bool
    supports_tools: bool
    concurrency: str
    max_context_tokens: int
    roles_supported: List[str]
    model_list: List[ModelMetadata]
    tokenizer: Optional[TokenizerInfo]
```

---

## Next Steps / Checklist

1. Implement `ProviderCapabilities` dataclass and tests.
2. Add model manager module and simple LRU eviction implementation.
3. Implement streaming event type and cross-provider conformance tests.
4. Add runtime manager selection debug logging and `--llm-dry-run` CLI.
5. Implement `tests/utils/fake_provider.py` and CI tests using it.

---

Links:
- Quickstart: `docs/llm_providers/quickstart.md`
- Fake provider spec: `docs/llm_providers/fake_provider.md`
