import os
import uuid
from typing import Any

import requests
import streamlit as st
from datarobot import Deployment

from constants import USER_ID, USER_AVATAR, USER_DISPLAY_NAME, LLM_DISPLAY_NAME, LLM_AVATAR, STATUS_INITIATE


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
    return Deployment.get(st.session_state.deployment_id)


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

    # Create a message storage on first render
    if "messages" not in st.session_state:
        st.session_state.messages = []


def add_new_prompt_message(prompt):
    deployment = get_deployment()
    new_prompt_id = str(uuid.uuid4())
    st.session_state.messages.append(
        {
            "id": new_prompt_id,
            "prompt": prompt,
            "result": None,
            "execution_status": STATUS_INITIATE,
            "user_id": USER_ID,
            "user_name": USER_DISPLAY_NAME,
            "user_avatar": USER_AVATAR,
            "deployment_name": LLM_DISPLAY_NAME if LLM_DISPLAY_NAME else deployment.model.get("type"),
            "deployment_avatar": LLM_AVATAR,
            "error_message": "",
            "feedback_value": None,
        }
    )


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


def rename_dataframe_columns(df):
    def clean_column_name(name):
        return name.replace('_PREDICTION', '').replace('_OUTPUT', '')

    # Apply the function to all column names
    df.columns = [clean_column_name(col) for col in df.columns]
    return df
