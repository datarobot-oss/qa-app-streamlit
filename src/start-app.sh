#!/usr/bin/env bash
set -euo pipefail

echo "Starting App"
streamlit-sal compile
streamlit run --server.port=8080 qa_chat_bot.py
