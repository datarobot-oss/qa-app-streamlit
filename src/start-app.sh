#!/usr/bin/env bash
echo "Starting App"

export token="$DATAROBOT_API_TOKEN"
export endpoint="$DATAROBOT_ENDPOINT"
export app_base_url_path="$STREAMLIT_SERVER_BASE_URL_PATH"

# If you have configured runtime params via DataRobots application source, the following 2 values should be set automatically.
# Otherwise you will need to set DEPLOYMENT_ID (required) and CUSTOM_METRIC_ID (optional) manually
if [ -n "$MLOPS_RUNTIME_PARAM_DEPLOYMENT_ID" ]; then
  export deployment_id="$MLOPS_RUNTIME_PARAM_DEPLOYMENT_ID"
else
  export deployment_id="$DEPLOYMENT_ID"
fi
if [ -n "$MLOPS_RUNTIME_PARAM_CUSTOM_METRIC_ID" ]; then
  export custom_metric_id="$MLOPS_RUNTIME_PARAM_CUSTOM_METRIC_ID"
else
  export custom_metric_id="$CUSTOM_METRIC_ID"
fi
if [ -n "$MLOPS_RUNTIME_PARAM_APP_NAME" ]; then
  export app_name="$MLOPS_RUNTIME_PARAM_APP_NAME"
fi

streamlit-sal compile
streamlit run --server.port=8080 qa_chat_bot.py