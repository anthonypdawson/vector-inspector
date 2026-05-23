# Planning: File Preview, Image Ingestion & Document Ingestion

**Date:** 2026-03-31  
**Status:** Draft

---

## Feature 2 — File Preview in Entry View

### Goal

When a metadata field value looks like a file path and the file exists on disk, render a preview of that file inline in the entry detail views (`InlineDetailsPane` and/or `ItemDetailsDialog`) rather than displaying the raw path string.

Support:
- **Image files** — render a scaled thumbnail
- **Text files** — render the first N lines of content in a read-only text area
- **Unknown/binary files** — fall back to displaying the raw path as plain text (no crash)

---

### Affected Files

| File | Change |
|---|---|
| `src/vector_inspector/ui/components/inline_details_pane.py` | Primary target — add a "File Preview" collapsible section |
| `src/vector_inspector/ui/components/item_details_dialog.py` | Secondary — add preview widget row when path is detected |
| `src/vector_inspector/utils/file_preview_utils.py` | **New** — pure utility: path detection, file type resolution, thumbnail loading |
| `src/vector_inspector/ui/views/metadata/metadata_table.py` | Add "preview available" icon column delegate |

---

### Path Detection Logic

A value in item metadata qualifies for preview if ALL of the following hold:

1. The value is a `str`
2. `len(value) > 0` and `len(value) < 1024` (reject absurdly long strings)
3. `pathlib.Path(value).is_absolute()` OR the string contains a path separator (`/` or `\`)
4. `os.path.isfile(value)` returns `True` at render time (non-blocking stat)

Candidate metadata keys (checked first to short-circuit the scan):
- `file_path`, `frame_path`, `source`, `path`, `filename`, `image_path`, `thumbnail`

If no candidate key matches, do a broader scan of all remaining string-valued metadata fields using the rules above. Limit the scan to 20 fields to keep rendering fast.

**Important:** Path checks happen on the UI thread but are O(1) filesystem stats — acceptable. Do NOT read large files on the UI thread; use `ThreadedTaskRunner` (see [Ingestion section](#async-file-loading)).

---

### Supported File Types

Image files are identified by a fixed extension allowlist. Text files are detected dynamically to support any source or prose file without maintaining an explicit list.

#### Image extensions (fixed allowlist)

`.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp`, `.tiff`, `.tif`

#### Text detection (dynamic, two-step)

1. **`mimetypes.guess_type(path)`** (stdlib, no disk read) — if the MIME type starts with `text/`, the file is treated as text. This covers JS, TS, Ruby, Go, Rust, Shell, and virtually every source file out of the box.
2. **Null-byte sniff fallback** — if `mimetypes` returns `None` or a non-`text/` type (unknown extension), read the first 8 KB and check for `\x00` bytes. No null bytes → treat as text. This is the same heuristic git uses and handles any extension-less or unusual file.

**Result:** image and text detection requires zero new dependencies and covers all common source file types automatically.

#### Structured document types (explicit, for ingestion only)

`.pdf` and `.docx` require dedicated extraction libraries and are classified separately from the general text path (see Feature 1).

Anything that fails both image detection and text detection → falls back to raw path label only (no crash).

---

### UI Design

#### `InlineDetailsPane` — new collapsible section

Add a **"File Preview"** `CollapsibleSection` between the existing "Document Preview" and "Metadata" sections. The section is only created and shown when at least one previewable path is found.

**Image preview widget (InlineDetailsPane — constrained):**
- `QLabel` with `setPixmap(...)` — max size **160 × 120 px** (intentionally small; the pane is a glance, not a viewer)
- Below the image: filename only (no dimensions, to save vertical space)
- Double-click → open in OS default viewer via `QDesktopServices.openUrl(QUrl.fromLocalFile(path))`
- Right-click → context menu with two actions:
  - **Open** — same as double-click
  - **Reveal in Finder / Show in Explorer** — opens the containing folder and selects the file:
    - macOS: `subprocess.run(["open", "-R", path])`
    - Windows: `subprocess.run(["explorer", "/select,", path])`
    - Linux fallback: `QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(path)))`
  - The correct label ("Finder" vs "Explorer" vs "Files") is resolved at runtime via `sys.platform`.

**Text preview widget (InlineDetailsPane — constrained):**
- `QTextEdit` set read-only, fixed height **100 px** (compact; scrollable)
- Load first **30 lines or 2 KB**, whichever comes first
- If truncated, add a `"… (truncated)"` label underneath
- For JSON/CSV files: display raw content only (no pretty-printing to avoid CPU spike)

**Multiple paths found:** Render one preview block per path, stacked vertically inside the section's scroll area. Cap at 3 previews to avoid overwhelming the pane.

#### `ItemDetailsDialog`

Add a labeled `QFrame` row titled **"File Preview"** using larger image/text widgets, inserted between the "Document" and "Metadata" rows. Follows all existing row-padding conventions.

**Image widget (ItemDetailsDialog — full-detail view):**
- Default: scaled-down thumbnail at **320 × 240 px** with filename + dimensions label below.
- A small **"Full size" / "Fit"** toggle button (or double-click on the image) switches between:
  - **Fit mode** (default) — image scaled to `min(dialog_width - padding, 640)` × 480 px, aspect-ratio preserved.
  - **Full size mode** — image shown at native resolution inside a `QScrollArea`; scrollable if larger than the dialog.
- Right-click menu mirrors the inline pane (Open, Reveal in Finder/Explorer).

**Text widget (ItemDetailsDialog):**
- `QTextEdit` read-only, height **300 px**
- Load first 100 lines or 8 KB, with truncation label if needed.

#### Metadata table — "Preview available" indicator

Add a narrow fixed-width column (20 px) at the far left of the metadata table. When an item has at least one previewable file path (detected using `find_preview_paths`), the cell renders a small icon (📎 or a custom SVG eye icon from `assets/icons/`) using a `QStyledItemDelegate`. Empty otherwise.

- The icon is a **non-clickable visual signal only** — clicking the row still selects it normally.
- Tooltip on hover: `"This entry has a file preview available"`.
- The column header is blank (no label) and not resizable.
- The check is performed when the table model is populated, stored as a boolean flag on the model item (`Qt.UserRole + 10` or a named role). No disk I/O happens at paint time — `find_preview_paths` is called once per item during data load and the result is cached.
- The icon reuses the same threading path as data loading; no extra background task is needed since path detection is O(1) per field.

---

### Async File Loading

File content and image loading happens off the UI thread using `ThreadedTaskRunner`:

```python
def _load_preview(self, path: str) -> None:
    def _read():
        # returns (type, data) where type is "image" | "text" | "error"
        ...

    def _on_done(result):
        self._render_preview(result)

    self._runner.run(_read, callback=_on_done)
```

If the file disappears between the stat check and the load, emit an "error" result and show a `"File no longer available"` label — do not raise.

---

### New Utility Module: `file_preview_utils.py`

```
src/vector_inspector/utils/file_preview_utils.py
```

Public API:

```python
IMAGE_EXTENSIONS: frozenset[str]
CANDIDATE_KEYS: tuple[str, ...]

def find_preview_paths(metadata: dict[str, Any]) -> list[str]:
    """Return up to 3 valid, existing file paths found in metadata."""

def file_type(path: str) -> Literal["image", "text", "unknown"]:
    """
    Classify a path as 'image', 'text', or 'unknown'.
    Images are matched against IMAGE_EXTENSIONS.
    Text is detected via mimetypes.guess_type; falls back to a null-byte sniff
    of the first 8 KB if mimetypes returns None or a non-text/ MIME type.
    """

def is_text_file(path: str) -> bool:
    """
    Return True if the file should be treated as plain text.
    Uses mimetypes then null-byte sniff; never raises on read errors (returns False).
    """

def read_text_preview(path: str, max_lines: int = 100, max_bytes: int = 8192) -> tuple[str, bool]:
    """Return (content, truncated). Raises OSError on failure."""

def load_image_pixmap(path: str, max_w: int = 320, max_h: int = 240) -> QPixmap:
    """Load, decode, and scale an image. Raises OSError or ValueError on failure."""
```

---

### Testing

- `tests/utils/test_file_preview_utils.py` — unit tests for `find_preview_paths`, `file_type`, `is_text_file`, `read_text_preview` using tmp files (no Qt needed)
  - `is_text_file`: `.py` → True (mimetypes), `.ts` → True (mimetypes), `.rb` → True (mimetypes), extension-less file with text content → True (sniff), binary file → False (sniff)
  - `file_type`: image extension → `"image"`, text MIME → `"text"`, `.pdf` / `.docx` → `"unknown"` (ingestion handles these separately)
- `tests/ui/test_inline_details_pane.py` — extend existing pane tests to cover: path detected → section visible, no path → section hidden
- `tests/ui/test_metadata_table.py` — icon column: item with previewable path shows flag; item without path does not
- Image loading tested with a 1×1 px PNG fixture
- Reveal action: assert correct platform command is built (mock `subprocess.run`)
- Edge cases: symlink, non-existent file, zero-byte file, binary file with `.txt` extension (limit to 8 KB read is sufficient protection)

---

## Feature 1 — Document & Image Ingestion

### Goal

Add a **file ingestion pipeline** to Vector Inspector that:
1. Accepts a folder (or individual files) as input
2. Generates embeddings appropriate to the file type:
   - **Images** — CLIP embeddings via `openai/clip-vit-base-patch32`
   - **Text/documents** — sentence embeddings via `sentence-transformers/all-MiniLM-L6-v2`
3. Writes items to the currently connected collection with standardized metadata

This is a first-party ingestion path for both images and documents, complementing the existing CSV/JSON import. Concepts and model choices are borrowed from `rag-lab/rag_lab/core/video_pipeline.py` and the local model in `rag-lab/models/all-MiniLM-L6-v2/`.

---

### Architecture

File ingestion lives in a new unified service:

```
src/vector_inspector/services/file_ingestion_service.py
```

The service dispatches to the appropriate pipeline based on file type (image or document). It is invoked from the existing UI via new menu items under **File → Import**:
- **Import Images…** — CLIP pipeline
- **Import Documents…** — sentence-transformer pipeline

Both stubs are owned by VI. Implementation is available free-tier with local models; cloud/custom model variants are wired by VS.

---

### Embedding Models

#### Images — CLIP

Use **OpenAI CLIP** (`openai/clip-vit-base-patch32`) via `transformers` + `Pillow`, loaded lazily:

```python
# utils/lazy_imports.py additions
def get_clip_model_and_processor():
    from transformers import CLIPModel, CLIPProcessor
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    return model, processor
```

Output: **512-dim** float32 embedding, L2-normalized.

#### Text/Documents — Sentence Transformers

Use **`sentence-transformers/all-MiniLM-L6-v2`** via `sentence-transformers`, loaded lazily:

```python
# utils/lazy_imports.py additions
def get_sentence_transformer(model_name: str = "all-MiniLM-L6-v2"):
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(model_name)
```

If the model is already present locally (e.g., `rag-lab/models/all-MiniLM-L6-v2/`), the path can be passed directly to avoid a download. Output: **384-dim** float32 embedding, L2-normalized.

**Note:** Because image (512-dim) and text (384-dim) embeddings have different dimensions, image and document imports must target **separate collections** with matching dimensions. The ingestion dialog enforces this by showing only dimension-compatible collections in the dropdown.

All embeddings are L2-normalized (matching rag-lab's convention and typical cosine-distance collections).

---

### Supported File Types

#### Images (fixed allowlist)

`.png`, `.jpg`, `.jpeg`, `.gif`, `.bmp`, `.webp`, `.tiff`, `.tif`

#### Plain text / source files (dynamic detection)

Rather than a fixed list, the ingestion service uses the same `is_text_file()` utility from `file_preview_utils.py`:
1. `mimetypes.guess_type(path)` — MIME starts with `text/` → accepted. Covers `.txt`, `.md`, `.py`, `.js`, `.ts`, `.rb`, `.go`, `.rs`, `.sh`, `.csv`, `.html`, `.xml`, `.log`, `.srt` and more without any explicit list.
2. Null-byte sniff fallback — for unknown or extension-less files.

For ingestion, if `is_text_file()` returns True **and** the extension is not `.pdf` or `.docx`, the document pipeline handles the file as plain text.

#### Structured documents (explicit)

| Type | Extension | Extraction library |
|---|---|---|
| PDF | `.pdf` | `pypdf` |
| Word | `.docx` | `python-docx` |

Files that are neither images, detected text, PDF, nor `.docx` are skipped with an entry in `IngestionResult.errors`.

---

### Metadata Schema

#### Common fields (all file types)

| Key | Value |
|---|---|
| `file_path` | Absolute path to the source file |
| `filename` | `os.path.basename(file_path)` |
| `file_hash` | MD5 hex digest of the raw file bytes |
| `format` | Lowercase extension without dot, e.g. `"png"`, `"pdf"` |
| `file_type` | `"image"` or `"document"` |
| `ingested_at` | ISO 8601 UTC timestamp |
| `source_folder` | Absolute path of the input folder (omitted for single-file ingestion) |

`id` is the `file_hash` for image items (deduplication) unless the user opts for UUID generation. For document chunks, `id` is `"{file_hash}-{chunk_index}"` (see Document-specific fields).

`document` is set to the filename for images, or to the first 512 characters of the chunk text for documents.

#### Image-specific fields

| Key | Value |
|---|---|
| `width` | Pixel width (int) |
| `height` | Pixel height (int) |

#### Document-specific fields

| Key | Value |
|---|---|
| `char_count` | Character count of extracted text (int) |
| `word_count` | Word count of extracted text (int) |
| `page_count` | Number of pages — PDF only; omitted for plain text and `.docx` unless easily obtained |
| `chunk_index` | 0-based index of this chunk within the document (int) |
| `chunk_total` | Total number of chunks produced from this document (int) |
| `parent_id` | MD5 `file_hash` of the source file — links all chunks back to their origin |

`id` for chunk items is `"{file_hash}-{chunk_index}"` (stable, deterministic, deduplication-safe).

---

### Service API

```python
class FileIngestionService:
    def ingest_folder(
        self,
        folder_path: str,
        connection,                          # ConnectionInstance
        collection_name: str,
        file_type: Literal["image", "document"],
        batch_size: int = 16,
        recursive: bool = False,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> IngestionResult:
        """Scan folder for files matching file_type and ingest them."""
        ...

    def ingest_files(
        self,
        file_paths: list[str],
        connection,
        collection_name: str,
        file_type: Literal["image", "document"],
        batch_size: int = 16,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> IngestionResult:
        """Ingest an explicit list of files."""
        ...
```

Internally, `ingest_files` dispatches to `_embed_image_batch` or `_embed_document_batch` based on `file_type`.

`IngestionResult` is a simple dataclass:

```python
@dataclass
class IngestionResult:
    total: int          # number of source files processed (not chunks)
    succeeded: int      # files where all chunks were upserted successfully
    skipped: int        # files skipped because all chunks already present (hash match)
    failed: int         # files where extraction or embedding raised an error
    errors: list[str]   # human-readable per-file error messages
    chunks_written: int # total individual chunk items upserted across all files
```

`total`, `succeeded`, `skipped`, and `failed` always count **source files**, not chunks. `chunks_written` is the total number of chunk items actually upserted and is shown in the completion summary (e.g., `"Ingested 3 documents (47 chunks). 1 skipped. 0 failed."`).

---

### Processing Pipelines

#### Per-image pipeline

```
1. Validate file — readable, non-zero size, extension in IMAGE_EXTENSIONS
2. Compute MD5 hash
3. Check for duplicate — query collection by id=hash; skip if present
4. Open with Pillow — convert to RGB
5. Capture width, height
6. Run CLIP processor + model → 512-dim float32 embedding
7. L2-normalize embedding
8. Build metadata dict (common + image-specific fields)
9. Upsert to collection via connection.add/upsert
```

#### Per-document pipeline

Text extraction is dispatched by extension:

| Extension | Extraction method |
|---|---|
| `.txt`, `.md`, `.log`, `.csv`, `.srt`, `.vtt`, `.py` | `open(path, encoding="utf-8", errors="replace").read()` |
| `.html`, `.xml` | `open()` read, then strip tags with a minimal regex (no external HTML parser) |
| `.pdf` | `pypdf.PdfReader(path)` — concatenate all page texts |
| `.docx` | `docx.Document(path)` from `python-docx` — join paragraph texts |

```
1. Validate file — readable, non-zero size, `is_text_file()` returns True (or extension is `.pdf`/`.docx`)
2. Compute MD5 hash of raw file bytes (`file_hash` / `parent_id`)
3. Check for duplicate — query collection for items with `parent_id=file_hash`:
   - If count == 0 → proceed (new file)
   - If count > 0 and count == stored `chunk_total` → fully ingested; skip unless `overwrite=True`
   - If count > 0 and count < stored `chunk_total` → **partial ingestion detected**; log a warning and re-ingest from scratch (delete existing partial chunks first, then proceed)
   - `overwrite=True` → delete all existing chunks for this `parent_id` unconditionally, then re-ingest
4. Extract full text using the appropriate method above
5. If extracted text is empty, record as error and skip (do not embed empty strings)
6. Compute `char_count`, `word_count` (and `page_count` for PDF) from full text
7. **Chunk** text into segments: split on `\n\n` first; hard-split any paragraph exceeding max chunk size at character boundary
8. Compute `chunk_total = len(chunks)` **before** starting any upsert (all chunks receive the same `chunk_total` value)
9. For each chunk:
   a. Run `SentenceTransformer.encode(chunk_text)` → 384-dim float32 embedding
   b. L2-normalize embedding
   c. Build metadata dict (common + document-specific fields: `chunk_index`, `chunk_total`, `parent_id`, `char_count`, `word_count`, `page_count`)
   d. Set `id = "{file_hash}-{chunk_index}"`
   e. Accumulate in batch buffer; flush via `connection.add/upsert` when `batch_size` chunks are ready
10. After all chunks are flushed, increment `IngestionResult.succeeded` and add chunk count to `chunks_written`
11. If any chunk upsert raises, record the file as failed, add to `errors`, delete any partially upserted chunks for this `parent_id` (best-effort cleanup)
```

**Chunk size:** 1 000 characters is the default, configurable via the "Max chunk size" spinner (range 200–4 096).

**Multi-document invariant:** `chunk_index` and `chunk_total` are always scoped **per source document**, not globally across a batch. Two documents each producing 10 chunks both have `chunk_total=10` and `chunk_index` 0–9. Uniqueness is guaranteed by `id = "{file_hash}-{chunk_index}"` since `file_hash` differs per document.

**Single vs. multi-document:** the pipeline is identical for both. A single-document ingest is just `ingest_files([path], ...)` with one file in the list. `IngestionResult.total` will be 1 and `chunks_written` will reflect that document’s chunk count.

Batching: accumulate up to `batch_size` chunks (not files) before calling upsert to reduce round-trips.

---

### UI Entry Points

Two separate menu items under **File → Import**:

| Action | Menu item |
|---|---|
| Image ingestion | `File → Import → Import Images…` |
| Document ingestion | `File → Import → Import Documents…` |

Both follow the same dialog flow:

1. **File picker** — `QFileDialog.getExistingDirectory` (folder mode) **or** `QFileDialog.getOpenFileNames` (multi-file, filtered to the relevant extensions)
2. **Config dialog** — collection selector dropdown (filtered to dimension-compatible collections: 512 for images, 384 for documents), "Include subfolders" checkbox, "Overwrite duplicates" checkbox, batch size spinner
   - For documents: additional **"Max chunk size"** spinner (default 1 000 chars, range 200–4 096)
   - **"+ New collection" button** next to the dropdown — opens an inline mini-dialog:
     - Name field (validated: non-empty, no special chars)
     - Dimension field — pre-filled to 512 (image mode) or 384 (document mode), editable
     - "Create" button calls `connection.create_collection(name, dimension)` and then selects the new collection in the dropdown
     - On success the mini-dialog closes and the new collection is pre-selected; on failure a `QMessageBox.warning` is shown
3. **Run** — via `ThreadedTaskRunner` with `LoadingDialog` showing per-file progress
4. **Completion** — `QMessageBox` with summary (e.g., `"Ingested 12 documents. 1 skipped (duplicate). 0 failed."`)
5. **Refresh** — metadata view reloads if the current collection matches

---

### Dependencies

`transformers`, `Pillow`, and `sentence-transformers` are optional deps; add `torch` (CPU-only), `pypdf`, and `python-docx` if not already present.

All must be added via `pdm add` and accessed through `lazy_imports.py`:

```
pdm add torch --group optional
pdm add transformers --group optional
pdm add Pillow --group optional
pdm add sentence-transformers --group optional
pdm add pypdf --group optional
pdm add python-docx --group optional
```

| Dependency | Used for |
|---|---|
| `torch` | CLIP and sentence-transformers inference backend |
| `transformers` | CLIP model + processor |
| `Pillow` | Image decoding (image pipeline) |
| `sentence-transformers` | Text embedding model |
| `pypdf` | PDF text extraction |
| `python-docx` | Word `.docx` text extraction |

If a required dependency is missing at runtime, the ingestion service raises a `LazyImportError` with a user-friendly message pointing to the relevant `pdm add` command.

---

### Re-ingest File Action

A **"Re-ingest file"** context menu action appears in the metadata table when the selected item has a `file_path` metadata field pointing to an existing file.

**Location:** Right-click context menu in the metadata table, grouped alongside future per-item actions. The menu entry reads `"Re-ingest file…"` and is disabled (greyed out) if `file_path` is absent or the file no longer exists.

**Behavior:**
1. Resolve `file_path` from the item's metadata.
2. Determine pipeline type from `file_type` metadata field (`"image"` or `"document"`); fall back to `file_type(path)` from `file_preview_utils` if the field is missing.
3. Show a small confirmation dialog: `"Re-ingest [filename]? This will overwrite the existing embedding and metadata."`
4. Call `FileIngestionService.ingest_files([file_path], ..., overwrite=True)` via `ThreadedTaskRunner`.
5. On completion, refresh the item row in the table (re-fetch from the collection).

**Affected files:**

| File | Change |
|---|---|
| `src/vector_inspector/ui/views/metadata/metadata_table.py` | Add "Re-ingest file…" context menu item |
| `src/vector_inspector/services/file_ingestion_service.py` | `overwrite: bool = False` parameter on `ingest_files`; when `True`, skip the hash-duplicate check |

---

### Testing

- `tests/services/test_file_ingestion_service.py`

  **Image pipeline:**
  - Mock the CLIP model and processor (return deterministic 512-dim fake embeddings)
  - Test: folder scan finds correct image files, skips non-images and unsupported extensions
  - Test: duplicate detection (hash match → skipped)
  - Test: batch accumulation sends correct number of upsert calls
  - Test: `IngestionResult` counts correct on mixed success/failure input
  - Test: corrupt/unreadable image recorded in `errors`, does not abort the batch

  **Document pipeline:**
  - Mock `SentenceTransformer.encode` (return deterministic 384-dim fake embeddings)
  - Test: plain `.txt` file extracted and embedded correctly
  - Test: `.ts` / `.rb` source file accepted via `is_text_file()` dynamic detection
  - Test: `.pdf` extraction via mocked `pypdf.PdfReader`
  - Test: `.docx` extraction via mocked `python-docx`
  - Test: empty extracted text → skipped with error entry, does not call encode
  - Test: paragraph-aware chunking — text with `\n\n` splits into correct chunk count
  - Test: hard-split on oversized paragraph — chunk never exceeds max chunk size
  - Test: `chunk_index` / `chunk_total` / `parent_id` values are correct across all chunks of a file
  - Test: `chunk_total` is identical on every chunk of the same document
  - Test: `id` format is `"{file_hash}-{chunk_index}"`
  - Test: **multi-document batch** — two documents with different hashes produce non-overlapping `id` sets; each document’s `chunk_index` starts at 0 independently
  - Test: **single-document ingestion** — `ingest_files([path])` produces correct `IngestionResult.total=1` and correct `chunks_written`
  - Test: **partial ingestion recovery** — collection contains `n < chunk_total` chunks for a `parent_id`; pipeline deletes them and re-ingests from scratch
  - Test: duplicate detection — file with all chunks already present (`count == chunk_total`) skipped when `overwrite=False`
  - Test: `overwrite=True` deletes existing chunks before re-ingesting
  - Test: upsert failure mid-document — partial chunks cleaned up, file recorded as failed, next file continues
  - Test: unsupported extension skipped with error entry
  - Test: `IngestionResult` counts files (not chunks); `chunks_written` reflects total chunk items upserted

  **Re-ingest action:**
  - Test: `overwrite=True` bypasses the duplicate check and calls upsert
  - Test: `overwrite=False` (default) skips on hash match

---

## Shared Considerations

### common: `file_preview_utils.py` ↔ ingestion

`IMAGE_EXTENSIONS`, `is_text_file()`, `file_type()`, and path-canonicalization helpers are shared between both features. Define them once in `file_preview_utils.py` and import from there in `file_ingestion_service.py`. `TEXT_EXTENSIONS` is removed — text classification is now dynamic via `is_text_file()`, so no extension allowlist needs to be maintained.

### Release Notes

Both features should be recorded in `docs/RELEASE_REASON.md` under:

```
## UI
- File preview panel in entry view: images and text files render inline when a path is detected in metadata
- "Preview available" icon column in the metadata table signals entries that have a file preview
- "Reveal in Finder / Show in Explorer" right-click action on file preview widgets
- "Re-ingest file…" context menu action refreshes embedding and metadata for a single item

## Providers / Ingestion
- New image ingestion pipeline: embed a folder of images with CLIP (512-dim) and write directly to any connected collection
- New document ingestion pipeline: embed text files, PDFs, and Word documents with sentence-transformers (384-dim) and write to any connected collection
- Ingestion dialogs include a "+ New collection" button to create a dimension-matched collection inline
```

---

## Open Questions

1. ~~**Free vs. Premium boundary**~~ — **Resolved.** Basic local-model ingestion (CLIP + all-MiniLM-L6-v2) is free-tier; cloud/custom model support is premium.

2. ~~**Preview in `ItemDetailsDialog` too, or `InlineDetailsPane` only?**~~ — **Resolved.** Both. Inline pane uses a compact constrained size (160×120 px image, 100 px text). `ItemDetailsDialog` uses larger sizes with a "Full size" / "Fit" toggle for images.

3. ~~**Model caching**~~ — **Resolved.** Download on first use with a progress indicator; add a "Download models" action to settings. Detect and reuse a local path (e.g., `rag-lab/models/all-MiniLM-L6-v2/`) if configured.

4. ~~**Collection creation**~~ — **Resolved.** "+ New collection" button added directly to the ingestion config dialog (see UI Entry Points). Dimension is pre-filled and editable.

5. ~~**Max preview pane width**~~ — **Resolved.** Read `pane.width()` at render time and scale accordingly; 160 px is the inline default, `min(dialog_width - padding, 640)` for the dialog.

6. ~~**Document chunking**~~ — **Resolved.** Chunking is the v1 default (not truncation). Documents are split into segments of up to 1 000 characters (paragraph-aware, hard-split fallback). Each chunk carries `chunk_index`, `chunk_total`, and `parent_id` (= `file_hash` of the source file). `id` is `"{file_hash}-{chunk_index}"`.

7. ~~**`.doc` (legacy Word) support**~~ — **Resolved.** Skip `.doc` files with a clear error message suggesting conversion to `.docx`. Future enhancement if `antiword` or LibreOffice integration becomes feasible.

8. ~~**HTML/XML stripping quality**~~ — **Resolved.** Accept the regex tradeoff in v1. Add an opt-in `beautifulsoup4` path behind a lazy import if quality proves insufficient.

---
