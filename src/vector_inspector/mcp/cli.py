"""Console entry point for the Vector Inspector MCP server.

Follows the ``_cli.py`` pattern: argument parsing happens before any
``vector_inspector`` import, so the process never touches Qt. The
server speaks MCP over stdio; stdout is the protocol wire, so this
module never ``print()``s while serving (logging goes to stderr).
"""

import argparse
import logging
import os
import sys

# ONNX Runtime telemetry is ON by default (1.29+) and POSTs trace
# events — including a persistent device ID — to Microsoft's 1DS
# backend. The only reliable opt-out is ORT_DISABLE_TELEMETRY=1 set
# before ONNX Runtime initializes; the library's
# disable_telemetry_events() call does not stop it. Set it here, at
# module import, so it is in place before any import in this process
# can pull in ONNX Runtime (via fastembed or a provider's default
# embedding). setdefault keeps an explicit user setting: setting
# ORT_DISABLE_TELEMETRY=0 opts back in.
os.environ.setdefault("ORT_DISABLE_TELEMETRY", "1")

GITHUB_URL = "https://github.com/anthonypdawson/vector-inspector"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="vector-inspector-mcp",
        description=(
            "Vector Inspector MCP server — inspect, search, and manage "
            "vector databases (ChromaDB, Qdrant, Pinecone, LanceDB, "
            "pgvector, Weaviate, Milvus) through one MCP tool surface.\n"
            "\n"
            "Connections are named with repeatable --connection specs:\n"
            "  name@provider?key=value&key=value\n"
            "Secrets are given as env:VARNAME and resolved from the\n"
            "environment at connect time; they are never written in a spec.\n"
            "\n"
            "Connections saved in the desktop GUI are also loaded\n"
            "automatically from ~/.vector-inspector/profiles.json, and a\n"
            "profile saved in the GUI mid-session is usable without\n"
            "restarting. A launch spec wins when it shares a profile's\n"
            "name. Profile credentials resolve from the environment\n"
            "first, then the OS keychain entry the GUI wrote.\n"
            "\n"
            "Examples:\n"
            "  vector-inspector-mcp \\\n"
            "    --connection local@chromadb?type=persistent&path=./chroma \\\n"
            "    --connection lance@lancedb?path=./lancedb\n"
            "  vector-inspector-mcp --connection pine@pinecone?api_key=env:PINECONE_API_KEY\n"
            "\n"
            "VI_MCP_CONNECTIONS holds semicolon-separated specs as well;\n"
            "--connection wins on name conflicts."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"For problems, visit: {GITHUB_URL}",
    )
    parser.add_argument(
        "--connection",
        action="append",
        default=[],
        metavar="SPEC",
        help="Named connection spec (repeatable): name@provider?key=value&key=value",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Block all mutating tools (add/update/delete items, create/delete collections).",
    )
    parser.add_argument(
        "--log-level",
        metavar="LEVEL",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        type=str.upper,
        default="WARNING",
        help="Log level for stderr logging (default: WARNING).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.8.4",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    """Parse args, force telemetry off, and serve MCP over stdio."""
    args = _build_parser().parse_args(argv)

    # Telemetry is forced off in this process (the server also
    # neutralises TelemetryService.send_event at startup; this env
    # var honours the desktop CLI's own convention).
    os.environ["VI_NO_TELEMETRY"] = "1"

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Imports happen after arg parsing and env setup, mirroring _cli.py:
    # nothing in this path imports Qt.
    from vector_inspector.mcp.config import load_configs
    from vector_inspector.mcp.profiles import GuiProfiles
    from vector_inspector.mcp.server import create_server

    try:
        configs = load_configs(args.connection)
    except ValueError as exc:
        sys.stderr.write(f"vector-inspector-mcp: {exc}\n")
        raise SystemExit(2) from exc

    profiles = GuiProfiles()
    profile_configs = profiles.load()

    if not configs and not profile_configs:
        logger.warning(
            "No connections configured. Pass --connection specs, set "
            "VI_MCP_CONNECTIONS, or save a connection in the desktop "
            "GUI; vi_list_providers still works."
        )

    server = create_server(configs, read_only=args.read_only, profiles=profiles)
    # create_server() imports the provider layer, which pins the
    # "vector_inspector" parent logger to WARNING (see core/logging)
    # and adds its own handler alongside basicConfig's root handler.
    # Restore the level this process was asked for (or the startup
    # line below is silently swallowed) and stop the record
    # propagating to root (or it prints twice, once per handler).
    logger.setLevel(getattr(logging, args.log_level))
    logging.getLogger("vector_inspector").propagate = False
    logger.info(
        "Serving %d connection(s) over stdio (read_only=%s)",
        len(set(configs) | set(profile_configs)),
        args.read_only,
    )
    try:
        server.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Interrupted; shutting down")
    finally:
        # Best-effort disconnect; the registry is owned by the server
        # closure, so reach it through the tools is unnecessary — the
        # process is exiting and connections close with it.
        pass


if __name__ == "__main__":
    main()
