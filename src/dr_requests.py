import json
import logging
import sys
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
from datarobot.models.deployment import CustomMetric
from datarobot_predict.deployment import predict

from constants import CUSTOM_METRIC_SUBMIT_TIMEOUT_SECONDS, MAX_PREDICTION_INPUT_SIZE_BYTES, STATUS_ERROR, \
    STATUS_COMPLETED
from utils import get_deployment, raise_datarobot_error_for_status, process_citations, rename_dataframe_columns


def submit_metric(message, value):
    deployment = get_deployment()
    prompt_id = message.get("id")
    endpoint = st.session_state.endpoint
    custom_metric_id = st.session_state.custom_metric_id
    custom_metric = CustomMetric.get(deployment_id=deployment.id, custom_metric_id=custom_metric_id)

    # Return early if the same feedback was submitted already
    if message.get("feedback_value") == value:
        return

    message['feedback_value'] = value
    url = f"{endpoint}/deployments/{deployment.id}/customMetrics/{custom_metric_id}/fromJSON/"

    ts = datetime.utcnow()
    rows = [{"timestamp": ts.isoformat(), "value": value, "associationId": prompt_id}]
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


# TODO: Split non request code to util 'prepare request data'
def make_prediction(init_message):
    deployment = get_deployment()
    prompt = init_message['prompt']
    prompt_id = init_message['id']
    deployment_association_id_settings = deployment.get_association_id_settings()
    association_id_names = deployment_association_id_settings.get("column_names")
    prompt_column_name = deployment.model.get('prompt', "promptText")

    data_tuples = [
        (prompt_column_name, prompt),
        (association_id_names[0], prompt_id) if association_id_names is not None else None,
        ('response', '') if association_id_names is not None else None,
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
        result_df, response_headers = predict(deployment, input_df)
        processed_df = rename_dataframe_columns(result_df)
        prediction = processed_df.to_dict(orient="records")[0]
        processed_citations = process_citations(prediction)
    except Exception as exc:
        logging.error(exc)
        prediction_error = str(exc)

    if prediction or prediction_error:
        for message in st.session_state.messages:
            if message['id'] == prompt_id:
                if prediction and not prediction_error:
                    message['result'] = prediction['resultText']
                    message['execution_status'] = STATUS_COMPLETED
                    message["citations"] = [{'text': doc['page_content'], 'source': doc['metadata']['source']} for doc
                                            in processed_citations] if processed_citations else None

                    # Extra model output
                    if prediction.get('datarobot_latency'):
                        message['datarobot_latency'] = prediction['datarobot_latency']
                    if prediction.get('datarobot_token_count'):
                        message['datarobot_token_count'] = prediction['datarobot_token_count']
                    if prediction.get('datarobot_confidence_score'):
                        message['datarobot_confidence_score'] = prediction['datarobot_confidence_score']

                elif prediction_error:
                    message['execution_status'] = STATUS_ERROR
                    message['error_message'] = prediction_error


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
