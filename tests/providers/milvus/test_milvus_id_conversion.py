import pytest

pytest.importorskip("pymilvus")

from vector_inspector.core.connections.milvus_connection import MilvusConnection


def test_to_milvus_id_integer():
    assert MilvusConnection._to_milvus_id(42) == 42


def test_to_milvus_id_numeric_string():
    assert MilvusConnection._to_milvus_id("99") == 99


def test_to_milvus_id_negative_numeric_string():
    assert MilvusConnection._to_milvus_id("-5") == -5


def test_to_milvus_id_non_numeric_string_is_deterministic():
    result1 = MilvusConnection._to_milvus_id("some-uuid-like-string")
    result2 = MilvusConnection._to_milvus_id("some-uuid-like-string")
    assert result1 == result2
    assert isinstance(result1, int)
    assert result1 > 0


def test_to_milvus_id_different_strings_produce_different_ids():
    assert MilvusConnection._to_milvus_id("abc") != MilvusConnection._to_milvus_id("xyz")
