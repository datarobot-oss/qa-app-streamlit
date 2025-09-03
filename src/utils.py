import logging
import os
import uuid
from contextlib import contextmanager
from typing import cast, Dict, Any

import re
import json
import requests
import streamlit as st
from datarobot import Deployment, AppPlatformError
from openai import APIError

from constants import STATUS_PENDING, ROLE_ASSISTANT, ROLE_SYSTEM, I18N_APP_NAME_DEFAULT, STATUS_ERROR


class DataRobotPredictionError(Exception):
    """Raised if there are issues getting predictions from DataRobot"""


class ResponseProcessingError(Exception):
    """Raised if the app faces issues processing the response from OpenAI"""


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
def get_base_url():
    endpoint = st.session_state.endpoint
    deployment_id = st.session_state.deployment_id
    return f"{endpoint}/deployments/{deployment_id}"


@st.cache_data(show_spinner=False)
def get_association_id_column_name():
    deployment = get_deployment()

    # The library typing sets the return value as <string>, but it actually returns a <dict>. Cast it here
    deployment_association_id_settings = cast(Dict[str, Any], deployment.get_association_id_settings())
    association_id_names = deployment_association_id_settings.get("column_names")
    return association_id_names[0] if association_id_names else None


def get_app_name():
    return os.getenv("APP_NAME") or I18N_APP_NAME_DEFAULT


def initiate_session_state():
    # Env variables
    if 'token' not in st.session_state:
        st.session_state.token = os.getenv("TOKEN")
    if 'endpoint' not in st.session_state:
        st.session_state.endpoint = os.getenv("ENDPOINT")
    if 'custom_metric_id' not in st.session_state:
        st.session_state.custom_metric_id = os.getenv("CUSTOM_METRIC_ID")
    if 'deployment_id' not in st.session_state:
        st.session_state.deployment_id = os.getenv("DEPLOYMENT_ID")
    if 'app_id' not in st.session_state:
        st.session_state.app_id = os.getenv("APP_ID")
    if 'enable_chat_api' not in st.session_state:
        st.session_state.enable_chat_api = os.getenv("ENABLE_CHAT_API", 'False').lower() == 'true'
    if 'enable_chat_api_streaming' not in st.session_state:
        st.session_state.enable_chat_api_streaming = os.getenv("ENABLE_CHAT_API_STREAMING", 'False').lower() == 'true'

    # Create messages storage on first render
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if os.getenv("SYSTEM_PROMPT") and len(st.session_state.messages) == 0:
        st.session_state.messages.append({"role": ROLE_SYSTEM, "content": os.getenv("SYSTEM_PROMPT")})

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


def process_citations(citations: dict[str: Any]) -> list[dict[str: Any]]:
    """Processes citation data"""
    output_list = []

    for citation in citations:
        citation_dict = {
            "page_content": citation.get('content', ''),
            "metadata": {
                "source": citation.get('metadata', {}).get('source'),
                "page": citation.get('metadata', {}).get('page'),
            },
            "type": "Document"
        }

        output_list.append(citation_dict)

    return [{'text': doc['page_content'],
             'source': doc['metadata']['source'],
             'page': doc['metadata']['page']} for doc
            in
            output_list]

# Process function for the result from datarobot-predict
def process_predict_citations(input_dict: dict[str: Any]) -> list[dict[str: Any]]:
    """Processes citation data"""
    output_list = []
    num_citations = len([k for k in input_dict.keys() if k.startswith("CITATION_CONTENT")])

    if num_citations == 0 and '_LLM_CONTEXT' in input_dict:
        return process_llm_context_citations(input_dict["_LLM_CONTEXT"])

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


def process_llm_context_citations(llm_context: str):
    citations = json.loads(llm_context)
    output_list = []

    for citation in citations:
        link = citation.get("link", '')
        [source, page] = split_source_page(link)

        citation_dict = {
            "page_content": citation.get("content", ''),
            "metadata": {
                "source": source,
                "page": page
            },
            "type": "Document"
        }

        output_list.append(citation_dict)

    return [{'text': doc['page_content'],
             'source': doc['metadata']['source'],
             'page': doc['metadata']['page']} for doc
            in
            output_list]


def split_source_page(link):
    match = re.match(r"^(.*):(\d+)$", link)
    if match:
        return match.group(1), match.group(2)
    else:
        # Remove the ':' at the end when no page info is found
        return link[:-1], None


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
        (msg for msg in st.session_state.messages if msg.get("meta_id", None) == meta_id and msg["role"] == role), None)


def sanitize_messages_for_request(messages):
    """Strips meta_id and any invalid fields from the messages, otherwise OpenAI will fail due to schema mismatch"""
    sanitized_messages = []
    for i, message in enumerate(messages):
        if message['content'] is None:
            if i > 0 and messages[i - 1]['meta_id'] == message['meta_id']:
                sanitized_messages.pop()
            continue

        sanitized_messages.append({key: message[key] for key in message if key in {"role", "content"}})

    return sanitized_messages


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


@contextmanager
def handle_chat_api_error(meta_id):
    try:
        yield
    except APIError as e:
        request_error = '`{url}`  \n{code} {reason}  \n{msg}'.format(
            code=e.status_code, reason="Chat API returned an error", msg=e.body,
            url=get_base_url())
        set_result_message_state(meta_id, None, status=STATUS_ERROR, error=request_error)
    except ResponseProcessingError as e:
        request_error = '{reason}  \n{msg}'.format(reason="Error processing response from Chat API", msg=e)
        set_result_message_state(meta_id, None, status=STATUS_ERROR, error=request_error)
    except Exception as e:
        set_result_message_state(meta_id, None, status=STATUS_ERROR,
                                 error=f"An unexpected error occurred: {e}")
