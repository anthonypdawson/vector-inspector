import numpy as np


class _FakeConnectionBase:
    def __init__(self, create_success=True, add_success=True, profile_name=None):
        self._create_success = create_success
        self._add_success = add_success
        self.profile_name = profile_name

    def create_collection(self, **kwargs):
        return self._create_success

    def add_items(self, **kwargs):
        return self._add_success


def FakeConnection(create_success=True, add_success=True, profile_name=None, cls_name="MockDB"):
    """Factory that returns an instance whose class has the requested name."""
    C = type(cls_name, (_FakeConnectionBase,), {})
    return C(create_success=create_success, add_success=add_success, profile_name=profile_name)


class FakeProvider:
    def __init__(self, dimension=3, encode_success=True):
        self.dimension = dimension
        self._encode_success = encode_success

    def get_metadata(self):
        class M:
            dimension = self.dimension

        return M()

    def encode(self, texts, normalize=True, show_progress=False):
        if not self._encode_success:
            raise RuntimeError("encode-failed")
        # return numpy array of shape (len(texts), dimension)
        return np.zeros((len(texts), self.dimension))


def test_create_collection_success():
    from vector_inspector.services.collection_service import CollectionService

    conn = FakeConnection(create_success=True)
    svc = CollectionService()
    assert svc.create_collection(conn, "col1", dimension=128) is True


def test_create_collection_failure():
    from vector_inspector.services.collection_service import CollectionService

    conn = FakeConnection(create_success=False)
    svc = CollectionService()
    assert svc.create_collection(conn, "col1") is False


def test_populate_with_sample_data_success(monkeypatch):
    from vector_inspector.core.sample_data import SampleDataType
    from vector_inspector.services.collection_service import CollectionService

    svc = CollectionService()
    conn = FakeConnection(add_success=True, cls_name="MockDB")

    # Patch ProviderFactory.create to return our fake provider
    import vector_inspector.services.collection_service as cs_mod

    monkeypatch.setattr(cs_mod.ProviderFactory, "create", lambda name, t: FakeProvider(dimension=4))

    success, msg = svc.populate_with_sample_data(conn, "colA", 3, SampleDataType.TEXT, "fake-model")
    assert success is True
    assert "Successfully added 3 sample items" in msg


def test_populate_with_sample_data_provider_load_fail(monkeypatch):
    from vector_inspector.core.sample_data import SampleDataType
    from vector_inspector.services.collection_service import CollectionService

    svc = CollectionService()
    conn = FakeConnection(add_success=True)

    def raise_create(name, t):
        raise RuntimeError("provider-load")

    import vector_inspector.services.collection_service as cs_mod

    monkeypatch.setattr(cs_mod.ProviderFactory, "create", raise_create)

    success, msg = svc.populate_with_sample_data(conn, "colA", 2, SampleDataType.TEXT, "bad-model")
    assert success is False
    assert "Failed to load embedding model" in msg


def test_populate_with_sample_data_encode_fail(monkeypatch):
    from vector_inspector.core.sample_data import SampleDataType
    from vector_inspector.services.collection_service import CollectionService

    svc = CollectionService()
    conn = FakeConnection(add_success=True)

    monkeypatch.setattr(
        "vector_inspector.services.collection_service.ProviderFactory.create",
        lambda n, t: FakeProvider(encode_success=False),
    )

    success, msg = svc.populate_with_sample_data(conn, "colA", 2, SampleDataType.TEXT, "model")
    assert success is False
    assert "Failed to generate embeddings" in msg


def test_populate_with_sample_data_add_items_fail(monkeypatch):
    from vector_inspector.core.sample_data import SampleDataType
    from vector_inspector.services.collection_service import CollectionService

    svc = CollectionService()
    conn = FakeConnection(add_success=False)

    monkeypatch.setattr(
        "vector_inspector.services.collection_service.ProviderFactory.create", lambda n, t: FakeProvider()
    )

    success, msg = svc.populate_with_sample_data(conn, "colA", 2, SampleDataType.TEXT, "model")
    assert success is False
    assert "Failed to insert data into collection" in msg
