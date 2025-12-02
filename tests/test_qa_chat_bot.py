import json
import os
from collections import namedtuple
from unittest.mock import patch

import pandas as pd
import pytest
import responses
from streamlit.testing.v1 import AppTest

from .conftest import find_request_by_url, create_stream_chat_completion, create_chat_completion


# NOTE: The tests currently leak values between scenarios via cached functions.
# There is an open issue for this problem here: https://github.com/streamlit/streamlit/issues/9139
@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env",
    "mock_set_env_app_name",
    "mock_app_info_api",
    "mock_version_api",
    "mock_deployment_api",
    "app_id"
)
@patch('constants.I18N_APP_DESCRIPTION', 'A small example description')
@patch('constants.I18N_SPLASH_TITLE', 'What would you like to know?')
@patch('constants.I18N_SPLASH_TEXT', 'Ask me anything!')
@patch('constants.I18N_INPUT_PLACEHOLDER', 'Send your question')
def test_empty_chat_app():
    # Path to the CSV file relative to the test file
    current_dir = os.path.dirname(__file__)
    csv_file_path = os.path.join(current_dir, 'mocks/prediction_response.csv')
    dataframe_output = pd.read_csv(csv_file_path)
    PredictionResult = namedtuple('PredictionResult', field_names=['dataframe', 'response_headers'])

    with patch('datarobot_predict.deployment.predict',
               return_value=PredictionResult(dataframe=dataframe_output, response_headers={})):
        """The app loads and renders empty chat splash"""
        at = AppTest.from_file("qa_chat_bot.py").run()
        assert at.subheader[0].value == 'Application Test'
        assert at.caption[0].value == 'A small example description'
        assert at.button(key="share-button").label == 'Share'
        assert at.text[0].value == 'What would you like to know?'
        assert at.text[1].value == 'Ask me anything!'
        assert at.chat_input[0].placeholder == 'Send your question'
        assert at.session_state.is_chat_api_enabled == True


@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env",
    "mock_app_info_api",
    "mock_version_api",
    "mock_deployment_api",
    "app_id"
)
def test_chat_api_supported_app():
    """The app loads and uses deployment capabilities to check for Chat API support"""
    at = AppTest.from_file("qa_chat_bot.py").run()
    assert at.session_state.is_chat_api_enabled == True


@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env",
    "mock_app_info_api",
    "mock_deployment_api",
    "mock_version_api",
    "mock_bad_request_error",
    "deployment_id",
    "datarobot_endpoint"
)
@patch("openai.resources.chat.Completions.create")
def test_chat_send_chat_api_error(openai_create, mock_bad_request_error, deployment_id, datarobot_endpoint):
    """The app receives chat response after sending a prompt"""

    openai_create.side_effect = mock_bad_request_error

    app = AppTest.from_file("qa_chat_bot.py")
    at = app.run()
    assert at.session_state.is_chat_api_enabled == True
    at.chat_input[0].set_value('Tell me an interesting animal fact').run()

    # Check the user prompt message
    assert at.chat_message[0].markdown[0].value == '__You:__'
    assert at.chat_message[0].markdown[1].value == 'Tell me an interesting animal fact'

    # Check the LLM response message
    assert at.chat_message[1].markdown[0].value == '__LLM Deployment:__'
    request_error = '`{url}`  \n{code} {reason}  \n{msg}'.format(
        code=400, reason="Chat API returned an error",
        msg="{'message': 'ERROR: The LLM has received an invalid request.'}",
        url=f"{datarobot_endpoint}/deployments/{deployment_id}")
    assert at.chat_message[1].error[0].value == request_error



@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env",
    "mock_app_info_api",
    "mock_deployment_api",
    "mock_version_api",
)
@patch("openai.resources.chat.Completions.create")
def test_chat_send_chat_api_without_stream_request(openai_create):
    """The app receives chat response after sending a prompt"""

    mock_file = 'mock_chat_api_no_stream.json'
    openai_create.return_value = create_chat_completion(mock_file)

    app = AppTest.from_file("qa_chat_bot.py")
    at = app.run()
    assert at.session_state.is_chat_api_enabled == True
    at.chat_input[0].set_value('Tell me an interesting animal fact').run()

    # Check the user prompt message
    assert at.chat_message[0].markdown[0].value == '__You:__'
    assert at.chat_message[0].markdown[1].value == 'Tell me an interesting animal fact'

    # Check the LLM response message
    assert at.chat_message[1].markdown[0].value == '__LLM Deployment:__'
    assert at.chat_message[1].markdown[
               1].value == 'Giraffes only need to drink water once every few days because they get most of their water from the plants they eat!'

    meta_element_value = at.chat_message[1].markdown[4].value
    # The markdown value contains html elements, so we need to check by substrings
    expected_substrings = ['Latency:', '0.62s', 'Tokens:', '26', 'Confidence:', '50.00%']

    # Loop over each expected substring and assert in the meta element value
    for substring in expected_substrings:
        assert substring in meta_element_value, f"Expected '{substring}' to be in '{meta_element_value}'"

    msg_id = at.session_state.messages[0].get('meta_id')
    citation_button = at.button(key=f"citation-{msg_id}")
    assert f"citation-{msg_id}" in at.session_state
    assert citation_button.label == 'Citation'
    citation_button.click().run()

    # Check citation source
    assert at.caption[
               1].value == 'datarobot_english_documentation/datarobot_docs|en|modeling|special-workflows|multilabel.txt - Page: 0'
    assert at.caption[2].value == 'datarobot_english_documentation/datarobot_docs|en|more-info|eli5.txt - Page: 0'

    # Check citation text
    expected_citation_text_1 = 'Imagine you want to receive an answer'
    assert expected_citation_text_1 in at.text[1].value, \
        f"Expected '{expected_citation_text_1}' to be in '{at.text[1].value}'"

    expected_citation_text_2 = 'What are summarized categorical features?'
    assert expected_citation_text_2 in at.text[2].value, \
        f"Expected '{expected_citation_text_2}' to be in '{at.text[2].value}'"


@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env",
    "mock_app_info_api",
    "mock_deployment_api",
    "mock_version_api",
)
@patch("openai.resources.chat.Completions.create")
def test_chat_api_no_citations(openai_create):
    """The app should not show citations button when not available"""

    mock_file = 'mock_chat_api_no_stream_no_citations.json'
    openai_create.return_value = create_chat_completion(mock_file)

    app = AppTest.from_file("qa_chat_bot.py")
    at = app.run()
    assert at.session_state.is_chat_api_enabled == True
    at.chat_input[0].set_value('Tell me an interesting animal fact').run()

    # Assert that the citations button does not exist when Citations are not available
    msg_id = at.session_state.messages[0].get('meta_id')
    assert f"citation-{msg_id}" not in at.session_state


@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env",
    "mock_app_info_api",
    "mock_deployment_api",
    "mock_version_api",
)
@patch("openai.resources.chat.Completions.create")
def test_chat_api_legacy_citations(openai_create):
    mock_file = 'mock_chat_api_no_stream_legacy_citations.json'
    openai_create.return_value = create_chat_completion(mock_file)

    app = AppTest.from_file("qa_chat_bot.py")
    at = app.run()
    assert at.session_state.is_chat_api_enabled == True
    at.chat_input[0].set_value('Tell me an interesting animal fact').run()

    msg_id = at.session_state.messages[0].get('meta_id')
    citation_button = at.button(key=f"citation-{msg_id}")
    assert f"citation-{msg_id}" in at.session_state
    assert citation_button.label == 'Citation'
    citation_button.click().run()

    # Check citation source
    assert at.caption[
               1].value == 'datarobot_english_documentation/datarobot_docs|en|modeling|special-workflows|multilabel.txt - Page: 0'
    assert at.caption[2].value == 'datarobot_english_documentation/datarobot_docs|en|more-info|eli5.txt - Page: 0'

    # Check citation text
    expected_citation_text_1 = 'Imagine you want to receive an answer'
    assert expected_citation_text_1 in at.text[1].value, \
        f"Expected '{expected_citation_text_1}' to be in '{at.text[1].value}'"

    expected_citation_text_2 = 'What are summarized categorical features?'
    assert expected_citation_text_2 in at.text[2].value, \
        f"Expected '{expected_citation_text_2}' to be in '{at.text[2].value}'"


@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env",
    "mock_set_env_disable_chat_api",
    "mock_app_info_api",
    "mock_deployment_api",
    "mock_version_api",
)
def test_chat_send_predict_request():
    """The app receives chat response after sending a prompt"""
    app = AppTest.from_file("qa_chat_bot.py")
    at = app.run()
    assert at.session_state.is_chat_api_enabled == False
    at.chat_input[0].set_value('Hello').run()

    # Check the user prompt message
    assert at.chat_message[0].markdown[0].value == '__You:__'
    assert at.chat_message[0].markdown[1].value == 'Hello'

    # Check the LLM response message
    assert at.chat_message[1].markdown[0].value == '__LLM Deployment:__'
    assert at.chat_message[1].markdown[1].value == 'Hello! How can I assist you today?'

    meta_element_value = at.chat_message[1].markdown[4].value
    # The markdown value contains html elements, so we need to check by substrings
    expected_substrings = ['Latency:', '0.52s', 'Tokens:', '9', 'Confidence:', '28.57%']

    # Loop over each expected substring and assert in the meta element value
    for substring in expected_substrings:
        assert substring in meta_element_value, f"Expected '{substring}' to be in '{meta_element_value}'"

    msg_id = at.session_state.messages[0].get('meta_id')
    citation_button = at.button(key=f"citation-{msg_id}")
    assert citation_button.label == 'Citation'
    citation_button.click().run()

    # Check citation source
    assert at.caption[
               1].value == 'datarobot_english_documentation/datarobot_docs|en|get-started|gs-get-help|troubleshooting|signin-help.txt - Page: 0'
    assert at.caption[2].value == 'datarobot_english_documentation/datarobot_docs|en|gen-ai|playground.txt - Page: 0'

    # Check citation text
    expected_citation_text_1 = 'The input entered during chatting used to generate the LLM response.'
    assert expected_citation_text_1 in at.text[2].value, \
        f"Expected '{expected_citation_text_1}' to be in '{at.text[2].value}'"

    expected_citation_text_2 = 'Enter the Azure OpenAI API version to use for this operation'
    assert expected_citation_text_2 in at.text[3].value, \
        f"Expected '{expected_citation_text_2}' to be in '{at.text[3].value}'"


@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env",
    "mock_set_env_enable_chat_api_streaming",
    "mock_app_info_api",
    "mock_deployment_api",
    "mock_version_api",
)
@patch("openai.resources.chat.Completions.create")
def test_chat_send_chat_api_stream_request(openai_create):
    """The app receives chat response after sending a prompt"""
    chunk_files = ['mock_initial_chunk.json', 'mock_delta_chunk.json', 'mock_final_chunk.json']
    openai_create.return_value = create_stream_chat_completion(chunk_files)

    app = AppTest.from_file("qa_chat_bot.py")
    at = app.run()
    assert at.session_state.is_chat_api_enabled == True
    at.chat_input[0].set_value('Tell me a joke').run()

    # Check the user prompt message
    assert at.chat_message[0].markdown[0].value == '__You:__'
    assert at.chat_message[0].markdown[1].value == 'Tell me a joke'

    # Check the LLM response message
    assert at.chat_message[1].markdown[0].value == '__LLM Deployment:__'
    assert at.chat_message[1].markdown[1].value == 'Why don\'t scientists trust atoms? Because they make up everything.'

    meta_element_value = at.chat_message[1].markdown[4].value
    # The markdown value contains html elements, so we need to check by substrings
    expected_substrings = ['Latency:', '0.08s', 'Tokens:', '13', 'Confidence:', '63.64%']

    # Loop over each expected substring and assert in the meta element value
    for substring in expected_substrings:
        assert substring in meta_element_value, f"Expected '{substring}' to be in '{meta_element_value}'"

    msg_id = at.session_state.messages[0].get('meta_id')
    citation_button = at.button(key=f"citation-{msg_id}")
    assert citation_button.label == 'Citation'
    citation_button.click().run()

    # Check citation source
    assert at.caption[1].value == 'datarobot_english_documentation/datarobot_docs|en|more-info|eli5.txt - Page: 0'
    assert at.caption[
               2].value == 'datarobot_english_documentation/datarobot_docs|en|modeling|special-workflows|multilabel.txt - Page: 0'

    # Check citation text
    expected_citation_text_1 = 'Do aliens exist?'
    assert expected_citation_text_1 in at.text[0].value, \
        f"Expected '{expected_citation_text_1}' to be in '{at.text[0].value}'"

    expected_citation_text_2 = 'you were going to find the best deal'
    assert expected_citation_text_2 in at.text[1].value, \
        f"Expected '{expected_citation_text_2}' to be in '{at.text[1].value}'"


@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env",
    "mock_set_env_enable_chat_api_streaming",
    "mock_app_info_api",
    "mock_deployment_api",
    "mock_version_api",
)
@patch("openai.resources.chat.Completions.create")
def test_chat_send_chat_api_stream_request_no_citations(openai_create):
    """The app receives chat response after sending a prompt"""
    chunk_files = ['mock_initial_chunk.json', 'mock_delta_chunk.json', 'mock_final_chunk_no_citations.json']
    openai_create.return_value = create_stream_chat_completion(chunk_files)

    app = AppTest.from_file("qa_chat_bot.py")
    at = app.run()
    assert at.session_state.is_chat_api_enabled == True
    at.chat_input[0].set_value('Tell me a joke').run()

    # Check the user prompt message
    assert at.chat_message[0].markdown[0].value == '__You:__'
    assert at.chat_message[0].markdown[1].value == 'Tell me a joke'

    # Check the LLM response message
    assert at.chat_message[1].markdown[0].value == '__LLM Deployment:__'
    assert at.chat_message[1].markdown[1].value == 'Why don\'t scientists trust atoms? Because they make up everything.'

    # Assert that the citations button does not exist when Citations are not available
    msg_id = at.session_state.messages[0].get('meta_id')
    assert f"citation-{msg_id}" not in at.session_state


@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env",
    "mock_set_env_enable_chat_api_streaming",
    "mock_app_info_api",
    "mock_deployment_api",
    "mock_deployment_chat_api_stream",
    "mock_version_api",
    "model_id",
    "feedback_endpoint",
    "is_model_specific"
)
@pytest.mark.parametrize("is_model_specific", [True, False])
@patch("openai.resources.chat.Completions.create")
def test_chat_feedback_request(openai_create, feedback_endpoint, model_id, is_model_specific):
    """The user can submit feedback for a response"""
    chunk_files = ['mock_initial_chunk.json', 'mock_delta_chunk.json', 'mock_final_chunk.json']
    openai_create.return_value = create_stream_chat_completion(chunk_files)

    app = AppTest.from_file("qa_chat_bot.py")
    at = app.run()
    assert at.session_state.is_chat_api_enabled == True
    at.chat_input[0].set_value('Hello').run()

    # Check the LLM response message
    assert at.chat_message[1].markdown[0].value == '__LLM Deployment:__'
    assert at.chat_message[1].markdown[1].value == 'Why don\'t scientists trust atoms? Because they make up everything.'

    meta_id = at.session_state.messages[0].get('meta_id')
    assoc_id = at.session_state.messages_meta[meta_id]["association_id"]
    feedback_up_button = at.button(key=f"feedback-up-{assoc_id}")
    # '\u2009' matches the thin whitespace for a feedback button
    assert feedback_up_button.label == '\u2009'
    assert feedback_up_button.value is False
    feedback_up_button.click().run()
    feedback_request = find_request_by_url(responses.calls, feedback_endpoint)
    feedback_up_request_body = json.loads(feedback_request.request.body)
    if is_model_specific:
        assert model_id == feedback_up_request_body.get('modelId')
    else:
        assert 'modelId' not in feedback_up_request_body
    assert 1 == feedback_up_request_body['buckets'][0]['value']
    assert feedback_up_button.value is True
