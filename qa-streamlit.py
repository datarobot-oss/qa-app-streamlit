#
#  Copyright 2024 DataRobot, Inc. and its affiliates.
#
#  All rights reserved.
#  This is proprietary source code of DataRobot, Inc. and its affiliates.
#  Released under the terms of DataRobot Tool and Utility Agreement.
#
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import backoff
import dr_components as dr_st
import requests
import streamlit as st
from datarobot import Client
from datarobot import Deployment
from datarobot.client import set_client
from dr_components.utils import (
    remove_markdown_space,
    remove_main_container_overflow,
    enable_custom_component_callbacks,
    move_st_sidebar_right,
)

st.set_page_config(layout="wide", initial_sidebar_state='expanded')

API_URL = '{base_url}/predApi/v1.0/deployments/{deployment_id}/predictions'  # noqa

logger = logging.getLogger(__name__)

token = os.getenv("token")
endpoint = os.getenv("endpoint")
custom_metric_id = os.getenv("custom_metric_id") or os.getenv("mlops_runtime_param_custom_metric_id") or None
deployment_id = os.getenv("deployment_id") or os.getenv("mlops_runtime_param_deployment_id") or None
app_base_url_path = os.getenv("app_base_url_path", None)
app_id = None
if app_base_url_path is not None:
    app_id = app_base_url_path.split('/')[-1].strip()

# Don't change this. It is enforced server-side too.
MAX_PREDICTION_FILE_SIZE_BYTES = 52428800  # 50 MB

# If you have additional information to show in a sidebar, you can enable it here
SHOW_SIDEBAR = False

# Static current user info
user_name = "You"
user_id = "1"
user_gravatar_url = "https://www.gravatar.com/avatar/?d=mp"

# Timeouts
CUSTOM_METRIC_SUBMIT_TIMEOUT_SECONDS = 60
PREDICTIONS_TIMEOUT_SECONDS = 60

# Default values for retrying failed requests
RETRY_COUNT = 100
RETRY_DEFAULT_WAIT_SEC = 15
RETRY_STATUS_CODES = {502, 504}

# In this case we should wait for Retry-After header
RETRY_AFTER_STATUS_CODES = {503}

class DataRobotPredictionError(Exception):
    """Raised if there are issues getting predictions from DataRobot"""


def process_citations(input_dict: dict[str: Any]) -> list[dict[str: Any]]:
    """Processes citation data"""

    output_list = []
    num_citations = len([k for k in input_dict.keys() if k.startswith("CITATION_CONTENT")])

    for i in range(num_citations):
        citation_content_key = f"CITATION_CONTENT_{i}"
        citation_source_key = f"CITATION_SOURCE_{i}"
        citation_page_key = f"CITATION_PAGE_{i}"

        citation_dict = {
            "page_content": input_dict[citation_content_key],
            "metadata": {
                "source": input_dict[citation_source_key],
                "page": input_dict[citation_page_key]
            },
            "type": "Document"
        }

        output_list.append(citation_dict)
    return output_list


@backoff.on_predicate(
    backoff.runtime,
    predicate=lambda r: r.status_code in RETRY_AFTER_STATUS_CODES,
    value=lambda r: int(r.headers.get("Retry-After", RETRY_DEFAULT_WAIT_SEC)),
    max_time=RETRY_COUNT * RETRY_DEFAULT_WAIT_SEC,
    max_tries=RETRY_COUNT,
    jitter=None,
    logger=logger,
)
@backoff.on_predicate(
    backoff.fibo,
    predicate=lambda r: r.status_code in RETRY_STATUS_CODES,
    max_tries=RETRY_COUNT,
    max_time=RETRY_COUNT * RETRY_DEFAULT_WAIT_SEC,
    jitter=None,
    logger=logger,
)
@backoff.on_exception(
    backoff.fibo,
    requests.Timeout,
    max_tries=RETRY_COUNT,
    max_time=RETRY_COUNT * RETRY_DEFAULT_WAIT_SEC,
    logger=logger,
)
def post_prediction(url, data, headers):
    return requests.post(
        url,
        data=data,
        headers=headers,
        timeout=PREDICTIONS_TIMEOUT_SECONDS,
    )


def make_datarobot_deployment_predictions(data, deployment):
    """
    Make predictions on data provided using DataRobot deployment_id provided.
    See docs for details:
         https://docs.datarobot.com/en/docs/api/reference/predapi/dr-predapi.html

    Parameters
    ----------
    data : str
        if using JSON as input:
        [{"Feature1":numeric_value,"Feature2":"string"}]

    deployment : Deployment
        The deployment to make predictions with.

    Returns
    -------
    Response schema:
        https://docs.datarobot.com/en/docs/api/reference/predapi/dr-predapi.html#response-schema

    Raises
    ------
    DataRobotPredictionError if there are issues getting predictions from DataRobot
    """
    # Set HTTP headers. The charset should match the contents of the file.
    headers = {
        'Content-Type': 'application/json; charset=UTF-8',
        'Authorization': 'Bearer {}'.format(token),
    }

    prediction_environment = deployment.prediction_environment or {}
    is_serverless_deployment = prediction_environment.get('platform') == 'datarobotServerless'

    serverless_prediction_url = f'{endpoint}/deployments/{deployment.id}/predictions'

    if deployment.default_prediction_server:
        headers['DataRobot-Key'] = deployment.default_prediction_server.get('datarobot-key')
        base_url = deployment.default_prediction_server['url']
    else:
        base_url = '{uri.scheme}://{uri.netloc}/'.format(uri=urlparse(endpoint))

    general_prediction_url = API_URL.format(
        base_url=base_url,
        deployment_id=deployment.id
    )

    url = serverless_prediction_url if is_serverless_deployment else general_prediction_url

    # Make API request for predictions
    predictions_response = post_prediction(url, data, headers)

    _raise_dataroboterror_for_status(predictions_response)
    # Return a Python dict following the schema in the documentation
    return predictions_response.json()


def _raise_dataroboterror_for_status(response):
    """Raise DataRobotPredictionError if the request fails along with the response returned"""
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        err_msg = '{code} Error: {msg}'.format(
            code=response.status_code, msg=response.text)
        raise DataRobotPredictionError(err_msg)


def get_deployment():
    if 'deployment' not in st.session_state:
        deployment = Deployment.get(deployment_id)
        st.session_state.deployment = deployment

    return st.session_state.deployment


def get_application_info():
    if app_id is None:
        # Fallback for local development
        st.session_state.app_info = {}

    if "app_info" not in st.session_state:
        # Set HTTP headers. The charset should match the contents of the file.
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
            'Authorization': 'Bearer {}'.format(token),
        }
        url = f"{endpoint}/customApplications/{app_id}/"

        response = requests.get(url, headers=headers, timeout=30)

        _raise_dataroboterror_for_status(response)

        st.session_state.app_info = response.json()

    return st.session_state.app_info


def submit_metric(deployment: Deployment, metric_id: str, value: float, a_id: str):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Token {}".format(token),
    }

    submit_url = f"{endpoint}/deployments/{deployment.id}/customMetrics/{metric_id}/fromJSON/"
    get_url = f"{endpoint}/deployments/{deployment.id}/customMetrics/{metric_id}/"
    custom_metric_response = requests.get(get_url, headers=headers, timeout=CUSTOM_METRIC_SUBMIT_TIMEOUT_SECONDS)
    _raise_dataroboterror_for_status(custom_metric_response)
    custom_metric = custom_metric_response.json()

    ts = datetime.utcnow()
    rows = [{"timestamp": ts.isoformat(), "value": value, "associationId": a_id}]
    data = {
        "buckets": rows,
    }
    if custom_metric.get('isModelSpecific'):
        data['modelId'] = deployment.model['id']

    serialised_data = json.dumps(data)
    requests.post(submit_url, data=serialised_data, headers=headers, timeout=CUSTOM_METRIC_SUBMIT_TIMEOUT_SECONDS)


def handle_feedback_request(prompt_id, value, message, deployment: Deployment):
    if value == 1:
        if user_id not in message['feedbackResult']['positiveUserIds']:
            message['feedbackResult']['positiveUserIds'].append(user_id)
        if user_id in message['feedbackResult']['negativeUserIds']:
            message['feedbackResult']['negativeUserIds'].remove(user_id)
        if custom_metric_id:
            submit_metric(deployment, custom_metric_id, value, prompt_id)
    if value == 0:
        if user_id not in message['feedbackResult']['negativeUserIds']:
            message['feedbackResult']['negativeUserIds'].append(user_id)
        if user_id in message['feedbackResult']['positiveUserIds']:
            message['feedbackResult']['positiveUserIds'].remove(user_id)
        if custom_metric_id:
            submit_metric(deployment, custom_metric_id, value, prompt_id)


def on_chat_message_callback_handler(key, deployment):
    component_state = st.session_state.get(key)
    if 'callback' in component_state:
        callback_name, callback_values, *_ = component_state['callback'].values()

        if callback_name == 'send_feedback':
            prompt_id = callback_values.get('prompt_id')
            feedback_value = int(callback_values.get('feedback_value'))
            for message in st.session_state.messages:
                if message['id'] == prompt_id:
                    handle_feedback_request(prompt_id, feedback_value, message, deployment)


def make_prediction(prompt_id, prompt, deployment):
    deployment_association_id_settings = deployment.get_association_id_settings()
    association_id_names = deployment_association_id_settings.get("column_names")
    prompt_column_name = deployment.model.get('prompt', "promptText")
    prediction_error = None

    st.session_state.messages.append(
        {
            "id": prompt_id,
            "prompt": prompt,
            "result": None,
            "executionStatus": "RUNNING",
            "userId": user_id,
            "userName": user_name,
            "userAvatar": user_gravatar_url,
            "deploymentName": deployment.model.get("type"),
            "deploymentAvatar": "",
            "errorMessage": "",
            "resultMetadata": [],
            "feedbackResult": {"positiveUserIds": [], "negativeUserIds": []},
        }
    )

    predictions = {}
    data = {
        prompt_column_name: prompt,
    }

    if association_id_names:
        data["response"] = ""
        data[association_id_names[0]] = prompt_id

    json_data = json.dumps([data])
    data_size = sys.getsizeof(data)

    if data_size >= MAX_PREDICTION_FILE_SIZE_BYTES:
        st.write(
            ('Input file is too large: {} bytes. ' 'Max allowed size is: {} bytes.').format(
                data_size, MAX_PREDICTION_FILE_SIZE_BYTES
            )
        )
    try:
        predictions = make_datarobot_deployment_predictions(json_data, deployment)
    except Exception as exc:
        logging.error(exc)
        prediction_error = str(exc)

    response = predictions.get('data')
    prediction = response[0]['prediction'] if response else None

    extra_model_output = response[0].get('extraModelOutput', {}) if response else dict()
    citations = extra_model_output.get('datarobot_citations', {})
    result_references = process_citations(
        citations if citations else extra_model_output
    )

    if response or prediction_error:
        for message in st.session_state.messages:
            if message['id'] == prompt_id:
                if prediction and not prediction_error:
                    message['result'] = prediction
                    message['executionStatus'] = 'COMPLETED'
                    if extra_model_output.get("cost"):
                        message["resultMetadata"].append(
                            {
                                "key": "cost",
                                "name": "Cost",
                                "value": f'${extra_model_output.get("cost")}',
                            }
                        )
                    if extra_model_output.get("datarobot_token_count"):
                        message["resultMetadata"].append(
                            {
                                "key": "tokens",
                                "name": "Tokens",
                                "value": extra_model_output["datarobot_token_count"],
                            }
                        )
                    if extra_model_output.get("datarobot_latency"):
                        message["resultMetadata"].append(
                            {
                                "key": "latency",
                                "name": "Latency",
                                "value": f'{extra_model_output["datarobot_latency"]:.2f}s',
                            }
                        )
                    message["confidenceScore"] = str(extra_model_output.get('datarobot_confidence_score'))
                    message["citations"] = [{'text': doc['page_content'], 'source': doc['metadata']['source']} for doc
                                            in result_references] if result_references else None

                elif prediction_error:
                    message['executionStatus'] = 'ERROR'
                    message['errorMessage'] = 'Error: {msg}'.format(
                        msg=prediction_error
                    )
                    # We need this to display an error message as response
                    # TODO fix check for result
                    message['result'] = ' '


def on_send_prompt_handler(key, deployment):
    component_state = st.session_state.get(key)
    if 'callback' in component_state:
        callback_name, callback_values, *_ = component_state['callback'].values()

        if callback_name == 'send_prompt':
            prompt = list(callback_values.values())[0]
            prompt_id = str(uuid.uuid4())
            make_prediction(prompt_id, prompt, deployment)


def start_streamlit():
    # Setup DR client
    set_client(Client(endpoint=endpoint, token=token))

    deployment = get_deployment()
    app_info = get_application_info()

    # Create a message storage
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Prepare QA App layout for custom components
    remove_markdown_space()
    remove_main_container_overflow()
    enable_custom_component_callbacks()
    active_theme = dr_st.util_detect_theme()
    move_st_sidebar_right(theme=active_theme, apply_dr_style=True)
    bg_color = "#DEE3ED" if active_theme == "light" else "#1D2226"

    # Application header
    header_container_key = "header_container"
    with (dr_st.full_width_container(header_container_key, bg_color)):
        col1, col2 = st.columns(2)
        with col1:
            dr_st.info_section(
                title=app_info.get('name', "Untitled Application"),
                key="app_header_info",
                text=app_info.get('description', ""),
                title_class_name='heading-05 margin-top-2',
                text_class_name='body',
                bg_color=bg_color,
            )

        with col2:
            button_code_key = "action_view_code"
            button_share_key = "action_share_button"
            with dr_st.action_bar(
                    content_keys=[button_code_key, button_share_key],
                    justify_content='end',
                    key='qa_app_header_center',
                    add_right_padding=False,
            ):
                if app_info.get('externalAccessEnabled', False) and app_info.get('applicationUrl'):
                    dr_st.share_button(
                        url=app_info.get('applicationUrl'),
                        is_sharing_enabled=True,
                        key=button_share_key,
                        bg_color=bg_color,
                    )

    if SHOW_SIDEBAR:
        with st.sidebar:
            app_summary = (
                "An example text for this app"
            )

            dr_st.info_section(
                title="Model Info",
                text=app_summary,
                key="model-info-section",
                key_values_list=[
                    {"label": "Name", "value": "Chatbot"},
                    {"label": "Description", "value": "Docs chatbot"},
                    {"label": "Date created", "value": "March 21, 2024"},
                ],
                title_class_name="heading-06 margin-y-2",
            )

    with dr_st.fixed_width_container(width=800, key='main_container'):
        chat_history_key = "chat_history"
        dr_st.chat_history(
            st.session_state.messages,
            min_height=525,
            max_height=525,
            key=chat_history_key,
            on_change=on_chat_message_callback_handler,
            allow_feedback=bool(custom_metric_id),
            args=(
                chat_history_key,
                deployment
            ),
        )

        prompt_input_key = "prompt_input"
        dr_st.prompt_input(
            user_name,
            user_gravatar_url,
            key=prompt_input_key,
            on_change=on_send_prompt_handler,
            args=(prompt_input_key, deployment),
        )


if __name__ == "__main__":
    start_streamlit()
