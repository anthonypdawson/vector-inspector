"""Service for installing and uninstalling optional packages via pip.

Handles both database provider packages (chromadb, qdrant, …) and optional
feature-group packages (viz, embeddings, clip, documents).  All commands are
validated against an immutable registry before any subprocess is launched, so
arbitrary package names cannot be injected through user input.

Security note
-------------
``item_id`` is validated against ``_VALID_IDS`` before appearing in any
subprocess command.  Any unknown value raises ``ValueError`` immediately.
"""

import subprocess
import sys
from collections.abc import Callable
from typing import Optional

from vector_inspector.core.provider_detection import PROVIDERS
from vector_inspector.services.telemetry_service import TelemetryService

# ---------------------------------------------------------------------------
# Registries
# ---------------------------------------------------------------------------

_VALID_PROVIDER_IDS: frozenset[str] = frozenset(p["id"] for p in PROVIDERS)

_VALID_FEATURE_IDS: frozenset[str] = frozenset(["viz", "embeddings", "clip", "documents"])

# All IDs that may appear in a pip command.
_VALID_IDS: frozenset[str] = _VALID_PROVIDER_IDS | _VALID_FEATURE_IDS

# Versioned pip specs — used for display/tooltip purposes.
_PACKAGE_SPECS: dict[str, list[str]] = {
    # providers
    "chromadb": ["chromadb>=0.4.22"],
    "qdrant": ["qdrant-client>=1.7.0"],
    "pinecone": ["pinecone>=8.0.0"],
    "lancedb": ["lancedb>=0.27.0", "pyarrow>=14.0.0"],
    "pgvector": ["psycopg2-binary>=2.9.11", "pgvector>=0.4.2"],
    "weaviate": ["weaviate-client>=4.19.2"],
    "milvus": ["pymilvus>=2.6.8"],
    # feature groups
    "viz": ["scikit-learn>=1.3.0", "umap-learn>=0.5.5", "hdbscan>=0.8.41"],
    "embeddings": ["sentence-transformers>=2.2.0", "fastembed>=0.7.4", "hf-xet>=1.2.0"],
    "clip": ["torch>=2.0.0", "transformers>=4.40.0", "Pillow>=10.0.0"],
    "documents": ["pypdf>=4.0.0", "python-docx>=1.1.0"],
}

# Bare package names derived from specs — used for ``pip uninstall``.
_PACKAGES: dict[str, list[str]] = {
    item_id: [s.split(">")[0].split("=")[0].split("<")[0].split("!")[0] for s in specs]
    for item_id, specs in _PACKAGE_SPECS.items()
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _kind(item_id: str) -> str:
    """Return ``"provider"`` or ``"feature"`` for telemetry event naming."""
    return "provider" if item_id in _VALID_PROVIDER_IDS else "feature"


def _run_pip(
    cmd: list[str],
    on_output: Optional[Callable[[str], None]],
) -> tuple[int, str]:
    """Run a pip subprocess, streaming output lines.

    Returns ``(returncode, combined_output)``.  Returns ``(-1, error_msg)``
    when pip itself cannot be launched (``OSError``); in that case the caller
    should not emit telemetry since no install/uninstall was attempted.
    """
    output_lines: list[str] = []
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            output_lines.append(line)
            if on_output:
                on_output(line)
        process.wait()
        return process.returncode, "".join(output_lines)
    except OSError as exc:
        error_msg = f"Failed to launch pip: {exc}"
        if on_output:
            on_output(error_msg + "\n")
        return -1, error_msg


# ---------------------------------------------------------------------------
# Public API — install
# ---------------------------------------------------------------------------


def get_install_command(item_id: str) -> list[str]:
    """Return the subprocess argv list for installing a provider or feature.

    Args:
        item_id: A known provider or feature identifier (e.g. ``"chromadb"``,
            ``"viz"``).

    Returns:
        Command list suitable for ``subprocess.Popen``.

    Raises:
        ValueError: If ``item_id`` is not in the known registry.
    """
    if item_id not in _VALID_IDS:
        raise ValueError(f"Unknown provider or feature: {item_id!r}")
    return [sys.executable, "-m", "pip", "install", f"vector-inspector[{item_id}]"]


def install(
    item_id: str,
    on_output: Optional[Callable[[str], None]] = None,
) -> tuple[int, str]:
    """Install a provider or feature-group package using pip.

    Validates ``item_id`` against the known registry, then runs
    ``pip install vector-inspector[<item_id>]`` in a subprocess.
    Combined stdout+stderr is returned alongside the exit code.

    Args:
        item_id: A known provider or feature identifier (e.g. ``"chromadb"``,
            ``"viz"``).
        on_output: Optional callback invoked with each output line as it
            arrives.  Called from the calling thread.

    Returns:
        ``(returncode, combined_output)`` — ``returncode == 0`` means success.
        ``returncode == -1`` means pip could not be launched.

    Raises:
        ValueError: If ``item_id`` is not in the known registry.
    """
    cmd = get_install_command(item_id)
    returncode, output = _run_pip(cmd, on_output)
    if returncode >= 0:
        try:
            TelemetryService.send_event(
                f"{_kind(item_id)}.installed",
                {"metadata": {f"{_kind(item_id)}_id": item_id, "success": returncode == 0}},
            )
        except Exception:
            pass
    return returncode, output


# ---------------------------------------------------------------------------
# Public API — uninstall
# ---------------------------------------------------------------------------


def get_uninstall_command(item_id: str) -> list[str]:
    """Return the subprocess argv list for uninstalling a provider or feature.

    Args:
        item_id: A known provider or feature identifier (e.g. ``"chromadb"``,
            ``"viz"``).

    Returns:
        Command list suitable for ``subprocess.Popen``.

    Raises:
        ValueError: If ``item_id`` is not in the known registry.
    """
    if item_id not in _VALID_IDS:
        raise ValueError(f"Unknown provider or feature: {item_id!r}")
    packages = _PACKAGES.get(item_id, [])
    return [sys.executable, "-m", "pip", "uninstall", "-y", *packages]


def uninstall(
    item_id: str,
    on_output: Optional[Callable[[str], None]] = None,
) -> tuple[int, str]:
    """Uninstall a provider or feature-group's packages using pip.

    Validates ``item_id`` against the known registry, then runs
    ``pip uninstall -y <packages>`` in a subprocess.

    Args:
        item_id: A known provider or feature identifier (e.g. ``"chromadb"``,
            ``"viz"``).
        on_output: Optional callback invoked with each output line.

    Returns:
        ``(returncode, combined_output)`` — ``returncode == 0`` means success.
        ``returncode == -1`` means pip could not be launched.

    Raises:
        ValueError: If ``item_id`` is not in the known registry.
    """
    cmd = get_uninstall_command(item_id)
    returncode, output = _run_pip(cmd, on_output)
    if returncode >= 0:
        try:
            TelemetryService.send_event(
                f"{_kind(item_id)}.uninstalled",
                {"metadata": {f"{_kind(item_id)}_id": item_id, "success": returncode == 0}},
            )
        except Exception:
            pass
    return returncode, output
