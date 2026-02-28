"""Tests for the UpdateService."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from vector_inspector.services.update_service import UpdateService


@pytest.fixture(autouse=True)
def no_cache_file(tmp_path, monkeypatch):
    """Redirect the cache file to a temp location so tests don't pollute the real system."""
    cache = str(tmp_path / "update_cache.json")
    monkeypatch.setattr("vector_inspector.services.update_service.CACHE_FILE", cache)
    yield cache


class TestCompareVersions:
    def test_newer_version_returns_true(self):
        assert UpdateService.compare_versions("0.1.0", "0.2.0") is True

    def test_same_version_returns_false(self):
        assert UpdateService.compare_versions("1.0.0", "1.0.0") is False

    def test_older_version_returns_false(self):
        assert UpdateService.compare_versions("2.0.0", "1.9.9") is False

    def test_v_prefix_stripped(self):
        assert UpdateService.compare_versions("v1.0.0", "v1.0.1") is True

    def test_patch_bump(self):
        assert UpdateService.compare_versions("1.2.3", "1.2.4") is True


class TestGetUpdateInstructions:
    def test_returns_pip_and_github(self):
        instructions = UpdateService.get_update_instructions()
        assert "pip" in instructions
        assert "github" in instructions
        assert "vector-inspector" in instructions["pip"]
        assert "github.com" in instructions["github"]


class TestGetLatestRelease:
    def test_returns_none_on_request_exception(self):
        with patch("vector_inspector.services.update_service.requests.get") as mock_get:
            mock_get.side_effect = Exception("network error")
            result = UpdateService.get_latest_release()
            assert result is None

    def test_returns_release_on_200(self, no_cache_file):
        fake_release = {"tag_name": "v1.2.3", "name": "Release 1.2.3"}
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_release

        with patch("vector_inspector.services.update_service.requests.get", return_value=mock_resp):
            result = UpdateService.get_latest_release()
        assert result == fake_release

    def test_returns_none_on_403_rate_limit(self, no_cache_file):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.headers = {"X-RateLimit-Reset": str(int(time.time()) + 3600)}

        with patch("vector_inspector.services.update_service.requests.get", return_value=mock_resp):
            result = UpdateService.get_latest_release()
        assert result is None

    def test_rate_limit_respected_from_cache(self, no_cache_file):
        """If cache says we're rate limited, no network call should be made."""
        future_time = int(time.time()) + 10000
        with open(no_cache_file, "w") as f:
            json.dump({"rate_limited_until": future_time}, f)

        with patch("vector_inspector.services.update_service.requests.get") as mock_get:
            result = UpdateService.get_latest_release()
            mock_get.assert_not_called()
        assert result is None

    def test_returns_cached_release_within_ttl(self, no_cache_file):
        """If cache is fresh, should return cached release without network call."""
        fake_release = {"tag_name": "v0.9.9"}
        with open(no_cache_file, "w") as f:
            json.dump({"timestamp": int(time.time()), "release": fake_release}, f)

        with patch("vector_inspector.services.update_service.requests.get") as mock_get:
            result = UpdateService.get_latest_release()
            mock_get.assert_not_called()
        assert result == fake_release

    def test_force_refresh_ignores_cache(self, no_cache_file):
        """force_refresh=True should bypass TTL check."""
        fake_release = {"tag_name": "v2.0.0"}
        # Put stale-looking entry (timestamp near now so it's within TTL)
        with open(no_cache_file, "w") as f:
            json.dump({"timestamp": int(time.time()), "release": {"tag_name": "v1.0.0"}}, f)

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fake_release

        with patch("vector_inspector.services.update_service.requests.get", return_value=mock_resp):
            result = UpdateService.get_latest_release(force_refresh=True)
        assert result == fake_release

    def test_rate_limit_no_reset_header(self, no_cache_file):
        """403 without X-RateLimit-Reset header should default rate limit to 1 hour."""
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.headers = {}

        with patch("vector_inspector.services.update_service.requests.get", return_value=mock_resp):
            result = UpdateService.get_latest_release()
        assert result is None
        # Verify cache file was written with rate_limited_until
        with open(no_cache_file) as f:
            cache = json.load(f)
        assert "rate_limited_until" in cache
