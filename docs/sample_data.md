# Minimal "Create Collection" With Sample Data
A focused feature that lets users create a new collection and optionally populate it with synthetic text data. This gives Vector Inspector an instant testbed for embeddings, search, clustering, and early RAG Builder workflows.

---

## 1. Feature Overview
Users can:
- Create a new collection in the active vector database.
- Optionally generate N synthetic text items.
- Automatically embed and upsert those items.

This removes the need for users to bring their own data just to test features.

---

## 2. UI Components

File: ui/components/create_collection_dialog.py  
A PySide6 dialog modeled after your existing connection/profile dialogs.

Fields:
- Collection Name (text field)
- Add Sample Data (checkbox)
- Number of Items (spinbox, default 100)
- Data Type (dropdown: text, markdown, json)
- Embedding Model (dropdown populated from model registry)
- Buttons: Create, Cancel

Behavior:
- Emits a structured payload to the controller:
  name
  add_sample
  count
  data_type
  embedder_name

---

## 3. Controller Layer

File: ui/controllers/collection_controller.py  
Add a method:

create_collection(name, add_sample, count, data_type, embedder_name):
    1. Get active DB connection
    2. Create empty collection
    3. If sample data requested, call collection_service.populate_with_sample_data(...)
    4. Refresh UI state

This mirrors your existing controller patterns.

---

## 4. Service Layer

File: services/collection_service.py  
Add:

populate_with_sample_data(conn, collection, count, data_type, embedder_name):
    1. Generate synthetic items using generate_sample_data(...)
    2. Embed using existing embedding providers
    3. Upsert into the new collection with metadata {source: "sample"}

This uses your existing embedding + upsert infrastructure.

---

## 5. Sample Data Generator

File: core/sample_data/text_generator.py  
A tiny utility module:

generate_sample_data(n, data_type):
    if text:
        return random lorem sentences
    if markdown:
        return simple markdown sections
    if json:
        return list of small dicts with title + description

This is intentionally simple — just enough to test embeddings and retrieval.

---

## 6. Integration Points

Add menu entry:
Tools → Create Test Collection

Add button in connection view:
[ New Collection ]  [ New Test Collection ]

RAG Builder integration (later):
If no collections exist:
"Create a sample collection to get started →"

---

## 7. Implementation Checklist

- Add dialog UI
- Add controller method
- Add service method
- Add sample data generator module
- Add menu/button entry
- Test with Chroma, Qdrant, pgvector
- Validate embedding + upsert flow
- Add success/error notifications

---

## 8. Optional Future Enhancements

- Generate synthetic Q/A pairs
- Generate synthetic documents
- Generate embeddings only (no upsert)
- Generate clusterable data for clustering panel
- Import from URL (docs, blog posts, etc.)

