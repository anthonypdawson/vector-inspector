def test_fake_provider_delete_where(fake_provider):
    # initial collection has 3 items with metadatas name: a, b, c
    res_before = fake_provider.get_all_items("test_collection")
    assert len(res_before["ids"]) == 3

    # delete items where name == 'b'
    ok = fake_provider.delete_items("test_collection", where={"name": "b"})
    assert ok is True

    res_after = fake_provider.get_all_items("test_collection")
    # only two items should remain and none with name 'b'
    assert len(res_after["ids"]) == 2
    remaining_names = [m.get("name") for m in res_after["metadatas"]]
    assert "b" not in remaining_names


def test_fake_provider_delete_with_ids_ignores_where(fake_provider):
    # Ensure ids path takes precedence over where in FakeProvider.delete_items
    # Add a distinguishable item
    fake_provider.add_items("test_collection", ["x"], metadatas=[{"name": "x"}], ids=["special-id"])

    # Try deleting by id while passing a where that would not match the id
    ok = fake_provider.delete_items("test_collection", ids=["special-id"], where={"name": "nonexistent"})
    assert ok is True

    # Ensure the special-id is gone
    all_ids = fake_provider.get_all_items("test_collection")["ids"]
    assert "special-id" not in all_ids
