#!/usr/bin/env bash

set -e

echo "Installing Vector Inspector..."

# Ensure python3 exists
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python3 is required but not installed."
    exit 1
fi

# Install the package
python3 -m pip install --upgrade pip
python3 -m pip install --upgrade vector-inspector

echo "Type vector-inspector to launch the application."

echo "Launching Vector Inspector..."
vector-inspector &

