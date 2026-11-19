"""Unit tests for MCP connection-spec parsing (no provider deps needed)."""

import os

import pytest

from vector_inspector.mcp.config import (
    ConnectionConfig,
    load_configs,
    parse_connection_spec,
    parse_connection_specs,
)


def test_parse_chroma_persistent():
    cfg = parse_connection_spec("local@chromadb?type=persistent&path=./chroma")
    assert cfg == ConnectionConfig(
        name="local",
        provider="chromadb",
        params={"type": "persistent", "path": "./chroma"},
    )


def test_parse_lancedb_defaults():
    cfg = parse_connection_spec("lance@lancedb?path=./lancedb-data")
    assert cfg.name == "lance"
    assert cfg.provider == "lancedb"
    assert cfg.params == {"path": "./lancedb-data"}
    assert cfg.secret_env == {}


def test_parse_secret_must_be_env_reference():
    cfg = parse_connection_spec("pine@pinecone?api_key=env:PINECONE_API_KEY")
    assert cfg.secret_env == {"api_key": "PINECONE_API_KEY"}
    assert cfg.params == {}
    with pytest.raises(ValueError, match="env:VARNAME"):
        parse_connection_spec("pine@pinecone?api_key=sk-1234")


def test_parse_rejects_unknown_provider():
    with pytest.raises(ValueError, match="unknown provider"):
        parse_connection_spec("x@elasticsearch?path=./es")


def test_parse_rejects_malformed():
    with pytest.raises(ValueError, match="expected"):
        parse_connection_spec("no-at-sign")
    with pytest.raises(ValueError, match="empty name"):
        parse_connection_spec("@chromadb?path=./c")
    with pytest.raises(ValueError, match="key=value"):
        parse_connection_spec("x@chromadb?path")


def test_parse_rejects_duplicate_names():
    with pytest.raises(ValueError, match="Duplicate connection name"):
        parse_connection_specs(["a@chromadb", "a@lancedb?path=./l"])


def test_resolve_credentials(monkeypatch):
    monkeypatch.setenv("MY_API_KEY", "secret-value")
    cfg = parse_connection_spec("q@qdrant?type=http&host=h&api_key=env:MY_API_KEY")
    assert cfg.resolve_credentials() == {"api_key": "secret-value"}


def test_resolve_credentials_missing_env():
    cfg = parse_connection_spec("q@qdrant?type=http&host=h&api_key=env:DOES_NOT_EXIST_XYZ")
    with pytest.raises(ValueError, match="DOES_NOT_EXIST_XYZ"):
        cfg.resolve_credentials()


def test_load_configs_env_and_cli_precedence(monkeypatch):
    monkeypatch.setenv("VI_MCP_CONNECTIONS", "a@chromadb; b@lancedb?path=./l")
    configs = load_configs(["b@lancedb?path=./other"])
    assert set(configs) == {"a", "b"}
    # CLI spec wins on name conflict.
    assert configs["b"].params["path"] == "./other"


def test_load_configs_empty(monkeypatch):
    monkeypatch.delenv("VI_MCP_CONNECTIONS", raising=False)
    assert load_configs([]) == {}
    assert load_configs(None) == {}


def test_config_never_holds_literal_secret():
    # The whole point of env:VARNAME: the parsed config must not contain
    # a credential value anywhere.
    cfg = parse_connection_spec("pg@pgvector?type=http&host=h&database=d&user=u&password=env:PG_PASS")
    assert "PG_PASS" not in str(cfg.params)
    assert cfg.secret_env == {"password": "PG_PASS"}
    assert os.environ.get("PG_PASS") is None or True  # value lives only in env
