"""Service for backing up and restoring collections."""

import json
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import shutil

from vector_inspector.core.logging import log_info, log_error, log_debug
from .backup_helpers import write_backup_zip, read_backup_zip, normalize_embeddings


class BackupRestoreService:
    """Handles backup and restore operations for vector database collections."""

    @staticmethod
    def backup_collection(
        connection, collection_name: str, backup_dir: str, include_embeddings: bool = True
    ) -> Optional[str]:
        """
        Backup a collection to a directory.

        Args:
            connection: Vector database connection
            collection_name: Name of collection to backup
            backup_dir: Directory to store backups
            include_embeddings: Whether to include embedding vectors

        Returns:
            Path to backup file or None if failed
        """
        try:
            Path(backup_dir).mkdir(parents=True, exist_ok=True)

            collection_info = connection.get_collection_info(collection_name)
            if not collection_info:
                log_error("Failed to get collection info for %s", collection_name)
                return None

            all_data = connection.get_all_items(collection_name)
            if not all_data or not all_data.get("ids"):
                log_info("No data to backup from collection %s", collection_name)
                return None

            # Normalize embeddings to plain lists
            all_data = normalize_embeddings(all_data)

            if not include_embeddings and "embeddings" in all_data:
                del all_data["embeddings"]

            backup_metadata = {
                "collection_name": collection_name,
                "backup_timestamp": datetime.now().isoformat(),
                "item_count": len(all_data["ids"]),
                "collection_info": collection_info,
                "include_embeddings": include_embeddings,
            }

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{collection_name}_backup_{timestamp}.zip"
            backup_path = Path(backup_dir) / backup_filename

            write_backup_zip(backup_path, backup_metadata, all_data)
            log_info("Backup created: %s", backup_path)
            return str(backup_path)
        except Exception as e:
            log_error("Backup failed: %s", e)
            return None

    @staticmethod
    def restore_collection(
        connection, backup_file: str, collection_name: Optional[str] = None, overwrite: bool = False
    ) -> bool:
        """
        Restore a collection from a backup file.

        Args:
            connection: Vector database connection
            backup_file: Path to backup zip file
            collection_name: Optional new name for restored collection
            overwrite: Whether to overwrite existing collection

        Returns:
            True if successful, False otherwise
        """
        restore_collection_name = None
        try:
            metadata, data = read_backup_zip(backup_file)
            restore_collection_name = collection_name or metadata.get("collection_name")

            existing_collections = connection.list_collections()
            if restore_collection_name in existing_collections:
                if not overwrite:
                    log_info(
                        "Collection %s already exists. Use overwrite=True to replace it.",
                        restore_collection_name,
                    )
                    return False
                else:
                    connection.delete_collection(restore_collection_name)

            # Provider-specific preparation hook
            if hasattr(connection, "prepare_restore"):
                ok = connection.prepare_restore(metadata, data)
                if not ok:
                    log_error("Provider prepare_restore failed for %s", restore_collection_name)
                    return False

            # Ensure embeddings normalized
            data = normalize_embeddings(data)

            success = connection.add_items(
                restore_collection_name,
                documents=data.get("documents", []),
                metadatas=data.get("metadatas"),
                ids=data.get("ids"),
                embeddings=data.get("embeddings"),
            )

            if success:
                log_info("Collection '%s' restored from backup", restore_collection_name)
                log_info("Restored %d items", len(data.get("ids", [])))
                return True

            # Failure: attempt cleanup
            log_error("Failed to restore collection %s", restore_collection_name)
            try:
                if restore_collection_name in connection.list_collections():
                    log_info(
                        "Cleaning up failed restore: deleting collection '%s'",
                        restore_collection_name,
                    )
                    connection.delete_collection(restore_collection_name)
            except Exception as cleanup_error:
                log_error("Warning: Failed to clean up collection: %s", cleanup_error)
            return False

        except Exception as e:
            log_error("Restore failed: %s", e)
            try:
                if (
                    restore_collection_name
                    and restore_collection_name in connection.list_collections()
                ):
                    log_info(
                        "Cleaning up failed restore: deleting collection '%s'",
                        restore_collection_name,
                    )
                    connection.delete_collection(restore_collection_name)
            except Exception as cleanup_error:
                log_error("Warning: Failed to clean up collection: %s", cleanup_error)
            return False

    @staticmethod
    def list_backups(backup_dir: str) -> list:
        """
        List all backup files in a directory.

        Args:
            backup_dir: Directory containing backups

        Returns:
            List of backup file information dictionaries
        """
        backup_path = Path(backup_dir)
        if not backup_path.exists():
            return []

        backups = []
        for backup_file in backup_path.glob("*_backup_*.zip"):
            try:
                metadata, _ = read_backup_zip(backup_file)
                backups.append(
                    {
                        "file_path": str(backup_file),
                        "file_name": backup_file.name,
                        "collection_name": metadata.get("collection_name", "Unknown"),
                        "timestamp": metadata.get("backup_timestamp", "Unknown"),
                        "item_count": metadata.get("item_count", 0),
                        "file_size": backup_file.stat().st_size,
                    }
                )
            except Exception:
                continue

        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        return backups

    @staticmethod
    def delete_backup(backup_file: str) -> bool:
        """
        Delete a backup file.

        Args:
            backup_file: Path to backup file to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            Path(backup_file).unlink()
            return True
        except Exception as e:
            log_error("Failed to delete backup: %s", e)
            return False
