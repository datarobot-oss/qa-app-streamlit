import json
import os
import sys
from collections import namedtuple
from unittest.mock import patch

import pandas as pd
import pytest
import responses
from streamlit.testing.v1 import AppTest

from .conftest import find_request_by_url

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))


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
@patch('constants.FORCE_DISABLE_CHAT_API', False)
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
        # Forced Chat API to be disabled
        assert at.session_state.is_chat_api_enabled == True


@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env",
    "mock_app_info_api",
    "mock_version_api",
    "mock_deployment_api",
    "app_id"
)
@patch('constants.FORCE_DISABLE_CHAT_API', False)
def test_chat_api_supported_app():
    """The app loads and uses deployment capabilities to check for Chat API support"""
    at = AppTest.from_file("qa_chat_bot.py").run()
    assert at.session_state.is_chat_api_enabled == True


@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env",
    "mock_app_info_api",
    "mock_deployment_api",
    "mock_deployment_chat_api_stream",
    "mock_version_api",
)
@patch('constants.FORCE_DISABLE_CHAT_API', False)
def test_chat_send_chat_api_stream_request():
    """The app receives chat response after sending a prompt"""
    app = AppTest.from_file("qa_chat_bot.py")
    at = app.run()
    at.chat_input[0].set_value('Tell me a joke').run()

    # Check the user prompt message
    assert at.chat_message[0].markdown[0].value == '__You:__'
    assert at.chat_message[0].markdown[1].value == 'Tell me a joke'

    # Check the LLM response message
    assert at.chat_message[1].markdown[0].value == '__LLM Deployment:__'
    assert at.chat_message[1].markdown[1].value == 'Why did the bicycle fall over? Because it was two-tired!'

    meta_element_value = at.chat_message[1].markdown[4].value
    # The markdown value contains html elements, so we need to check by substrings
    expected_substrings = ['Latency:', '0.03s', 'Tokens:', '17', 'Confidence:', '46.15%']

    # Loop over each expected substring and assert in the meta element value
    for substring in expected_substrings:
        assert substring in meta_element_value, f"Expected '{substring}' to be in '{meta_element_value}'"

    msg_id = at.session_state.messages[0].get('meta_id')
    citation_button = at.button(key=f"citation-{msg_id}")
    assert citation_button.label == 'Citation'
    citation_button.click().run()

    # Check citation source
    assert at.caption[
               1].value == 'datarobot_english_documentation/datarobot_docs|en|modeling|special-workflows|multilabel.txt - Page: 0'
    assert at.caption[2].value == 'datarobot_english_documentation/datarobot_docs|en|more-info|eli5.txt - Page: 0'

    # Check citation text
    expected_citation_text_1 = 'A generalization of multiclass that provides greater flexibility.'
    assert expected_citation_text_1 in at.text[0].value, \
        f"Expected '{expected_citation_text_1}' to be in '{at.text[0].value}'"

    expected_citation_text_2 = 'Imagine you want to receive an answer'
    assert expected_citation_text_2 in at.text[1].value, \
        f"Expected '{expected_citation_text_2}' to be in '{at.text[1].value}'"


@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env",
    "mock_app_info_api",
    "mock_deployment_api",
    "mock_deployment_chat_api",
    "mock_version_api",
)
@patch('constants.FORCE_DISABLE_CHAT_API', False)
@patch('dr_requests.ENABLE_CHAT_API_STREAMING', False)
def test_chat_send_chat_api_without_stream_request():
    """The app receives chat response after sending a prompt"""
    app = AppTest.from_file("qa_chat_bot.py")
    at = app.run()
    at.chat_input[0].set_value('Tell me an interesting animal fact').run()

    # Check the user prompt message
    assert at.chat_message[0].markdown[0].value == '__You:__'
    assert at.chat_message[0].markdown[1].value == 'Tell me an interesting animal fact'

    # Check the LLM response message
    assert at.chat_message[1].markdown[0].value == '__LLM Deployment:__'
    assert at.chat_message[1].markdown[
               1].value == 'The heart of a blue whale, the largest animal on earth, is so big that a human could swim through its arteries!'

    meta_element_value = at.chat_message[1].markdown[4].value
    # The markdown value contains html elements, so we need to check by substrings
    expected_substrings = ['Latency:', '0.64s', 'Tokens:', '28', 'Confidence:', '41.67%']

    # Loop over each expected substring and assert in the meta element value
    for substring in expected_substrings:
        assert substring in meta_element_value, f"Expected '{substring}' to be in '{meta_element_value}'"

    msg_id = at.session_state.messages[0].get('meta_id')
    citation_button = at.button(key=f"citation-{msg_id}")
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

    expected_citation_text_2 = 'The **Illustration** tab shows how summarized categorical data is represented as a feature'
    assert expected_citation_text_2 in at.text[2].value, \
        f"Expected '{expected_citation_text_2}' to be in '{at.text[2].value}'"


@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env",
    "mock_app_info_api",
    "mock_deployment_api",
    "mock_version_api",
)
def test_chat_send_predict_request():
    """The app receives chat response after sending a prompt"""
    app = AppTest.from_file("qa_chat_bot.py")
    at = app.run()
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
    "mock_app_info_api",
    "mock_deployment_api",
    "mock_deployment_chat_api_stream",
    "mock_version_api",
    "model_id",
    "feedback_endpoint",
    "is_model_specific"
)
@pytest.mark.parametrize("is_model_specific", [True, False])
@patch('constants.FORCE_DISABLE_CHAT_API', False)
def test_chat_feedback_request(feedback_endpoint, model_id, is_model_specific):
    """The user can submit feedback for a response"""
    app = AppTest.from_file("qa_chat_bot.py")
    at = app.run()
    at.chat_input[0].set_value('Hello').run()

    # Check the LLM response message
    assert at.chat_message[1].markdown[0].value == '__LLM Deployment:__'
    assert at.chat_message[1].markdown[1].value == 'Why did the bicycle fall over? Because it was two-tired!'

    msg_id = at.session_state.messages[0].get('meta_id')
    feedback_up_button = at.button(key=f"feedback-up-{msg_id}")
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
