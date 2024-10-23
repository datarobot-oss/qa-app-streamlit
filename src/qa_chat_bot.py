import streamlit as st
import streamlit_sal as sal
from datarobot import Client
from datarobot.client import set_client
from streamlit_sal import sal_stylesheet

from components import render_prompt_message, render_response_message, render_empty_chat, render_app_header
from constants import *
from utils import add_new_prompt_message, initiate_session_state, get_deployment

# Basic application page configuration, modify values in `constants.py`
st.set_page_config(page_title=I18N_APP_NAME, page_icon=APP_FAVICON, layout=APP_LAYOUT,
                   initial_sidebar_state=SIDEBAR_DEFAULT_STATE)


def start_streamlit():
    initiate_session_state()

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
                add_new_prompt_message(prompt)

        if len(st.session_state.messages) > 0:
            # Render all chat messages from this session on every app rerun
            for message in st.session_state.messages:
                # Render the prompt entered by the user in a fragment function
                render_prompt_message(message)
                # Render the LLM response in a fragment function
                render_response_message(message)
        else:
            # Render the empty chat splash in a fragment.
            # The SAL container remains here to keep the upper sal_stylesheet context
            with sal.container('empty-chat'):
                render_empty_chat()


if __name__ == "__main__":
    start_streamlit()
