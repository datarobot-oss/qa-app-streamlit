#!/usr/bin/env bash
set -euo pipefail

# Change to the src directory — SAL looks for .streamlit_sal config here,
# and uv reads pyproject.toml from this directory.
cd "$(dirname "$0")/src"

# Run each test file separately: Streamlit's AppTest leaks state between files.
for file in ../tests/test_*.py; do
  echo "Running $file"
  uv run pytest "$file" "$@" || exit 1
done
