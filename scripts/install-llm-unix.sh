#!/usr/bin/env bash
set -euo pipefail

EXTRA_INDEX=${EXTRA_INDEX:-"https://abetlen.github.io/llama-cpp-python/whl/cpu"}
PACKAGE=${PACKAGE:-"llama-cpp-python"}
PREFER_BINARY=${PREFER_BINARY:-"--prefer-binary"}

echo "Installing $PACKAGE (prefer binary where available)"

if command -v pip >/dev/null 2>&1; then
  PIP_CMD=pip
elif command -v pip3 >/dev/null 2>&1; then
  PIP_CMD=pip3
else
  echo "No pip found on PATH. Activate your Python venv or install pip." >&2
  exit 1
fi

$PIP_CMD install $PACKAGE $PREFER_BINARY --extra-index-url $EXTRA_INDEX

echo "Done. Verify with: python -c 'import llama_cpp; print("ok")'"
