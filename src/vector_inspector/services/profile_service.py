"""Service for managing connection profiles."""

import json
import uuid
from pathlib import Path
from typing import Any
from PySide6.QtCore import QObject, Signal
from vector_inspector.core.logging import log_error

from .credential_service import CredentialService


class ConnectionProfile:
    """Represents a saved connection profile."""

    def __init__(
        self,
        profile_id: str,
        name: str,
        provider: str,
        config: dict[str, Any],
        credential_fields: list[str] | None = None,
    ):
        """
        Initialize a connection profile.

        Args:
            profile_id: Unique profile identifier
            name: User-friendly profile name
            provider: Provider type (chromadb, qdrant, etc.)
            config: Non-sensitive configuration (host, port, path, etc.)
            credential_fields: List of field names that contain credentials
        """
        self.id = profile_id
        self.name = name
        self.provider = provider
        self.config = config
        self.credential_fields = credential_fields or []

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to dictionary (without credentials)."""
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "config": self.config,
            "credential_fields": self.credential_fields,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConnectionProfile":
        """Create profile from dictionary."""
        return cls(
            profile_id=data["id"],
            name=data["name"],
            provider=data["provider"],
            config=data.get("config", {}),
            credential_fields=data.get("credential_fields", []),
        )


class ProfileService(QObject):
    """Manages connection profiles and persistence.

    Signals:
        profile_added: Emitted when a profile is added (profile_id)
        profile_updated: Emitted when a profile is updated (profile_id)
        profile_deleted: Emitted when a profile is deleted (profile_id)
    """

    # Signals
    profile_added = Signal(str)  # profile_id
    profile_updated = Signal(str)  # profile_id
    profile_deleted = Signal(str)  # profile_id

    def __init__(self):
        """Initialize profile service."""
        super().__init__()
        self.profiles_dir = Path.home() / ".vector-inspector"
        self.profiles_file = self.profiles_dir / "profiles.json"
        self.credential_service = CredentialService()
        self._profiles: dict[str, ConnectionProfile] = {}
        self._last_active_connections: list[str] = []
        self._load_profiles()

    def _load_profiles(self):
        """Load profiles from disk."""
        try:
            if self.profiles_file.exists():
                with open(self.profiles_file, encoding="utf-8") as f:
                    data = json.load(f)

                    # Load profiles
                    for profile_data in data.get("profiles", []):
                        profile = ConnectionProfile.from_dict(profile_data)
                        self._profiles[profile.id] = profile

                    # Load last active connections
                    self._last_active_connections = data.get("last_active_connections", [])
        except Exception as e:
            log_error("Failed to load profiles: %s", e)
            self._profiles = {}
            self._last_active_connections = []

    def _save_profiles(self):
        """Save profiles to disk."""
        try:
            # Create directory if it doesn't exist
            self.profiles_dir.mkdir(parents=True, exist_ok=True)

            # Prepare data
            data = {
                "profiles": [profile.to_dict() for profile in self._profiles.values()],
                "last_active_connections": self._last_active_connections,
            }

            # Write to file
            with open(self.profiles_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_error("Failed to save profiles: %s", e)

    def create_profile(
        self,
        name: str,
        provider: str,
        config: dict[str, Any],
        credentials: dict[str, Any] | None = None,
    ) -> str:
        """
        Create a new connection profile.

        Args:
            name: Profile name
            provider: Provider type
            config: Connection configuration (non-sensitive)
            credentials: Credential data to store securely (optional)

        Returns:
            The profile ID
        """
        profile_id = str(uuid.uuid4())
        credential_fields = list(credentials.keys()) if credentials else []

        profile = ConnectionProfile(
            profile_id=profile_id,
            name=name,
            provider=provider,
            config=config,
            credential_fields=credential_fields,
        )

        self._profiles[profile_id] = profile

        # Store credentials if provided
        if credentials:
            self.credential_service.store_credentials(profile_id, credentials)

        self._save_profiles()
        self.profile_added.emit(profile_id)

        return profile_id

    def get_profile(self, profile_id: str) -> ConnectionProfile | None:
        """Get a profile by ID."""
        return self._profiles.get(profile_id)

    def get_all_profiles(self) -> list[ConnectionProfile]:
        """Get all saved profiles."""
        return list(self._profiles.values())

    def update_profile(
        self,
        profile_id: str,
        name: str | None = None,
        config: dict[str, Any] | None = None,
        credentials: dict[str, Any] | None = None,
    ) -> bool:
        """
        Update an existing profile.

        Args:
            profile_id: ID of profile to update
            name: New name (optional)
            config: New configuration (optional)
            credentials: New credentials (optional)

        Returns:
            True if successful, False if profile not found
        """
        profile = self._profiles.get(profile_id)
        if not profile:
            return False

        if name is not None:
            profile.name = name

        if config is not None:
            profile.config = config

        if credentials is not None:
            profile.credential_fields = list(credentials.keys())
            self.credential_service.store_credentials(profile_id, credentials)

        self._save_profiles()
        self.profile_updated.emit(profile_id)

        return True

    def delete_profile(self, profile_id: str) -> bool:
        """
        Delete a profile.

        Args:
            profile_id: ID of profile to delete

        Returns:
            True if successful, False if profile not found
        """
        if profile_id not in self._profiles:
            return False

        # Delete credentials
        self.credential_service.delete_credentials(profile_id)

        # Remove from profiles
        del self._profiles[profile_id]

        # Remove from last active connections if present
        if profile_id in self._last_active_connections:
            self._last_active_connections.remove(profile_id)

        self._save_profiles()
        self.profile_deleted.emit(profile_id)

        return True

    def duplicate_profile(self, profile_id: str, new_name: str) -> str | None:
        """
        Duplicate an existing profile.

        Args:
            profile_id: ID of profile to duplicate
            new_name: Name for the new profile

        Returns:
            New profile ID, or None if source profile not found
        """
        source_profile = self._profiles.get(profile_id)
        if not source_profile:
            return None

        # Get credentials from source
        credentials = self.credential_service.get_credentials(profile_id)

        # Create new profile
        new_id = self.create_profile(
            name=new_name,
            provider=source_profile.provider,
            config=source_profile.config.copy(),
            credentials=credentials,
        )

        return new_id

    def get_profile_with_credentials(self, profile_id: str) -> dict[str, Any] | None:
        """
        Get a profile along with its credentials.

        Args:
            profile_id: ID of profile

        Returns:
            Dictionary with profile data and credentials, or None if not found
        """
        profile = self._profiles.get(profile_id)
        if not profile:
            return None

        credentials = self.credential_service.get_credentials(profile_id)

        return {
            "id": profile.id,
            "name": profile.name,
            "provider": profile.provider,
            "config": profile.config,
            "credentials": credentials or {},
        }

    def export_profiles(self, include_credentials: bool = False) -> list[dict[str, Any]]:
        """
        Export all profiles for backup/sharing.

        Args:
            include_credentials: Whether to include credentials (NOT RECOMMENDED)

        Returns:
            List of profile dictionaries
        """
        exported = []
        for profile in self._profiles.values():
            data = profile.to_dict()
            if include_credentials:
                credentials = self.credential_service.get_credentials(profile.id)
                if credentials:
                    data["credentials"] = credentials
            exported.append(data)
        return exported

    def import_profiles(
        self, profiles_data: list[dict[str, Any]], overwrite: bool = False
    ) -> dict[str, str]:
        """
        Import profiles from exported data.

        Args:
            profiles_data: List of profile dictionaries
            overwrite: Whether to overwrite existing profiles with same ID

        Returns:
            Dictionary mapping old IDs to new IDs
        """
        id_mapping = {}

        for profile_data in profiles_data:
            old_id = profile_data.get("id")

            # Generate new ID if not overwriting or ID exists
            if not overwrite or old_id in self._profiles:
                new_id = str(uuid.uuid4())
            else:
                new_id = str(old_id) if old_id else str(uuid.uuid4())

            credentials = profile_data.pop("credentials", None)

            # Create profile
            profile = ConnectionProfile(
                profile_id=new_id,
                name=profile_data["name"],
                provider=profile_data["provider"],
                config=profile_data.get("config", {}),
                credential_fields=profile_data.get("credential_fields", []),
            )

            self._profiles[new_id] = profile

            # Store credentials if provided
            if credentials:
                self.credential_service.store_credentials(new_id, credentials)

            id_mapping[old_id] = new_id

        self._save_profiles()

        return id_mapping

    def save_last_active_connections(self, connection_ids: list[str]):
        """
        Save list of last active connection profile IDs for session restore.

        Args:
            connection_ids: List of profile IDs that were active
        """
        self._last_active_connections = connection_ids
        self._save_profiles()

    def get_last_active_connections(self) -> list[str]:
        """Get list of last active connection profile IDs."""
        return self._last_active_connections.copy()

    def migrate_legacy_connection(self, config: dict[str, Any]) -> str:
        """
        Migrate a legacy single-connection configuration to a profile.

        Args:
            config: Legacy connection configuration

        Returns:
            The new profile ID
        """
        provider = config.get("provider", "chromadb")
        conn_type = config.get("type", "persistent")

        # Create a name based on connection type
        if conn_type == "persistent":
            name = f"Legacy {provider.title()} (Persistent)"
        elif conn_type == "http":
            host = config.get("host", "localhost")
            name = f"Legacy {provider.title()} ({host})"
        else:
            name = f"Legacy {provider.title()} (Ephemeral)"

        # Extract credentials if any
        credentials = {}
        if config.get("api_key"):
            credentials["api_key"] = config["api_key"]
            del config["api_key"]  # Remove from config

        # Create profile
        profile_id = self.create_profile(
            name=name,
            provider=provider,
            config=config,
            credentials=credentials if credentials else None,
        )

        return profile_id
