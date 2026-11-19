"""Gate test: the provider layer and the MCP server must import without PySide6.

This is the spike's acceptance criterion, kept permanently. It runs
the imports in a subprocess with PySide6 blocked (``sys.modules``
poisoning), so it is meaningful even in environments where PySide6
*is* installed — the child process proves the import path never
touches Qt.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

REPO_ROOT = Path(__file__).resolve().parents[1]

# The child blocks PySide6 outright, then imports the provider layer
# and the MCP server and lists the server's tools. Any Qt import
# anywhere on that path raises ModuleNotFoundError and fails the test.
_CHILD_SCRIPT = r"""
import asyncio
import json
import sys

# Poison PySide6: any import of it (or a submodule) must fail.
sys.modules["PySide6"] = None

from vector_inspector.core.connections.base_connection import VectorDBConnection
from vector_inspector.core.provider_factory import ProviderFactory
from vector_inspector.mcp.cli import main as cli_main
from vector_inspector.mcp.config import parse_connection_spec
from vector_inspector.mcp.server import create_server

assert "PySide6" not in sys.modules or sys.modules["PySide6"] is None
assert "PySide6.QtCore" not in sys.modules

server = create_server({})
tools = asyncio.run(server.list_tools())
print(json.dumps({"tools": sorted(t.name for t in tools)}))
"""


def test_provider_layer_and_mcp_server_import_without_pyside6():
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    # Make sure the child cannot inherit a Qt platform from the parent.
    env.pop("QT_QPA_PLATFORM", None)
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD_SCRIPT],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert proc.returncode == 0, (
        f"Import without PySide6 failed.\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
    )
    tools = json.loads(proc.stdout.strip().splitlines()[-1])["tools"]
    expected = [
        "vi_add_items",
        "vi_collection_info",
        "vi_connect",
        "vi_connection_info",
        "vi_create_collection",
        "vi_delete_collection",
        "vi_delete_items",
        "vi_get_items",
        "vi_list_collections",
        "vi_list_connections",
        "vi_list_providers",
        "vi_search",
        "vi_update_items",
    ]
    assert tools == expected


# Importing the MCP CLI must set ORT_DISABLE_TELEMETRY=1 by default,
# before any ONNX Runtime import: ONNX Runtime 1.29+ ships telemetry
# ON by default on Linux and POSTs to Microsoft's 1DS backend. An
# explicit user setting (e.g. =0 to opt back in) is respected.
_CHILD_TELEMETRY_SCRIPT = r"""
import os

import vector_inspector.mcp.cli  # noqa: F401  (sets ORT_DISABLE_TELEMETRY)

print(os.environ.get("ORT_DISABLE_TELEMETRY"))
"""


def _run_cli_telemetry_child(preset):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    env.pop("QT_QPA_PLATFORM", None)
    if preset is None:
        env.pop("ORT_DISABLE_TELEMETRY", None)
    else:
        env["ORT_DISABLE_TELEMETRY"] = preset
    proc = subprocess.run(
        [sys.executable, "-c", _CHILD_TELEMETRY_SCRIPT],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert proc.returncode == 0, (
        f"CLI telemetry child failed.\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
    )
    return proc.stdout.strip()


def test_cli_disables_onnx_telemetry_by_default():
    assert _run_cli_telemetry_child(preset=None) == "1"


def test_cli_respects_explicit_telemetry_opt_in():
    assert _run_cli_telemetry_child(preset="0") == "0"
