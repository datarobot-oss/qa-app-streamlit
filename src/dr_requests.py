import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional

import pandas as pd
import requests
import streamlit as st
from datarobot.models.deployment import CustomMetric
from datarobot_predict.deployment import predict

from constants import CUSTOM_METRIC_SUBMIT_TIMEOUT_SECONDS, MAX_PREDICTION_INPUT_SIZE_BYTES, STATUS_ERROR, \
    STATUS_COMPLETED, DEFAULT_PROMPT_COLUMN_NAME, DEFAULT_RESULT_COLUMN_NAME, CAPABILITIES_TIMEOUT_SECONDS, \
    CHAT_CAPABILITIES_KEY, ENABLE_CHAT_API_STREAMING
from utils import get_deployment, raise_datarobot_error_for_status, process_citations, rename_dataframe_columns, \
    get_association_id_column_name, strip_metadata_from_messages, set_result_message_state


@st.cache_data(show_spinner=False)
def get_has_chat_api_support(deployment_id, token, endpoint):
    url = f"{endpoint}/deployments/{deployment_id}/capabilities/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Token {}".format(token),
    }

    has_chat_api_support = False
    try:
        response = requests.get(url, headers=headers, timeout=CAPABILITIES_TIMEOUT_SECONDS).json()
        chat_capabilities = next((item for item in response['data'] if item['name'] == CHAT_CAPABILITIES_KEY), {})
        has_chat_api_support = chat_capabilities.get('supported', False)
    except Exception as exc:
        logging.error(exc)

    return has_chat_api_support


def prediction_server_override_url() -> Optional[str]:
    """
    Because of the way internal networking is set up for on-prem and ST SAAS networks,
    we need to use the service URL instead of the external URL.
    """
    if os.environ.get("DATAROBOT_ENDPOINT") == 'http://datarobot-nginx/api/v2/':
        return 'http://datarobot-prediction-server:80/predApi/v1.0/'
    else:
        return None


def submit_metric(meta_id, message_meta, value):
    deployment = get_deployment()
    endpoint = st.session_state.endpoint
    custom_metric_id = st.session_state.custom_metric_id
    custom_metric = CustomMetric.get(deployment_id=deployment.id, custom_metric_id=custom_metric_id)

    # Return early if the same feedback was submitted already
    if message_meta.get("feedback_value") == value:
        return

    message_meta['feedback_value'] = value
    url = f"{endpoint}/deployments/{deployment.id}/customMetrics/{custom_metric_id}/fromJSON/"

    ts = datetime.utcnow()
    rows = [{"timestamp": ts.isoformat(), "value": value, "associationId": meta_id}]
    data = {
        "buckets": rows,
    }
    if custom_metric.is_model_specific:
        data['modelId'] =  deployment.model['id']
    serialised_data = json.dumps(data)
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Token {}".format(st.session_state.token),
    }
    requests.post(url, data=serialised_data, headers=headers, timeout=CUSTOM_METRIC_SUBMIT_TIMEOUT_SECONDS)


def send_predict_request(message):
    deployment = get_deployment()
    # Force prompt to be string using quotes, simply setting the type will get re-cast in transit
    prompt = f"'{message['content']}'"
    meta_id = message['meta_id']
    association_id_column_name = get_association_id_column_name()
    prompt_column_name = deployment.model.get('prompt', DEFAULT_PROMPT_COLUMN_NAME)
    result_column_name = deployment.model.get('target_name', DEFAULT_RESULT_COLUMN_NAME)

    data_tuples = [
        (association_id_column_name, meta_id) if association_id_column_name is not None else None,
        (prompt_column_name, prompt),
    ]
    data = dict(filter(lambda item: item is not None, data_tuples))
    data_size = sys.getsizeof(data)

    if data_size >= MAX_PREDICTION_INPUT_SIZE_BYTES:
        st.write(
            ('Prompt input is too large: {} bytes. ' 'Max allowed size is: {} bytes.').format(
                data_size, MAX_PREDICTION_INPUT_SIZE_BYTES
            )
        )

    input_df = pd.DataFrame(data, index=[0])
    prediction = None
    prediction_error = None
    processed_citations = None

    try:
        result_df, response_headers = predict(deployment, input_df, prediction_endpoint=prediction_server_override_url())
        processed_df = rename_dataframe_columns(result_df)
        prediction = processed_df.to_dict(orient="records")[0]
        processed_citations = process_citations(prediction)
    except Exception as exc:
        logging.error(exc)
        prediction_error = str(exc)

    message_content = prediction[result_column_name] if not prediction_error else None
    status = STATUS_COMPLETED if not prediction_error else STATUS_ERROR
    set_result_message_state(meta_id, message_content, status, citations=processed_citations,
                             extra_model_output=prediction, error=prediction_error)


def send_stream_request(message):
    meta_id = message['meta_id']
    endpoint = st.session_state.endpoint
    deployment_id = st.session_state.deployment_id
    deployment = get_deployment()
    url = f"{endpoint}/deployments/{deployment_id}/chat/completions"
    headers = {
        "Authorization": "Token {}".format(st.session_state.token),
        "Content-Type": "application/json",
    }

    chat_completions_request = {
        "model": deployment.model.get("type"),
        "messages": strip_metadata_from_messages(st.session_state.messages),
        "stream": ENABLE_CHAT_API_STREAMING,
    }

    result = None
    prediction_error = None
    processed_citations = None
    message_content = ""
    chat_completion = requests.post(url, json=chat_completions_request, headers=headers, stream=True)
    for chunk in chat_completion.iter_lines():
        try:
            # Strip "data: " and parse JSON content
            data_str = chunk.decode('utf-8').lstrip("data: ")
            data_json = json.loads(data_str)

            # Get completion content, e.g., choices[0].delta.content
            delta_content = data_json['choices'][0]['delta'].get('content') if ENABLE_CHAT_API_STREAMING else None
            if delta_content:
                message_content += delta_content
                yield delta_content

            # Check if this is the last chunk
            if data_json['choices'][0].get('finish_reason') == 'stop':
                try:
                    if not ENABLE_CHAT_API_STREAMING:
                        message = data_json['choices'][0].get('message')
                        message_content = message.get('content')
                    result = data_json.get('datarobot_moderations', None)
                    processed_citations = process_citations(result)
                except Exception as exc:
                    logging.error(exc)
                    prediction_error = str(exc)

                message_content = message_content if not prediction_error else None
                status = STATUS_COMPLETED if not prediction_error else STATUS_ERROR
                set_result_message_state(meta_id, message_content, status, citations=processed_citations,
                                         extra_model_output=result, error=prediction_error)

        except json.JSONDecodeError:
            continue  # Skip chunks that aren’t valid JSON. Not sure if necessary as it does not yet send true partial chunks


@st.cache_data(show_spinner=False)
def get_application_info():
    if st.session_state.app_id is None:
        # Fallback for local development
        return {}

    # Set HTTP headers. The charset should match the contents of the file.
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer {}'.format(st.session_state.token),
    }
    url = f"{st.session_state.endpoint}/customApplications/{st.session_state.app_id}/"

    response = requests.get(url, headers=headers, timeout=30)

    raise_datarobot_error_for_status(response)
    return response.json()
