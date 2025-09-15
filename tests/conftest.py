import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
import responses
from bson import ObjectId
from openai import BadRequestError
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk, ChoiceDelta
from openai.types.chat.chat_completion_chunk import Choice as StreamChoice

# Add the `src` directory to the Python path
src_path = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(src_path))


# Fixtures
@pytest.fixture(scope='module')
def deployment_id():
    return 'deployment_id_' + str(ObjectId())


@pytest.fixture(scope='module')
def custom_metric_id():
    return 'custom_metric_id_' + str(ObjectId())


@pytest.fixture(scope='module')
def app_name():
    return 'Application Test'


@pytest.fixture(scope='module')
def datarobot_token():
    return 'datarobot_token_' + str(ObjectId())


@pytest.fixture(scope='module')
def datarobot_endpoint():
    return "https://test-app.datarobot.com/api/v2"


@pytest.fixture(scope='module')
def model_id():
    return 'model_id_' + str(ObjectId())


@pytest.fixture(scope='module')
def prediction_server_id():
    return 'prediction_server_id_' + str(ObjectId())


@pytest.fixture(scope='module')
def prediction_api_key():
    return 'prediction_api_key_' + str(ObjectId())


@pytest.fixture
def prediction_api_url():
    return "https://prediction-test.dynamic.orm.datarobot.com"


@pytest.fixture
def feedback_endpoint(datarobot_endpoint, deployment_id, custom_metric_id):
    return f"{datarobot_endpoint}/deployments/{deployment_id}/customMetrics/{custom_metric_id}/fromJSON/"


@pytest.fixture
def custom_metric_endpoint(datarobot_endpoint, deployment_id, custom_metric_id):
    return f"{datarobot_endpoint}/deployments/{deployment_id}/customMetrics/{custom_metric_id}/"


@pytest.fixture
def msg_id():
    return 'msg_id_' + str(ObjectId())


@pytest.fixture
def app_id():
    return 'app_id_' + str(ObjectId())


@pytest.fixture
def mock_set_env_app_name(monkeypatch, app_name):
    with patch.dict(os.environ):
        monkeypatch.setenv("APP_NAME", app_name)
        yield


@pytest.fixture
def mock_set_env_disable_chat_api(monkeypatch, app_name):
    with patch.dict(os.environ):
        monkeypatch.setenv("ENABLE_CHAT_API", "false")
        yield


@pytest.fixture
def mock_set_env_enable_chat_api_streaming(monkeypatch, app_name):
    with patch.dict(os.environ):
        monkeypatch.setenv("ENABLE_CHAT_API_STREAMING", "true")
        yield


@pytest.fixture
def mock_set_env(
    monkeypatch,
    datarobot_token,
    datarobot_endpoint,
    custom_metric_id,
    deployment_id,
    app_id,
):
    with patch.dict(os.environ, clear=True):
        monkeypatch.setenv("TOKEN", datarobot_token)
        monkeypatch.setenv("ENDPOINT", datarobot_endpoint)
        monkeypatch.setenv("CUSTOM_METRIC_ID", custom_metric_id)
        monkeypatch.setenv("DEPLOYMENT_ID", deployment_id)
        monkeypatch.setenv("APP_ID", app_id)
        monkeypatch.setenv("ENABLE_CHAT_API", True)
        yield


@pytest.fixture
def mock_app_info_api(datarobot_endpoint, app_id):
    responses.get(
        f"{datarobot_endpoint}/customApplications/{app_id}/",
        json={
            'id': app_id,
            'name': 'New Q&A App native 2024-07-16T12:40:41',
            'externalAccessEnabled': True,
            'applicationUrl': f'https://test-app.datarobot.com/custom_applications/{app_id}/',
        }
    )


@pytest.fixture
def mock_version_api(datarobot_endpoint):
    responses.get(
        f"{datarobot_endpoint}/version/",
        json={
            "major": 2,
            "minor": 34,
            "versionString": "2.34.0",
            "releasedVersion": "2.33.0",
        },
    )

@pytest.fixture
def is_model_specific():
    return True


@pytest.fixture
def mock_deployment_chat_api_stream(
        datarobot_endpoint,
        model_id,
        deployment_id,
):
    def mock_stream():
        current_dir = os.path.dirname(__file__)

        initial_file_path = os.path.join(current_dir, 'mocks/mock_initial_chunk.json')
        with open(initial_file_path, "r") as initial_file:
            file_content = json.load(initial_file)
            yield "data: {}\n\n".format(
                json.dumps(file_content)
            ).encode("utf-8")

        delta_file_path = os.path.join(current_dir, 'mocks/mock_delta_chunk.json')
        with open(delta_file_path, "r") as delta_file:
            file_content = json.load(delta_file)
            yield "data: {}\n\n".format(
                json.dumps(file_content)
            ).encode("utf-8")

        final_file_path = os.path.join(current_dir, 'mocks/mock_final_chunk.json')
        with open(final_file_path, "r") as final_file:
            file_content = json.load(final_file)
            yield "data: {}\n\n".format(
                json.dumps(file_content)
            ).encode("utf-8")

    responses.post(
        f"{datarobot_endpoint}/deployments/{deployment_id}/chat/completions",
        body=b"".join(mock_stream()),
        content_type="text/event-stream",
    )


@pytest.fixture
def mock_deployment_chat_api(
        datarobot_endpoint,
        model_id,
        deployment_id,
):
    current_dir = os.path.dirname(__file__)
    mock_no_stream_file_path = os.path.join(current_dir, 'mocks/mock_chat_api_no_stream.json')
    with open(mock_no_stream_file_path, "r") as no_stream_file:
        file_content = json.load(no_stream_file)

        responses.post(
            f"{datarobot_endpoint}/deployments/{deployment_id}/chat/completions",
            body=json.dumps(file_content).encode("utf-8")
        )


@pytest.fixture
def mock_deployment_chat_api_no_citations(
        datarobot_endpoint,
        model_id,
        deployment_id,
):
    current_dir = os.path.dirname(__file__)
    mock_no_stream_file_path = os.path.join(current_dir, 'mocks/mock_chat_api_no_stream_no_citations.json')
    with open(mock_no_stream_file_path, "r") as no_stream_file:
        file_content = json.load(no_stream_file)

        responses.post(
            f"{datarobot_endpoint}/deployments/{deployment_id}/chat/completions",
            body=json.dumps(file_content).encode("utf-8")
        )


@pytest.fixture
def mock_deployment_chat_api_legacy_citations(
        datarobot_endpoint,
        model_id,
        deployment_id,
):
    current_dir = os.path.dirname(__file__)
    mock_no_stream_file_path = os.path.join(current_dir, 'mocks/mock_chat_api_no_stream_legacy_citations.json')
    with open(mock_no_stream_file_path, "r") as no_stream_file:
        file_content = json.load(no_stream_file)

        responses.post(
            f"{datarobot_endpoint}/deployments/{deployment_id}/chat/completions",
            body=json.dumps(file_content).encode("utf-8")
        )


@pytest.fixture
def mock_deployment_api(
        datarobot_endpoint,
        model_id,
        deployment_id,
        prediction_server_id,
        prediction_api_url,
        prediction_api_key,
        feedback_endpoint,
        is_model_specific,
        custom_metric_id,
        custom_metric_endpoint
):
    responses.get(
        f"{datarobot_endpoint}/deployments/{deployment_id}/",
        json={
            "id": deployment_id,
            "label": "LLM Q&A App",
            "model": {
                "id": model_id,
                "targetName": "resultText",
                "targetType": "TextGeneration",
                "type": "LLM Q&A App"
            },
            "defaultPredictionServer": {
                "id": prediction_server_id,
                "url": prediction_api_url,
                "datarobot-key": prediction_api_key,
                "suspended": False,
            },
        },
    )

    responses.get(
        f"{datarobot_endpoint}/deployments/{deployment_id}/settings/",
        json={
            "associationId": {
                "columnNames": [
                    "a_id"
                ],
                "requiredInPredictionRequests": False,
                "autoGenerateId": False,
            },
        },
    )

    responses.get(
        f"{datarobot_endpoint}/deployments/{deployment_id}/capabilities/",
        json={'data': [{'messages': ['Retraining is not supported.'],
                        'name': 'supports_retraining',
                        'supported': False},
                       {'messages': [],
                        'name': 'supports_chat_api',
                        'supported': True}]},
    )

    responses.post(
        feedback_endpoint,
        json=None,
    )

    responses.get(
        custom_metric_endpoint,
        json={
            "type": "average",
            "createdAt": "2024-08-13 08:04:50.728000",
            "createdBy": {
              "id": "66b2277149462769e9b580ce"
            },
            "name": "Feedback",
            "units": "Upvoted%",
            "isModelSpecific": is_model_specific,
            "directionality": "higherIsBetter",
            "timeStep": "hour",
            "baselineValues": [
                {
                  "value": 0.75
                }
            ],
            "timestamp": {
                "columnName": "timestamp",
                "timeFormat": None
            },
            "value": {
                "columnName": "value"
            },
            "sampleCount": {
                "columnName": "sample_count"
            },
            "batch": {
                "columnName": "batch"
            },
            "associationId": {
                "columnName": "association_id"
            },
            "description": "Upvote reaction from the Q&A app",
            "displayChart": True,
            "categories": None,
            "id": custom_metric_id
        },
    )


def find_request_by_url(calls, url):
    return next(
        (c for c in calls if c.request.url == url),
        None,  # Return None if no matching call is found
    )


def create_chat_completion(mock_file):
    current_dir = os.path.dirname(__file__)

    file_path = os.path.join(current_dir, f"mocks/{mock_file}")
    with open(file_path, "r") as chunk_file_content:
        mock_data = json.load(chunk_file_content)

        citations = None
        datarobot_moderations = None
        if mock_data.get('citations'):
            citations = mock_data.get("citations")
        if mock_data.get('datarobot_moderations'):
            datarobot_moderations = mock_data.get("datarobot_moderations")

        return ChatCompletion(
            id=mock_data.get("id"),
            model='datarobot-deployed-llm',
            object=mock_data.get("object"),
            choices=[
                Choice(
                    finish_reason="stop",
                    index=0,
                    message=ChatCompletionMessage(
                        content=mock_data.get("choices")[0].get("message").get("content"),
                        role=mock_data.get("choices")[0].get("message").get("role"),
                    ),
                )
            ],
            created=mock_data.get("created"),
            citations=citations,
            datarobot_moderations=datarobot_moderations,
        )


def create_stream_chat_completion(chunk_files):
    current_dir = os.path.dirname(__file__)

    for filename in chunk_files:
        file_path = os.path.join(current_dir, f"mocks/{filename}")
        with open(file_path, "r") as chunk_file_content:
            chunk_data = json.load(chunk_file_content)

            citations = None
            datarobot_moderations = None
            if chunk_data.get('citations'):
                citations = chunk_data.get("citations")
            if chunk_data.get('datarobot_moderations'):
                datarobot_moderations = chunk_data.get("datarobot_moderations")

            yield ChatCompletionChunk(
                id=chunk_data.get("id"),
                model='datarobot-deployed-llm',
                object=chunk_data.get("object"),
                choices=[
                    StreamChoice(
                        index=chunk_data.get("choices")[0].get("index"),
                        finish_reason=chunk_data.get("choices")[0].get("finish_reason"),
                        delta=ChoiceDelta(
                            content=chunk_data.get("choices")[0].get("delta").get("content"),
                            role=chunk_data.get("choices")[0].get("delta").get("role"),
                        )
                    ),
                ],
                created=chunk_data.get("created"),
                citations=citations,
                datarobot_moderations=datarobot_moderations,
            )


@pytest.fixture
def mock_bad_request_error(datarobot_endpoint, deployment_id):
    def raise_bad_request_error(model, messages):
        mock_response = httpx.Response(
            status_code=400,
            request=httpx.Request("POST", f"{datarobot_endpoint}/deployments/{deployment_id}/"),
            content=b'{"message": "ERROR: The LLM has received an invalid request."}'
        )
        raise BadRequestError(
            message="Mock bad request error",
            response=mock_response,
            body={"message": "ERROR: The LLM has received an invalid request."}
        )

    return raise_bad_request_error
