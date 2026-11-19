"""Read the desktop GUI's saved connection profiles.

The GUI stores profiles in ``~/.vector-inspector/profiles.json`` —
one entry per saved connection with its name, provider, non-secret
config (host, port, path, ...), and the names of its credential
fields. The credential *values* live in the OS keychain, never in
this file (see :func:`vector_inspector.mcp.config.read_keychain_credentials`).

The MCP server reads this file (never writes it) so a connection
configured once in the GUI is usable here without duplicating it in
a launch spec. ``GuiProfiles.load`` re-reads only when the file's
mtime changes, so a profile saved in the GUI mid-session is picked
up by the next tool call — no server restart.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from vector_inspector.mcp.config import DEFAULT_ENV_VARS, SUPPORTED_PROVIDERS, ConnectionConfig

logger = logging.getLogger(__name__)

DEFAULT_PROFILES_PATH = Path.home() / ".vector-inspector" / "profiles.json"


class GuiProfiles:
    """GUI profiles file, with mtime caching."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else DEFAULT_PROFILES_PATH
        self._mtime: float | None = None
        self._configs: dict[str, ConnectionConfig] = {}

    def load(self) -> dict[str, ConnectionConfig]:
        """Return profile configs keyed by name.

        Returns the cached configs when the file has not changed,
        and an empty dict when the file does not exist (yet) or is
        unreadable. A profile is skipped (with a warning) when it
        has no name, an unknown provider, or no config.
        """
        try:
            mtime = self.path.stat().st_mtime
        except OSError:
            return {}
        if mtime == self._mtime:
            return self._configs
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.warning("Could not read GUI profiles from %s: %s", self.path, exc)
            return {}
        configs: dict[str, ConnectionConfig] = {}
        for profile in data.get("profiles", []) if isinstance(data, dict) else []:
            if not isinstance(profile, dict):
                continue
            name = profile.get("name")
            provider = profile.get("provider")
            config = profile.get("config")
            if not name or not provider or not isinstance(config, dict):
                logger.warning("Skipping malformed GUI profile: %r", profile.get("id") or profile.get("name"))
                continue
            if provider not in SUPPORTED_PROVIDERS:
                logger.warning("Skipping GUI profile %r: unknown provider %r", name, provider)
                continue
            if name in configs:
                logger.warning("Skipping GUI profile %r: duplicate name, keeping the first", name)
                continue
            credential_fields = tuple(profile.get("credential_fields") or [])
            secret_env = {
                field: DEFAULT_ENV_VARS[(provider, field)]
                for field in credential_fields
                if (provider, field) in DEFAULT_ENV_VARS
            }
            configs[name] = ConnectionConfig(
                name=name,
                provider=provider,
                params=dict(config),
                secret_env=secret_env,
                credential_fields=credential_fields,
                profile_id=profile.get("id"),
            )
        self._mtime = mtime
        self._configs = configs
        return configs


def load_profiles(path: str | Path | None = None) -> dict[str, ConnectionConfig]:
    """One-shot read of the GUI profiles file (no caching)."""
    return GuiProfiles(path).load()
