#!/bin/bash
# Run Vector Inspector with cleared Python cache (for development)

cd "$(dirname "$0")/.."

echo "🧹 Clearing Python bytecode cache..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
echo "✓ Cache cleared"

echo "🚀 Starting Vector Inspector..."
cd src
pdm run python -m vector_inspector.main "$@"
