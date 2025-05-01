#!/usr/bin/env bash

# Change to the src directory (SAL is looking for a root dir that has .streamlit_sal config
cd "$(dirname "$0")/src"

# Start the tests without changing current active dir. Streamlits 'AppTest' still leaks between test runs to we need to
# run each file separate
# Forward all arguments passed to this script to pytest commands
for file in ../tests/test_*.py; do
  echo "Running $file"
  pytest "$file" "$@" || exit 1
done