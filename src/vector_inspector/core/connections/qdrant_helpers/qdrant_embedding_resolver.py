
from vector_inspector.core.embedding_utils import get_model_for_dimension, load_embedding_model, DEFAULT_MODEL


def resolve_embedding_model(connection, collection_name: str) -> tuple[object, str, str]:
    """Resolve an embedding model for a collection.

    Returns (model, model_name, model_type). This encapsulates the previous
    `_get_embedding_model_for_collection` logic so the connection stays focused
    on Qdrant operations.
    """
    collection_info = connection.get_collection_info(collection_name)
    if not collection_info:
        model_name, model_type = DEFAULT_MODEL
        model = load_embedding_model(model_name, model_type)
        return (model, model_name, model_type)

    # Priority 1: explicit metadata on collection
    if 'embedding_model' in collection_info:
        model_name = collection_info['embedding_model']
        model_type = collection_info.get('embedding_model_type', 'sentence-transformer')
        model = load_embedding_model(model_name, model_type)
        return (model, model_name, model_type)

    # Priority 3: guess by vector dimension
    vector_dim = collection_info.get('vector_dimension')
    if not vector_dim or vector_dim == 'Unknown':
        model_name, model_type = DEFAULT_MODEL
        model = load_embedding_model(model_name, model_type)
        return (model, model_name, model_type)

    model_name, model_type = get_model_for_dimension(vector_dim)
    model = load_embedding_model(model_name, model_type)
    return (model, model_name, model_type)
