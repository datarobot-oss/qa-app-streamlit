import logging
import os
import uuid
from typing import cast, Dict, Any

import requests
import streamlit as st
from datarobot import Deployment, AppPlatformError

from constants import STATUS_PENDING, ROLE_ASSISTANT


class DataRobotPredictionError(Exception):
    """Raised if there are issues getting predictions from DataRobot"""


def raise_datarobot_error_for_status(response):
    """Raise DataRobotPredictionError if the request fails along with the response returned"""
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        err_msg = '{code} Error: {msg}'.format(
            code=response.status_code, msg=response.text)
        raise DataRobotPredictionError(err_msg)


@st.cache_data(show_spinner=False)
def get_deployment():
    try:
        return Deployment.get(st.session_state.deployment_id)
    except AppPlatformError:
        logging.error('Failed to get deployment')
        return None


@st.cache_data(show_spinner=False)
def get_association_id_column_name():
    deployment = get_deployment()

    # The library typing sets the return value as <string>, but it actually returns a <dict>. Cast it here
    deployment_association_id_settings = cast(Dict[str, Any], deployment.get_association_id_settings())
    association_id_names = deployment_association_id_settings.get("column_names")
    return association_id_names[0] if association_id_names else None


def initiate_session_state():
    # Env variables
    if 'token' not in st.session_state:
        st.session_state.token = os.getenv("token")
    if 'endpoint' not in st.session_state:
        st.session_state.endpoint = os.getenv("endpoint")
    if 'custom_metric_id' not in st.session_state:
        st.session_state.custom_metric_id = os.getenv("custom_metric_id") or None
    if 'deployment_id' not in st.session_state:
        st.session_state.deployment_id = os.getenv("deployment_id") or None
    if 'app_id' not in st.session_state:
        app_base_url_path = os.getenv("app_base_url_path", None)
        st.session_state.app_id = app_base_url_path.split('/')[-1].strip() if app_base_url_path else None

    # Create messages storage on first render
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "messages_meta" not in st.session_state:
        st.session_state.messages_meta = {}

    if "pending_message_id" not in st.session_state:
        st.session_state.pending_message_id = None


def set_chat_api_session_state(is_chat_api_enabled):
    if 'is_chat_api_enabled' not in st.session_state or st.session_state.is_chat_api_enabled != is_chat_api_enabled:
        st.session_state.is_chat_api_enabled = is_chat_api_enabled


def add_new_prompt(prompt):
    new_prompt_id = str(uuid.uuid4())
    new_prompt = {"role": "user", "content": prompt, "meta_id": new_prompt_id}

    st.session_state.messages.append(new_prompt)
    st.session_state.messages_meta[new_prompt_id] = {
        'status': STATUS_PENDING,
        'error_message': None,
        'feedback_value': None,
    }
    st.session_state.pending_message_id = new_prompt_id


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

    return [{'text': doc['page_content'],
             'source': doc['metadata']['source'],
             'page': doc['metadata']['page']} for doc
            in
            output_list]


def rename_dataframe_columns(df):
    def clean_column_name(name):
        return name.replace('_PREDICTION', '').replace('_OUTPUT', '')

    # Apply the function to all column names
    df.columns = [clean_column_name(col) for col in df.columns]
    return df


def escape_result_text(text):
    # Avoids unexpected LaTex formatting on LLM response ($...$)
    return text.replace("$", r"\$")


def get_message_by_role(role, meta_id):
    return next(
        (msg for msg in st.session_state.messages if msg["meta_id"] == meta_id and msg["role"] == role), None)


def strip_metadata_from_messages(messages):
    """Strips meta_id field from the messages, otherwise OpenAI will fail due to schema mismatch"""
    return [
        {key: message[key] for key in message if key in {"role", "content"}}
        for message in messages
    ]


def set_result_message_state(meta_id, content, status, citations=None, extra_model_output=None, error=None):
    st.session_state.messages.append({
        'role': ROLE_ASSISTANT,
        'content': content,
        'meta_id': meta_id
    })
    set_result_message_meta_state(meta_id, status, citations, extra_model_output, error)
    st.session_state.pending_message_id = None


def set_result_message_meta_state(meta_id, status, citations=None, extra_model_output=None, error=None):
    st.session_state.messages_meta[meta_id]['status'] = status

    if citations:
        st.session_state.messages_meta[meta_id]['citations'] = citations

    if error:
        st.session_state.messages_meta[meta_id]['error_message'] = error

    if extra_model_output:
        association_id_column_name = get_association_id_column_name()
        if extra_model_output.get('datarobot_latency'):
            st.session_state.messages_meta[meta_id]['datarobot_latency'] = extra_model_output['datarobot_latency']
        if extra_model_output.get('datarobot_token_count'):
            st.session_state.messages_meta[meta_id]['datarobot_token_count'] = extra_model_output[
                'datarobot_token_count']
        if extra_model_output.get('datarobot_confidence_score'):
            st.session_state.messages_meta[meta_id]['datarobot_confidence_score'] = extra_model_output[
                'datarobot_confidence_score']
        if extra_model_output.get(association_id_column_name):
            st.session_state.messages_meta[meta_id]['association_id'] = extra_model_output[
                association_id_column_name] if association_id_column_name else meta_id
