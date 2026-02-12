"""Filter-related logic for metadata view."""

from typing import Any


def update_filter_fields(filter_builder, data: dict[str, Any]):
    """Update filter builder with available metadata field names.

    Args:
        filter_builder: FilterBuilder instance to update
        data: Collection data dictionary with documents and metadatas
    """
    field_names = []

    # Add 'document' field if documents exist
    documents = data.get("documents", [])
    if documents and any(doc for doc in documents if doc):
        field_names.append("document")

    # Add metadata fields
    metadatas = data.get("metadatas", [])
    if metadatas and len(metadatas) > 0 and metadatas[0]:
        # Get all unique metadata keys from the first item
        metadata_keys = sorted(metadatas[0].keys())
        field_names.extend(metadata_keys)

    if field_names:
        filter_builder.set_available_fields(field_names)
