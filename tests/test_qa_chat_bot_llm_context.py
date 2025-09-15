import os
from collections import namedtuple
from unittest.mock import patch

import pandas as pd
import pytest
import responses
from streamlit.testing.v1 import AppTest


@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env",
    "mock_app_info_api",
    "mock_set_env_disable_chat_api",
    "mock_deployment_api",
    "mock_version_api",
)
def test_chat_send_predict_request_process_llm_context():
    # Path to the CSV file relative to the test file
    current_dir = os.path.dirname(__file__)
    csv_file_path = os.path.join(current_dir, 'mocks/prediction_response_context_citations.csv')
    dataframe_output = pd.read_csv(csv_file_path)
    PredictionResult = namedtuple('PredictionResult', field_names=['dataframe', 'response_headers'])

    with patch('datarobot_predict.deployment.predict',
               return_value=PredictionResult(dataframe=dataframe_output, response_headers={})):
        app = AppTest.from_file("qa_chat_bot.py")
        at = app.run()
        assert at.session_state.is_chat_api_enabled == False
        at.chat_input[0].set_value('Tell me a joke').run()

        # Check the user prompt message
        assert at.chat_message[0].markdown[0].value == '__You:__'
        assert at.chat_message[0].markdown[1].value == 'Tell me a joke'

        # Check the LLM response message
        assert at.chat_message[1].markdown[0].value == '__LLM Deployment:__'
        assert at.chat_message[1].markdown[1].value == 'Why did the developer go broke? Because he used up all his cache!'

        meta_element_value = at.chat_message[1].markdown[4].value
        # The markdown value contains html elements, so we need to check by substrings
        expected_substrings = ['Latency:', '1.53s', 'Tokens:', '15']

        # Loop over each expected substring and assert in the meta element value
        for substring in expected_substrings:
            assert substring in meta_element_value, f"Expected '{substring}' to be in '{meta_element_value}'"

        msg_id = at.session_state.messages[0].get('meta_id')
        citation_button = at.button(key=f"citation-{msg_id}")
        assert citation_button.label == 'Citation'
        citation_button.click().run()

        # Check citation source
        assert at.caption[
                   1].value == 'datarobot_english_documentation/datarobot_docs|en|platform|account-mgmt|getting-help.txt - Page: 3'
        assert at.caption[
                   2].value == 'datarobot_english_documentation/datarobot_docs|en|modeling|reference|eureqa-ref|guidance.txt - Page: 1'

