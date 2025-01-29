import streamlit as st
import streamlit_sal as sal

import constants
from dr_requests import (
    submit_metric,
    send_predict_request,
    send_chat_api_request,
    send_chat_api_streaming_request,
    get_application_info
)
from utils import get_deployment, get_app_name, get_association_id_column_name, get_message_by_role


def render_app_header():
    app_info = get_application_info()
    app_name = get_app_name()
    app_description = constants.I18N_APP_DESCRIPTION
    external_access_enabled = app_info.get('externalAccessEnabled', False)
    app_url = app_info.get('applicationUrl', None)

    st.logo(constants.APP_LOGO)

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
                    if col1.button(constants.I18N_SHARE_BUTTON, key='share-button'):
                        show_share_dialog(app_url)


@st.dialog(constants.I18N_SHARE_DIALOG_TITLE, width="small")
def show_share_dialog(url):
    st.code(url, language="markdown")
    with sal.button('dialog-button'):
        if st.button(constants.I18N_DIALOG_CLOSE_BUTTON):
            st.rerun()


@st.dialog(constants.I18N_CITATION_DIALOG_TITLE, width="large")
def show_citations_dialog(prompt, answer, citations):
    with sal.container('citation-dialog-content'):
        col_prompt_key, col_prompt_value = st.columns([0.2, 0.8])
        with col_prompt_key:
            with sal.write('citation-key-text'):
                st.write(constants.I18N_CITATION_KEY_PROMPT)
        with col_prompt_value:
            st.write(prompt)

        col_answer_key, col_answer_value = st.columns([0.2, 0.8])
        with col_answer_key:
            with sal.write('citation-key-text'):
                st.write(constants.I18N_CITATION_KEY_ANSWER)
        with col_answer_value:
            st.write(answer)

        with sal.container('citation-sources'):
            col_citation_key, col_citation_value = st.columns([0.2, 0.8])
            with col_citation_key:
                with sal.write('citation-key-text'):
                    st.write(constants.I18N_CITATION_KEY_CITATION)
            with col_citation_value:
                for citation in citations:
                    with sal.container('citation-block'):
                        citation_block = st.container()
                        with sal.caption('citation-source', container=citation_block):
                            source_text = constants.I18N_CITATION_SOURCE_PAGE.format(
                                citation.get("source"),
                                citation.get("page")
                            ) if citation.get("page") is not None  else citation.get("source")
                            citation_block.caption(source_text)
                        with sal.text('citation-text', container=citation_block):
                            citation_block.text(citation.get("text"))

    with sal.button('dialog-button'):
        if st.button(constants.I18N_DIALOG_CLOSE_BUTTON):
            st.rerun()


# If your LLM response contains more metadata, you can add them here to `info_items`
def get_info_section_data(message_meta):
    info_items = []
    if message_meta.get("datarobot_latency"):
        formatted_value = constants.I18N_FORMAT_LATENCY.format(f'{message_meta["datarobot_latency"]:.2f}')
        info_items.append({constants.I18N_RESPONSE_LATENCY: formatted_value})

    if message_meta.get("datarobot_token_count"):
        info_items.append({constants.I18N_RESPONSE_TOKENS: message_meta["datarobot_token_count"]})

    if message_meta.get("datarobot_confidence_score"):
        formatted_value = constants.I18N_FORMAT_CONFIDENCE.format(
            f'{(100 * message_meta["datarobot_confidence_score"]):.2f}')
        info_items.append({constants.I18N_RESPONSE_CONFIDENCE: formatted_value})

    if message_meta.get("cost"):
        formatted_value = constants.I18N_FORMAT_CURRENCY.format(message_meta.get("cost"))
        info_items.append({constants.I18N_RESPONSE_COST: formatted_value})

    return info_items


def response_info_footer(meta_id):
    prompt_message = get_message_by_role(constants.ROLE_USER, meta_id)
    result_message = get_message_by_role(constants.ROLE_ASSISTANT, meta_id)
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
                        col1.button(constants.I18N_CITATION_BUTTON, key=f"citation-{meta_id}",
                                    on_click=show_citations_dialog,
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


@st.fragment
def render_message(message):
    role = message['role']
    content = message['content']
    msg_id = message['meta_id']

    msg_acc_name = constants.I18N_ACCESSIBILITY_LABEL_YOU if role == constants.ROLE_USER else constants.I18N_ACCESSIBILITY_LABEL_LLM
    msg_name = constants.USER_DISPLAY_NAME if role == constants.ROLE_USER else constants.LLM_DISPLAY_NAME
    msg_avatar = constants.USER_AVATAR if role == constants.ROLE_USER else constants.LLM_AVATAR
    meta_data = st.session_state.messages_meta[msg_id]

    # Render the message within a fragment, that way st.rerun() will only affect this container and not the whole app
    with sal.chat_message():
        with st.chat_message(name=msg_acc_name, avatar=msg_avatar):
            st.markdown(f"__{msg_name}:__")

            if role == constants.ROLE_USER:
                st.markdown(content)
            else:
                if 'status' in meta_data and meta_data['status'] == constants.STATUS_ERROR:
                    st.error(meta_data['error_message'], icon="🚨")
                else:
                    # escaped_text = escape_result_text(message['content'])
                    st.write(message['content'])
                    # st.write(escaped_text)
                    response_info_footer(msg_id)


@st.fragment
def render_pending_message(message):
    # Render the message within a fragment, that way st.rerun() will only affect this container and not the whole app
    with sal.chat_message():
        with st.chat_message(name=constants.I18N_ACCESSIBILITY_LABEL_LLM, avatar=constants.LLM_AVATAR):
            st.markdown(f"__{constants.LLM_DISPLAY_NAME}:__")
            if st.session_state.is_chat_api_enabled and constants.ENABLE_CHAT_API_STREAMING:
                # Immediately render any incoming streaming response
                st.write_stream(send_chat_api_streaming_request(message))
                # The final streaming chunk has been received now. Trigger rerun to let the render_message handle the
                # message rendering.
                st.rerun()
            else:
                with st.spinner(constants.I18N_LOADING_MESSAGE):
                    # Display a loading spinner message while we wait for a chat response
                    if st.session_state.is_chat_api_enabled:
                        send_chat_api_request(message)
                    else:
                        send_predict_request(message)
                    # Response has now been received, trigger manual rerun to render the message using render_message
                    st.rerun()


@st.fragment
def render_empty_chat():
    empty_chat = st.container()
    deployment = get_deployment()

    if st.session_state.deployment_id and deployment:
        empty_chat.image(constants.APP_EMPTY_CHAT_IMAGE, width=constants.APP_EMPTY_CHAT_IMAGE_WIDTH)
        with sal.text('empty-chat-header', container=empty_chat):
            empty_chat.text(constants.I18N_SPLASH_TITLE)
        if constants.I18N_SPLASH_TEXT:
            with sal.text('empty-chat-text', container=empty_chat):
                empty_chat.text(constants.I18N_SPLASH_TEXT)
    else:
        error_text = constants.I18N_NO_DEPLOYMENT_FOUND.format(
            st.session_state.deployment_id) if st.session_state.deployment_id and not deployment else constants.I18N_NO_DEPLOYMENT_ID
        with sal.text('empty-chat-text', container=empty_chat):
            empty_chat.error(error_text)
