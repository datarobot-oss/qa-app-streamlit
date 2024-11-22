import streamlit as st
import streamlit_sal as sal

from constants import (APP_LOGO, APP_EMPTY_CHAT_IMAGE, APP_EMPTY_CHAT_IMAGE_WIDTH, I18N_APP_DESCRIPTION,
                       I18N_FORMAT_LATENCY, I18N_RESPONSE_LATENCY, I18N_RESPONSE_TOKENS,
                       I18N_FORMAT_CONFIDENCE, I18N_RESPONSE_CONFIDENCE, I18N_FORMAT_CURRENCY, I18N_RESPONSE_COST,
                       I18N_DIALOG_CLOSE_BUTTON, I18N_APP_NAME, I18N_SHARE_DIALOG_TITLE,
                       I18N_CITATION_BUTTON, I18N_CITATION_DIALOG_TITLE, I18N_CITATION_KEY_ANSWER,
                       I18N_CITATION_KEY_PROMPT, I18N_CITATION_KEY_CITATION, I18N_CITATION_SOURCE_PAGE,
                       I18N_SPLASH_TITLE, I18N_SPLASH_TEXT, I18N_LOADING_MESSAGE, I18N_ACCESSIBILITY_LABEL_LLM,
                       STATUS_ERROR, STATUS_INITIATE, I18N_ACCESSIBILITY_LABEL_YOU, I18N_NO_DEPLOYMENT_FOUND,
                       I18N_NO_DEPLOYMENT_ID)
from dr_requests import submit_metric, make_prediction, get_application_info
from utils import get_deployment, escape_result_text, get_association_id_column_name


def render_app_header():
    st.logo(APP_LOGO)

    with sal.image('centered-image'):
        st.image(APP_LOGO)  # Set path of the company image to show centered


@st.experimental_dialog(I18N_SHARE_DIALOG_TITLE, width="small")
def show_share_dialog(url):
    st.code(url, language="markdown")
    with sal.button('dialog-button'):
        if st.button(I18N_DIALOG_CLOSE_BUTTON):
            st.rerun()


@st.experimental_dialog(I18N_CITATION_DIALOG_TITLE, width="large")
def show_citations_dialog(prompt, answer, citations):
    col_prompt_key, col_prompt_value = st.columns([0.2, 0.8])
    with col_prompt_key:
        with sal.write('citation-key-text'):
            st.write(I18N_CITATION_KEY_PROMPT)
    with col_prompt_value:
        st.write(prompt)

    col_answer_key, col_answer_value = st.columns([0.2, 0.8])
    with col_answer_key:
        with sal.write('citation-key-text'):
            st.write(I18N_CITATION_KEY_ANSWER)
    with col_answer_value:
        st.write(answer)

    col_citation_key, col_citation_value = st.columns([0.2, 0.8])
    with col_citation_key:
        with sal.write('citation-key-text'):
            st.write(I18N_CITATION_KEY_CITATION)
    with col_citation_value:
        for citation in citations:
            with sal.container('citation-block'):
                citation_block = st.container()
                with sal.caption('citation-source', container=citation_block):
                    source_text = I18N_CITATION_SOURCE_PAGE.format(
                        citation.get("source"),
                        citation.get("page")
                    ) if citation.get("page") else citation.get("source")
                    citation_block.caption(source_text)
                with sal.text('citation-text', container=citation_block):
                    citation_block.text(citation.get("text"))

    with sal.button('dialog-button'):
        if st.button(I18N_DIALOG_CLOSE_BUTTON):
            st.rerun()


# If your LLM response contains more meta data, you can add them here to `info_items`
def get_info_section_data(message):
    info_items = []
    if message.get("datarobot_latency"):
        formatted_value = I18N_FORMAT_LATENCY.format(f'{message["datarobot_latency"]:.2f}')
        info_items.append({I18N_RESPONSE_LATENCY: formatted_value})

    if message.get("datarobot_token_count"):
        info_items.append({I18N_RESPONSE_TOKENS: message["datarobot_token_count"]})

    if message.get("datarobot_confidence_score"):
        formatted_value = I18N_FORMAT_CONFIDENCE.format(
            f'{(100 * message["datarobot_confidence_score"]):.2f}')
        info_items.append({I18N_RESPONSE_CONFIDENCE: formatted_value})

    if message.get("cost"):
        formatted_value = I18N_FORMAT_CURRENCY.format(message.get("cost"))
        info_items.append({I18N_RESPONSE_COST: formatted_value})

    return info_items


def response_info_footer(message):
    msg_id = message['id']
    prompt = message['prompt']
    answer = message['result']
    feedback = message['feedback_value']
    citations = message.get('citations', None)
    custom_metric_id = st.session_state.custom_metric_id
    association_id = get_association_id_column_name()

    info_section_data = get_info_section_data(message)
    has_info_data = len(info_section_data) > 0
    if has_info_data or citations is not None:
        with sal.columns('chat-message-footer'):
            col0, col1 = st.columns([0.7, 0.3], vertical_alignment="center")

            if has_info_data:
                render_info_section(info_section_data, col0)

            with sal.column('justify-end', 'flex-row', container=col1):
                if custom_metric_id is not None and association_id is not None:
                    btn_up_icon_class = 'feedback-up-icon-active' if feedback == 1 else 'feedback-up-icon'
                    with sal.button('feedback-button', btn_up_icon_class, container=col1):
                        # Uses thin blank “ ” (U+2009) to be visible
                        col1.button(' ', on_click=submit_metric, args=(message, 1),
                                    key=f"feedback-up-{msg_id}")

                    btn_down_icon_class = 'feedback-down-icon-active' if feedback == 0 else 'feedback-down-icon'
                    with sal.button('feedback-button', btn_down_icon_class, container=col1):
                        # Uses thin blank “ ” (U+2009) to be visible
                        col1.button(' ', on_click=submit_metric, args=(message, 0),
                                    key=f"feedback-down-{msg_id}")
                if citations:
                    with sal.button('citation-button', container=col1):
                        col1.button(I18N_CITATION_BUTTON, key=f"citation-{msg_id}", on_click=show_citations_dialog,
                                    args=(prompt, answer, citations))


def render_info_section(data_list, container=None):
    html = '<div class="info-section">'
    for data in data_list:
        for key, value in data.items():
            # Can not use multiline here, Streamlit will treat it as code and wraps it with <pre>
            # Use single line concat instead
            html += '<div class="key-value-item">'
            html += f'<p><strong class="key">{key}:</strong> {value}</p>'
            html += '</div>'
    html += '</div>'

    # Streamlit adds `margin-bottom: -1rem` on markdown elements, remove it here
    with sal.markdown('no-margin', container=container):
        if container:
            container.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown(html, unsafe_allow_html=True)


@st.experimental_fragment
def render_prompt_message(message):
    # Render the message within a fragment, that way st.rerun() will only affect this container and not the whole app
    with sal.chat_message():
        with st.chat_message(name=I18N_ACCESSIBILITY_LABEL_YOU, avatar=message['user_avatar']):
            st.markdown(f"__{message['user_name']}:__")
            st.markdown(message["prompt"])


@st.experimental_fragment
def render_response_message(message):
    # Render the message within a fragment, that way st.rerun() will only affect this container and not the whole app
    with sal.chat_message():
        with st.chat_message(name=I18N_ACCESSIBILITY_LABEL_LLM, avatar=message['deployment_avatar']):
            st.markdown(f"__{message['deployment_name']}:__")

            if message['execution_status'] == STATUS_INITIATE:
                with st.spinner(I18N_LOADING_MESSAGE):
                    make_prediction(message)
                    st.rerun()
            elif message['execution_status'] == STATUS_ERROR:
                st.error(message['error_message'], icon="🚨")
            else:
                escaped_text = escape_result_text(message['result'])
                st.write(escaped_text)
                response_info_footer(message)


@st.experimental_fragment
def render_empty_chat():
    empty_chat = st.container()
    deployment = get_deployment()

    if st.session_state.deployment_id and deployment:
        empty_chat.image(APP_EMPTY_CHAT_IMAGE, width=APP_EMPTY_CHAT_IMAGE_WIDTH)
        with sal.text('empty-chat-header', container=empty_chat):
            empty_chat.text(I18N_SPLASH_TITLE)
        if I18N_SPLASH_TEXT:
            with sal.text('empty-chat-text', container=empty_chat):
                empty_chat.text(I18N_SPLASH_TEXT)
    else:
        error_text = I18N_NO_DEPLOYMENT_FOUND.format(
            st.session_state.deployment_id) if st.session_state.deployment_id and not deployment else I18N_NO_DEPLOYMENT_ID
        with sal.text('empty-chat-text', container=empty_chat):
            empty_chat.error(error_text)
