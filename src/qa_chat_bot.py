import streamlit as st
import streamlit_sal as sal
from datarobot import Client
from datarobot.client import set_client
from streamlit_sal import sal_stylesheet

from components import render_empty_chat, render_app_header, render_message, render_pending_message
from constants import *
from dr_requests import get_has_chat_api_support
from utils import add_new_prompt, initiate_session_state, set_chat_api_session_state, get_deployment, \
    get_message_by_role

# Basic application page configuration, modify values in `constants.py`
st.set_page_config(page_title=I18N_APP_NAME, page_icon=APP_FAVICON, layout=APP_LAYOUT,
                   initial_sidebar_state=SIDEBAR_DEFAULT_STATE)


def start_streamlit():
    initiate_session_state()
    is_chat_api_enabled = get_has_chat_api_support(deployment_id=st.session_state.deployment_id,
                                       token=st.session_state.token,
                                       endpoint=st.session_state.endpoint) if FORCE_DISABLE_CHAT_API == False else False
    set_chat_api_session_state(is_chat_api_enabled)

    # Setup DR client
    set_client(Client(token=st.session_state.token, endpoint=st.session_state.endpoint))
    has_valid_deployment = st.session_state.deployment_id and get_deployment()

    # Wraps the application with a SAL stylesheet so elements within it can be customized
    with sal_stylesheet():
        render_app_header()

        # You can manually enable the sidebar in `constants.py` and add your own content below
        if SHOW_SIDEBAR:
            with st.sidebar:
                st.subheader('Sidebar Title')
                st.write('Add your sidebar content here')

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
            # Render the empty chat splash in a fragment.
            # The SAL container remains here to keep the upper sal_stylesheet context
            with sal.container('empty-chat'):
                render_empty_chat()


if __name__ == "__main__":
    start_streamlit()
