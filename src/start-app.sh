#!/usr/bin/env bash
echo "Starting App"

export TOKEN="$DATAROBOT_API_TOKEN"
export ENDPOINT="$DATAROBOT_ENDPOINT"
export APP_BASE_URL_PATH="$STREAMLIT_SERVER_BASE_URL_PATH"

# If you have configured runtime params via DataRobots application source, the following 2 values should be set automatically.
# Otherwise you will need to set DEPLOYMENT_ID (required) and CUSTOM_METRIC_ID (optional) manually
if [ -n "$MLOPS_RUNTIME_PARAM_DEPLOYMENT_ID" ]; then
  export DEPLOYMENT_ID="$MLOPS_RUNTIME_PARAM_DEPLOYMENT_ID"
fi
if [ -n "$MLOPS_RUNTIME_PARAM_CUSTOM_METRIC_ID" ]; then
  export CUSTOM_METRIC_ID="$MLOPS_RUNTIME_PARAM_CUSTOM_METRIC_ID"
fi
if [ -n "$MLOPS_RUNTIME_PARAM_APP_NAME" ]; then
  export APP_NAME="$MLOPS_RUNTIME_PARAM_APP_NAME"
fi
if [ -n "$MLOPS_RUNTIME_PARAM_SYSTEM_PROMPT" ]; then
  export SYSTEM_PROMPT="$MLOPS_RUNTIME_PARAM_SYSTEM_PROMPT"
fi
if [ -n "$MLOPS_RUNTIME_PARAM_ENABLE_CHAT_API" ]; then
  export ENABLE_CHAT_API="$MLOPS_RUNTIME_PARAM_ENABLE_CHAT_API"
fi
if [ -n "$MLOPS_RUNTIME_PARAM_ENABLE_CHAT_API_STREAMING" ]; then
  export ENABLE_CHAT_API_STREAMING="$MLOPS_RUNTIME_PARAM_ENABLE_CHAT_API_STREAMING"
fi

streamlit-sal compile
streamlit run --server.port=8080 qa_chat_bot.py