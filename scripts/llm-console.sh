#!/bin/bash
# Run Vector Viewer application

cd "$(dirname "$0")/.."
cd src
pdm run vector-inspector --llm-console
