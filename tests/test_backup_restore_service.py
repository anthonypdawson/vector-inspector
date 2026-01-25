from pathlib import Path
import json

from vector_inspector.services.backup_helpers import write_backup_zip
from vector_inspector.services.backup_restore_service import BackupRestoreService


class FakeConnection:
    def __init__(self):
        self.collections = []
        self.added = None

    def list_collections(self):
        return self.collections

    def delete_collection(self, name):
        if name in self.collections:
            self.collections.remove(name)

    def prepare_restore(self, metadata, data):
        # Pretend to precreate collection
        self.collections.append(metadata.get("collection_name"))
        # Ensure IDs are strings
        if data.get("ids"):
            data["ids"] = [str(i) for i in data.get("ids")]
        return True

    def add_items(self, collection_name, documents, metadatas, ids, embeddings):
        self.added = dict(
            collection_name=collection_name,
            documents=documents,
            metadatas=metadatas,
            ids=ids,
            embeddings=embeddings,
        )
        return True


def test_restore_uses_prepare_restore_and_adds_items(tmp_path):
    metadata = {"collection_name": "col", "backup_timestamp": "now", "collection_info": {"vector_dimension": 3}}
    data = {"ids": [1, 2], "documents": ["a", "b"], "metadatas": [{}, {}], "embeddings": [[0,0,0],[1,1,1]]}
    p = tmp_path / "b.zip"
    write_backup_zip(p, metadata, data)

    conn = FakeConnection()
    svc = BackupRestoreService()
    ok = svc.restore_collection(conn, str(p))
    assert ok is True
    assert conn.added is not None
    assert conn.added["collection_name"] == "col"
    assert conn.added["ids"] == ["1", "2"]


def test_restore_with_empty_embeddings_triggers_prepare_restore(tmp_path):
    # Prepare a backup where embeddings key exists but is an empty list
    metadata = {"collection_name": "col_empty", "backup_timestamp": "now", "collection_info": {"vector_dimension": 3}}
    data = {"ids": [1, 2], "documents": ["a", "b"], "metadatas": [{}, {}], "embeddings": []}
    p = tmp_path / "b_empty.zip"
    write_backup_zip(p, metadata, data)

    class FakeConn2:
        def __init__(self):
            self.collections = []
            self.added = None

        def list_collections(self):
            return self.collections

        def delete_collection(self, name):
            if name in self.collections:
                self.collections.remove(name)

        def prepare_restore(self, metadata, data):
            # Simulate provider generating embeddings when list is empty
            if data.get("embeddings") == []:
                data["embeddings"] = [[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]]
            self.collections.append(metadata.get("collection_name"))
            return True

        def add_items(self, collection_name, documents, metadatas, ids, embeddings):
            self.added = dict(
                collection_name=collection_name,
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings,
            )
            return True

    conn = FakeConn2()
    svc = BackupRestoreService()
    ok = svc.restore_collection(conn, str(p))
    assert ok is True
    assert conn.added is not None
    assert conn.added["collection_name"] == "col_empty"
    assert conn.added["embeddings"] is not None
    assert len(conn.added["embeddings"]) == 2
