import streamlit as st
import streamlit_sal as sal

from constants import (APP_LOGO, APP_EMPTY_CHAT_IMAGE, APP_EMPTY_CHAT_IMAGE_WIDTH, I18N_APP_DESCRIPTION,
                       I18N_FORMAT_LATENCY, I18N_RESPONSE_LATENCY, I18N_RESPONSE_TOKENS,
                       I18N_FORMAT_CONFIDENCE, I18N_RESPONSE_CONFIDENCE, I18N_FORMAT_CURRENCY, I18N_RESPONSE_COST,
                       I18N_DIALOG_CLOSE_BUTTON, I18N_SHARE_BUTTON, I18N_APP_NAME, I18N_SHARE_DIALOG_TITLE,
                       I18N_CITATION_BUTTON, I18N_CITATION_DIALOG_TITLE, I18N_CITATION_KEY_ANSWER,
                       I18N_CITATION_KEY_PROMPT, I18N_CITATION_KEY_CITATION, I18N_CITATION_SOURCE_PAGE,
                       I18N_SPLASH_TITLE, I18N_SPLASH_TEXT, I18N_LOADING_MESSAGE, I18N_ACCESSIBILITY_LABEL_LLM,
                       ROLE_USER, I18N_ACCESSIBILITY_LABEL_YOU, I18N_NO_DEPLOYMENT_FOUND,
                       I18N_NO_DEPLOYMENT_ID, LLM_AVATAR, LLM_DISPLAY_NAME, USER_AVATAR, USER_DISPLAY_NAME,
                       ROLE_ASSISTANT, STATUS_ERROR)
from dr_requests import submit_metric, send_predict_request, send_stream_request, get_application_info
from utils import get_deployment, escape_result_text, get_association_id_column_name, get_message_by_role


def render_app_header():
    app_info = get_application_info()
    app_name = I18N_APP_NAME
    app_description = I18N_APP_DESCRIPTION
    external_access_enabled = app_info.get('externalAccessEnabled', False)
    app_url = app_info.get('applicationUrl', None)

    st.logo(APP_LOGO)

    # Remove flex grow so header does not take half the app height
    with sal.columns('no-flex-grow'):
        col0, col1 = st.columns([0.8, 0.2], vertical_alignment="center")
        with col0:
            with sal.subheader("app-header", container=col0):
                col0.subheader(app_name, anchor=False)
            if app_description:
                col0.caption(app_description)

        # Style this column to move the button to the right side
        with sal.column('justify-end', 'flex-row', container=col1):
            if external_access_enabled and app_url:
                with sal.button('share-button', container=col1):
                    if col1.button(I18N_SHARE_BUTTON, key='share-button'):
                        show_share_dialog(app_url)


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
def get_info_section_data(message_meta):
    info_items = []
    if message_meta.get("datarobot_latency"):
        formatted_value = I18N_FORMAT_LATENCY.format(f'{message_meta["datarobot_latency"]:.2f}')
        info_items.append({I18N_RESPONSE_LATENCY: formatted_value})

    if message_meta.get("datarobot_token_count"):
        info_items.append({I18N_RESPONSE_TOKENS: message_meta["datarobot_token_count"]})

    if message_meta.get("datarobot_confidence_score"):
        formatted_value = I18N_FORMAT_CONFIDENCE.format(
            f'{(100 * message_meta["datarobot_confidence_score"]):.2f}')
        info_items.append({I18N_RESPONSE_CONFIDENCE: formatted_value})

    if message_meta.get("cost"):
        formatted_value = I18N_FORMAT_CURRENCY.format(message_meta.get("cost"))
        info_items.append({I18N_RESPONSE_COST: formatted_value})

    return info_items


def response_info_footer(meta_id):
    prompt_message = get_message_by_role(ROLE_USER, meta_id)
    result_message = get_message_by_role(ROLE_ASSISTANT, meta_id)
    message_meta = st.session_state.messages_meta.get(meta_id, None)

    prompt = prompt_message['content']
    answer = result_message['content']
    feedback = message_meta['feedback_value']
    citations = message_meta.get('citations', None)
    custom_metric_id = st.session_state.custom_metric_id
    association_id = get_association_id_column_name()

    info_section_data = get_info_section_data(message_meta)
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
                        col1.button(' ', on_click=submit_metric, args=(meta_id, message_meta, 1),
                                    key=f"feedback-up-{meta_id}")

                    btn_down_icon_class = 'feedback-down-icon-active' if feedback == 0 else 'feedback-down-icon'
                    with sal.button('feedback-button', btn_down_icon_class, container=col1):
                        # Uses thin blank “ ” (U+2009) to be visible
                        col1.button(' ', on_click=submit_metric, args=(meta_id, message_meta, 0),
                                    key=f"feedback-down-{meta_id}")
                if citations:
                    with sal.button('citation-button', container=col1):
                        col1.button(I18N_CITATION_BUTTON, key=f"citation-{meta_id}", on_click=show_citations_dialog,
                                    args=(prompt, answer, citations))


def render_info_section(data_list, container=None):
    html = '<div class="info-section">'
    for data in data_list:
        for key, value in data.items():
            # Can not use multiline here, Streamlit will treat it as code and wraps it with <pre>
            # Use single line concat instead
            html += '<div class="key-value-item">'
            html += f'<strong class="key">{key}:</strong> {value}'
            html += '</div>'
    html += '</div>'

    # Streamlit adds `margin-bottom: -1rem` on markdown elements, remove it here
    with sal.markdown('no-margin', container=container):
        if container:
            container.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown(html, unsafe_allow_html=True)


@st.experimental_fragment
def render_message(message):
    role = message['role']
    content = message['content']
    msg_id = message['meta_id']

    msg_acc_name = I18N_ACCESSIBILITY_LABEL_YOU if role == ROLE_USER else I18N_ACCESSIBILITY_LABEL_LLM
    msg_name = USER_DISPLAY_NAME if role == ROLE_USER else LLM_DISPLAY_NAME
    msg_avatar = USER_AVATAR if role == ROLE_USER else LLM_AVATAR
    meta_data = st.session_state.messages_meta[msg_id]

    # Render the message within a fragment, that way st.rerun() will only affect this container and not the whole app
    with sal.chat_message():
        with st.chat_message(name=msg_acc_name, avatar=msg_avatar):
            st.markdown(f"__{msg_name}:__")

            if role == ROLE_USER:
                st.markdown(content)
            else:
                if 'status' in meta_data and meta_data['status'] == STATUS_ERROR:
                    st.error(meta_data['error_message'], icon="🚨")
                else:
                    escaped_text = escape_result_text(message['content'])
                    st.write(escaped_text)
                    response_info_footer(msg_id)


@st.experimental_fragment
def render_pending_message(message):
    # Render the message within a fragment, that way st.rerun() will only affect this container and not the whole app
    with sal.chat_message():
        with st.chat_message(name=I18N_ACCESSIBILITY_LABEL_LLM, avatar=LLM_AVATAR):
            st.markdown(f"__{LLM_DISPLAY_NAME}:__")
            if st.session_state.is_chat_api_enabled:
                st.write_stream(send_stream_request(message))
                # Trigger manual rerun so the footer gets populated with extra model output
                st.rerun()
            else:
                with st.spinner(I18N_LOADING_MESSAGE):
                    send_predict_request(message)
                    # Trigger manual rerun to render the response including its footer
                    st.rerun()


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
