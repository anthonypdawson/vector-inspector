"""Named-connection configuration for the MCP server.

A connection is named on the command line (repeatable
``--connection``) or in the ``VI_MCP_CONNECTIONS`` environment
variable as a compact spec string::

    name@provider?key=value&key=value

Examples::

    local@chromadb?type=persistent&path=./chroma
    lance@lancedb?path=./lancedb-data
    qdrant@qdrant?type=http&host=localhost&port=6333&api_key=env:QDRANT_API_KEY
    pine@pinecone?api_key=env:PINECONE_API_KEY

Secrets are never written in a spec. A value of the form
``env:VARNAME`` is resolved from the process environment at connect
time; the spec only ever names the variable. The server never
persists credentials anywhere.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Parameter names treated as credentials: handed to
# ProviderFactory.create as ``credentials`` (never echoed back in
# tool output) and resolved from the environment when written as
# ``env:VARNAME``.
SECRET_PARAMS = frozenset({"api_key", "api_token", "password"})

# Provider name -> pip extra that provides its client, for the
# "not installed" hint in vi_list_providers.
PROVIDER_EXTRAS = {
    "chromadb": "chromadb",
    "qdrant": "qdrant",
    "pinecone": "pinecone",
    "lancedb": "lancedb",
    "pgvector": "pgvector",
    "weaviate": "weaviate",
    "milvus": "milvus",
}

SUPPORTED_PROVIDERS = tuple(PROVIDER_EXTRAS)


@dataclass(frozen=True)
class ConnectionConfig:
    """One named connection: provider plus its parameters.

    ``params`` are the non-secret ProviderFactory config values.
    ``secret_env`` maps a credential name (e.g. ``api_key``) to the
    environment variable it is resolved from at connect time.
    """

    name: str
    provider: str
    params: dict[str, str] = field(default_factory=dict)
    secret_env: dict[str, str] = field(default_factory=dict)

    def resolve_credentials(self) -> dict[str, str]:
        """Resolve credential values from the environment.

        Raises:
            ValueError: If a named environment variable is not set.
        """
        credentials: dict[str, str] = {}
        for key, var in self.secret_env.items():
            value = os.environ.get(var)
            if not value:
                raise ValueError(
                    f"Connection '{self.name}': environment variable '{var}' (for credential '{key}') is not set"
                )
            credentials[key] = value
        return credentials

    def factory_config(self) -> dict[str, str]:
        """Config dict passed to ProviderFactory.create."""
        return dict(self.params)


def parse_connection_spec(spec: str) -> ConnectionConfig:
    """Parse one ``name@provider?key=value&key=value`` spec string.

    Raises:
        ValueError: If the spec is malformed or the provider is unknown.
    """
    if "@" not in spec:
        raise ValueError(f"Invalid connection spec {spec!r}: expected 'name@provider?key=value&key=value'")
    name, rest = spec.split("@", 1)
    name = name.strip()
    if not name:
        raise ValueError(f"Invalid connection spec {spec!r}: empty name")
    if "?" in rest:
        provider, query = rest.split("?", 1)
    else:
        provider, query = rest, ""
    provider = provider.strip()
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"Invalid connection spec {spec!r}: unknown provider "
            f"'{provider}' (supported: {', '.join(SUPPORTED_PROVIDERS)})"
        )
    params: dict[str, str] = {}
    secret_env: dict[str, str] = {}
    if query:
        for pair in query.split("&"):
            if "=" not in pair:
                raise ValueError(f"Invalid connection spec {spec!r}: expected key=value in {pair!r}")
            key, value = pair.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                raise ValueError(f"Invalid connection spec {spec!r}: empty key in {pair!r}")
            if key in SECRET_PARAMS and value.startswith("env:"):
                secret_env[key] = value[4:]
            elif key in SECRET_PARAMS:
                # A literal secret in the spec would leak into `ps`
                # output and shell history. Refuse it outright.
                raise ValueError(
                    f"Invalid connection spec for '{name}': credential "
                    f"'{key}' must be given as env:VARNAME, never literally"
                )
            else:
                params[key] = value
    return ConnectionConfig(name=name, provider=provider, params=params, secret_env=secret_env)


def parse_connection_specs(specs: list[str]) -> dict[str, ConnectionConfig]:
    """Parse a list of spec strings into configs keyed by name.

    Raises:
        ValueError: On a malformed spec or a duplicate connection name.
    """
    configs: dict[str, ConnectionConfig] = {}
    for spec in specs:
        spec = spec.strip()
        if not spec:
            continue
        cfg = parse_connection_spec(spec)
        if cfg.name in configs:
            raise ValueError(f"Duplicate connection name: '{cfg.name}'")
        configs[cfg.name] = cfg
    return configs


def load_configs(cli_specs: list[str] | None = None) -> dict[str, ConnectionConfig]:
    """Load named connections from CLI specs and VI_MCP_CONNECTIONS.

    ``VI_MCP_CONNECTIONS`` holds semicolon-separated spec strings.
    CLI specs win on name conflicts.
    """
    env_specs = os.environ.get("VI_MCP_CONNECTIONS", "")
    configs = parse_connection_specs([s for s in env_specs.split(";") if s.strip()] if env_specs else [])
    if cli_specs:
        configs.update(parse_connection_specs(cli_specs))
    return configs
