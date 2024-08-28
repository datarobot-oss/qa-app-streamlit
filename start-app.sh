#!/usr/bin/env bash
#
#  Copyright 2023 DataRobot, Inc. and its affiliates.
#
#  All rights reserved.
#  This is proprietary source code of DataRobot, Inc. and its affiliates.
#  Released under the terms of DataRobot Tool and Utility Agreement.
#
echo "Starting App"


export token="$DATAROBOT_API_TOKEN"
export endpoint="$DATAROBOT_ENDPOINT"
export custom_metric_id="$CUSTOM_METRIC_ID"
export deployment_id="$DEPLOYMENT_ID"
export mlops_runtime_param_custom_metric_id="$MLOPS_RUNTIME_PARAM_CUSTOM_METRIC_ID"
export mlops_runtime_param_deployment_id="$MLOPS_RUNTIME_PARAM_DEPLOYMENT_ID"
export app_base_url_path="$STREAMLIT_SERVER_BASE_URL_PATH"

streamlit run --server.port=8080 qa-streamlit.py