#!/usr/bin/env bash
set -euo pipefail

# Ensure we're in the script's directory so streamlit-sal can find .streamlit-sal
cd "$(dirname "$0")"

echo "Starting App"
# Compile SAL stylesheet; fall back to the committed CSS if the platform can't compile
streamlit-sal compile 2>/dev/null || echo "streamlit-sal compile skipped — using pre-compiled CSS"
streamlit run --server.port=8080 qa_chat_bot.py
