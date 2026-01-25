"""Helpers for backup/restore: zip read/write and embedding normalization.

Minimal, well-tested helpers to keep `BackupRestoreService` concise.
"""
import json
import zipfile
from typing import Any


def write_backup_zip(path, metadata: dict[str, Any], data: dict[str, Any]):
    """Write metadata and data into a zip file at `path`.

    `path` may be a pathlib.Path or string.
    """
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.writestr('metadata.json', json.dumps(metadata, indent=2))
        zipf.writestr('data.json', json.dumps(data, indent=2))


def read_backup_zip(path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Read metadata.json and data.json from a backup zip and return them.

    Returns (metadata, data).
    """
    with zipfile.ZipFile(path, 'r') as zipf:
        metadata_str = zipf.read('metadata.json').decode('utf-8')
        metadata = json.loads(metadata_str)
        data_str = zipf.read('data.json').decode('utf-8')
        data = json.loads(data_str)
    return metadata, data


def normalize_embeddings(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure embeddings in `data` are plain python lists (no numpy objects).

    This mutates and returns the same `data` dict for convenience.
    """
    if 'embeddings' not in data or data['embeddings'] is None:
        return data

    try:
        import numpy as np
    except Exception:
        np = None

    emb = data['embeddings']
    if np is not None:
        if isinstance(emb, np.ndarray):
            data['embeddings'] = emb.tolist()
            return data

        if isinstance(emb, list):
            new_list = []
            for item in emb:
                if isinstance(item, np.ndarray):
                    new_list.append(item.tolist())
                else:
                    new_list.append(item)
            data['embeddings'] = new_list
            return data

    # No numpy available — assume data already serializable
    return data
