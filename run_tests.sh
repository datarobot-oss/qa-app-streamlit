#!/usr/bin/env bash

# Change to the src directory (SAL is looking for a root dir that has .streamlit_sal config
cd "$(dirname "$0")/src"

# Start the tests without changing current active dir
pytest ../tests/