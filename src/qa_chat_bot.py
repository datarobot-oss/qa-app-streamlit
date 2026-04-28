import os

import streamlit as st
import streamlit_sal as sal
from datarobot import Client
from datarobot.client import set_client

from components import (
    render_app_header,
    render_empty_chat,
    render_message,
    render_pending_message,
    render_vdb_filter_sidebar,
)
from constants import *
from dr_requests import get_has_chat_api_support
from utils import (
    add_new_prompt,
    get_app_name,
    get_deployment,
    get_llm_models,
    get_message_by_role,
    initiate_session_state,
    set_chat_api_session_state,
)

# Basic application page configuration, modify values in `constants.py`
st.set_page_config(
    page_title=get_app_name(), page_icon=APP_FAVICON, layout=APP_LAYOUT, initial_sidebar_state=SIDEBAR_DEFAULT_STATE
)

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))


def _inject_sal_stylesheet():
    """Inject the pre-compiled SAL stylesheet directly, bypassing streamlit_sal's
    find_root_dir() which depends on CWD and a .streamlit_sal config file that may
    not be found when the platform runs streamlit from an unexpected working directory."""
    css_path = os.path.join(_SRC_DIR, "styles", "sal-stylesheet.css")
    try:
        with open(css_path) as f:
            css = f.read()
        if css:
            st.markdown(f"<style class='hidden'>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass  # Best effort — app still works without custom styling


def start_streamlit():
    # Setup DR client — reads DATAROBOT_API_TOKEN and DATAROBOT_ENDPOINT automatically
    dr = Client()
    set_client(dr)
    initiate_session_state(dr)

    if st.session_state.use_llm_gateway:
        # No deployment needed — route requests through the DataRobot LLM Gateway.
        set_chat_api_session_state(False)
        has_valid_deployment = True

        with st.sidebar:
            models = get_llm_models(st.session_state.token, st.session_state.endpoint)
            if models:
                # Seed the widget key once from the configured default so it sticks.
                # After that, Streamlit owns the selection state via the key.
                if "_llm_model_select" not in st.session_state:
                    configured = st.session_state.llm_gateway_model.removeprefix("datarobot/")
                    st.session_state["_llm_model_select"] = configured if configured in models else models[0]
                st.selectbox("LLM Model", options=models, key="_llm_model_select")
                st.session_state.llm_gateway_model = f"datarobot/{st.session_state['_llm_model_select']}"
            else:
                st.caption("No LLM Gateway models found.")
    else:
        is_chat_api_enabled = (
            get_has_chat_api_support(
                deployment_id=st.session_state.deployment_id,
                token=st.session_state.token,
                endpoint=st.session_state.endpoint,
            )
            if st.session_state.enable_chat_api
            else False
        )
        set_chat_api_session_state(is_chat_api_enabled)
        has_valid_deployment = bool(st.session_state.deployment_id and get_deployment())
        render_vdb_filter_sidebar()

    _inject_sal_stylesheet()
    render_app_header()

    # You can manually enable the sidebar in `constants.py` and add your own content below
    if SHOW_SIDEBAR:
        with st.sidebar:
            st.subheader("Sidebar Title")
            st.write("Add your sidebar content here")

    if has_valid_deployment:
        if prompt := st.chat_input(I18N_INPUT_PLACEHOLDER):
            add_new_prompt(prompt)

    # Ignore any system message in the conversation context
    filtered_messages = [msg for msg in st.session_state.messages if msg["role"] != ROLE_SYSTEM]
    if len(filtered_messages) > 0:
        # Render all chat messages from this session on every app rerun
        for message in filtered_messages:
            # Render the prompt entered by the user in a fragment function
            render_message(message)

        if st.session_state.pending_message_id:
            pending_message = get_message_by_role(ROLE_USER, st.session_state.pending_message_id)
            render_pending_message(pending_message)
    else:
        # Render the empty chat splash
        with sal.container("empty-chat"):
            render_empty_chat()


if __name__ == "__main__":
    start_streamlit()
