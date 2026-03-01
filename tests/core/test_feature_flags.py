"""Tests for the feature_flags module."""

import sys

import pytest

import vector_inspector.core.feature_flags as ff


@pytest.fixture(autouse=True)
def reset_flag():
    """Reset the global flag before each test."""
    ff._advanced_features_enabled = False
    yield
    ff._advanced_features_enabled = False


def test_initially_disabled():
    assert ff._advanced_features_enabled is False


def test_enable_advanced_features_sets_flag():
    ff.enable_advanced_features()
    assert ff._advanced_features_enabled is True


def test_are_advanced_features_enabled_after_enable():
    ff.enable_advanced_features()
    assert ff.are_advanced_features_enabled() is True


def test_are_advanced_features_enabled_when_disabled_no_studio(monkeypatch):
    """Returns False when flag is not set and vector_studio is not importable."""
    # Make sure vector_studio is not importable
    monkeypatch.setitem(sys.modules, "vector_studio", None)
    assert ff.are_advanced_features_enabled() is False


def test_are_advanced_features_enabled_when_studio_installed(monkeypatch):
    """Returns True when vector_studio can be imported even if flag not set."""
    import types

    fake_studio = types.ModuleType("vector_studio")
    monkeypatch.setitem(sys.modules, "vector_studio", fake_studio)
    assert ff.are_advanced_features_enabled() is True


def test_get_feature_tooltip_default():
    tooltip = ff.get_feature_tooltip()
    assert "Vector Studio" in tooltip
    assert "Advanced options" in tooltip


def test_get_feature_tooltip_custom_name():
    tooltip = ff.get_feature_tooltip("My Feature")
    assert "My Feature" in tooltip
    assert "Vector Studio" in tooltip


def test_enable_then_check_without_studio(monkeypatch):
    """Once enabled the module-level flag short-circuits regardless of studio import."""
    monkeypatch.setitem(sys.modules, "vector_studio", None)
    ff.enable_advanced_features()
    assert ff.are_advanced_features_enabled() is True
