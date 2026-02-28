import pytest

from vector_inspector.core.sample_data.text_generator import (
    SampleDataType,
    generate_sample_data,
)


def test_generate_deterministic_stability():
    a = generate_sample_data(20, randomize=False)
    b = generate_sample_data(20, randomize=False)
    assert a == b


def test_generate_large_count_smoke():
    items = generate_sample_data(10000, randomize=False)
    assert len(items) == 10000


# ---------------------------------------------------------------------------
# Text type (explicit enum / string alias)
# ---------------------------------------------------------------------------


def test_text_type_returns_correct_count():
    items = generate_sample_data(5, data_type=SampleDataType.TEXT, randomize=False)
    assert len(items) == 5


def test_text_items_have_required_keys():
    items = generate_sample_data(3, data_type=SampleDataType.TEXT, randomize=False)
    for item in items:
        assert "text" in item
        assert "metadata" in item
        assert item["metadata"]["type"] == "text"


def test_text_type_via_string_alias():
    items = generate_sample_data(3, data_type="text", randomize=False)
    assert len(items) == 3


# ---------------------------------------------------------------------------
# Markdown type
# ---------------------------------------------------------------------------


def test_markdown_type_returns_correct_count():
    items = generate_sample_data(5, data_type=SampleDataType.MARKDOWN, randomize=False)
    assert len(items) == 5


def test_markdown_items_start_with_heading():
    items = generate_sample_data(5, data_type=SampleDataType.MARKDOWN, randomize=False)
    for item in items:
        assert item["text"].startswith("## ")


def test_markdown_metadata_type():
    items = generate_sample_data(3, data_type=SampleDataType.MARKDOWN, randomize=False)
    for item in items:
        assert item["metadata"]["type"] == "markdown"
        assert "section" in item["metadata"]


def test_markdown_type_via_string_alias():
    items = generate_sample_data(3, data_type="markdown", randomize=False)
    assert len(items) == 3


# ---------------------------------------------------------------------------
# JSON type
# ---------------------------------------------------------------------------


def test_json_type_returns_correct_count():
    items = generate_sample_data(5, data_type=SampleDataType.JSON, randomize=False)
    assert len(items) == 5


def test_json_items_contain_title_prefix():
    items = generate_sample_data(5, data_type=SampleDataType.JSON, randomize=False)
    for item in items:
        assert "Title:" in item["text"]


def test_json_metadata_type():
    items = generate_sample_data(3, data_type=SampleDataType.JSON, randomize=False)
    for item in items:
        assert item["metadata"]["type"] == "json"
        assert "title" in item["metadata"]


def test_json_type_via_string_alias():
    items = generate_sample_data(3, data_type="json", randomize=False)
    assert len(items) == 3


# ---------------------------------------------------------------------------
# Randomized mode
# ---------------------------------------------------------------------------


def test_randomize_true_returns_items():
    items = generate_sample_data(10, randomize=True)
    assert len(items) == 10


def test_randomize_true_markdown():
    items = generate_sample_data(8, data_type=SampleDataType.MARKDOWN, randomize=True)
    assert len(items) == 8
    for item in items:
        assert "text" in item


def test_randomize_true_json():
    items = generate_sample_data(8, data_type=SampleDataType.JSON, randomize=True)
    assert len(items) == 8
    for item in items:
        assert "text" in item


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_invalid_string_type_raises():
    with pytest.raises(ValueError):
        generate_sample_data(5, data_type="invalid_type")
