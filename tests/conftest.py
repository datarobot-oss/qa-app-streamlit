import json
import os
from unittest.mock import patch

import pytest
import responses
from bson import ObjectId


# Fixtures
@pytest.fixture(scope='module')
def deployment_id():
    return 'deployment_id_' + str(ObjectId())


@pytest.fixture(scope='module')
def custom_metric_id():
    return 'custom_metric_id_' + str(ObjectId())


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
def app_base_url(
    app_id
):
    return f"https://test-app.datarobot.com/custom_applications/{app_id}"


@pytest.fixture
def mock_set_env(
    monkeypatch,
    datarobot_token,
    datarobot_endpoint,
    custom_metric_id,
    deployment_id,
    app_base_url,
):
    with patch.dict(os.environ, clear=True):
        monkeypatch.setenv("token", datarobot_token)
        monkeypatch.setenv("endpoint", datarobot_endpoint)
        monkeypatch.setenv("custom_metric_id", custom_metric_id)
        monkeypatch.setenv("deployment_id", deployment_id)
        monkeypatch.setenv("app_base_url_path", app_base_url)
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
