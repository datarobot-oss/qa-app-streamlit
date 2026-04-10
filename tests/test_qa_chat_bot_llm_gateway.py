"""Tests for LLM Gateway mode (no DEPLOYMENT_ID configured)."""

from unittest.mock import MagicMock, patch

import pytest
import responses
from streamlit.testing.v1 import AppTest


def _mock_completion(content: str) -> MagicMock:
    """Return a minimal litellm/OpenAI-compatible completion object."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    return response


def _mock_stream(*chunks: str):
    """Return a generator of streaming chunks for litellm.completion(stream=True)."""
    for content in chunks:
        chunk = MagicMock()
        chunk.choices = [MagicMock()]
        chunk.choices[0].delta.content = content
        yield chunk


@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env_llm_gateway",
    "mock_app_info_api",
    "mock_version_api",
    "app_id",
)
def test_llm_gateway_empty_chat():
    """Gateway mode: the app loads and shows the empty-chat splash without a DEPLOYMENT_ID."""
    at = AppTest.from_file("qa_chat_bot.py").run(timeout=10)
    assert at.session_state.use_llm_gateway is True
    assert at.session_state.is_chat_api_enabled is False
    # Chat input is available even without a deployment
    assert len(at.chat_input) == 1
    # Splash is shown
    assert at.text[0].value == "What do you want to know?"


@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env_llm_gateway",
    "mock_app_info_api",
    "mock_version_api",
)
@patch("litellm.completion")
def test_llm_gateway_non_streaming(mock_litellm):
    """Gateway mode: non-streaming response is rendered correctly."""
    mock_litellm.return_value = _mock_completion("The capital of France is Paris.")

    at = AppTest.from_file("qa_chat_bot.py").run(timeout=10)
    assert at.session_state.use_llm_gateway is True
    at.chat_input[0].set_value("What is the capital of France?").run(timeout=10)

    assert at.chat_message[0].markdown[1].value == "What is the capital of France?"
    assert at.chat_message[1].markdown[1].value == "The capital of France is Paris."

    # No feedback buttons or citations in gateway mode
    meta_id = at.session_state.messages[0].get("meta_id")
    assert f"citation-{meta_id}" not in at.session_state
    assert f"feedback-up-{meta_id}" not in at.session_state


@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env_llm_gateway",
    "mock_set_env_enable_chat_api_streaming",
    "mock_app_info_api",
    "mock_version_api",
)
@patch("litellm.completion")
def test_llm_gateway_streaming(mock_litellm):
    """Gateway mode: streaming response is assembled and rendered correctly."""
    mock_litellm.return_value = _mock_stream("Paris ", "is the capital ", "of France.")

    at = AppTest.from_file("qa_chat_bot.py").run(timeout=10)
    assert at.session_state.use_llm_gateway is True
    at.chat_input[0].set_value("What is the capital of France?").run(timeout=10)

    assert at.chat_message[0].markdown[1].value == "What is the capital of France?"
    assert at.chat_message[1].markdown[1].value == "Paris is the capital of France."


@responses.activate
@pytest.mark.usefixtures(
    "mock_set_env_llm_gateway",
    "mock_app_info_api",
    "mock_version_api",
)
@patch("litellm.completion")
def test_llm_gateway_error(mock_litellm):
    """Gateway mode: LLM errors are surfaced as an error message in the UI."""
    mock_litellm.side_effect = Exception("Gateway unavailable")

    at = AppTest.from_file("qa_chat_bot.py").run(timeout=10)
    at.chat_input[0].set_value("Hello").run(timeout=10)

    assert at.chat_message[1].error[0].value == "LLM Gateway error: Gateway unavailable"
