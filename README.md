# Q&A Custom Application Template

![App Demo gif](https://github.com/datarobot-oss/qa-app-streamlit/blob/main/assets/qa_app_demo.gif)

## Repository overview

In this repository you will find the Q&amp;A Streamlit application code template used within DataRobot. The application uses a styling library for Streamlit called `streamlit-sal`, ([read more](https://github.com/datarobot-oss/streamlit-sal)).


## Deployment configuration

The deployment used for this Q&A application needs to have a configured association ID and automatic association ID generation enabled.

This setting can be found by navigating to **Console > Deployments > `<Your deployment>` > Settings > Custom metrics**.

The `Association ID` name can be set to anything other than the reserved `promptText` or `resultText` values.


## Configuration

You can run the Q&amp;A app in DataRobot using a custom application or by running the Streamlit app directly. Custom applications can be created via the Registry's Apps workshop or by
using [DRApps](https://github.com/datarobot/dr-apps/blob/main/README.md).

**Dependencies** are managed with [uv](https://github.com/astral-sh/uv). Install and run locally:

```sh
cd src/
uv sync
streamlit-sal compile
streamlit run --server.port=8080 qa_chat_bot.py
```

Alternatively, run `start-app.sh` directly from the app src:

```sh
cd src/
./start-app.sh
```

When running locally, set the DataRobot credentials as environment variables:

```shell
export DATAROBOT_API_TOKEN="<your API token>"   # From DataRobot Developer Tools
export DATAROBOT_ENDPOINT="https://app.datarobot.com/api/v2"
export DEPLOYMENT_ID="<your deployment id>"     # Optional: omit to use LLM Gateway mode
export CUSTOM_METRIC_ID="<custom metric id>"    # Optional: enables feedback buttons
```

When deployed as a Custom Application, these are injected automatically via runtime parameters.

To run the tests:

```sh
./run_tests.sh
```

## Chat API

LLM Blueprints created via DataRobot's Playground now support OpenAI's Chat API. The chat completion endpoint is made
available via the deployment on: `<API_URL>/deployments/<deployment_id>/chat/completions`.
Documentation for this API can be found [here](https://docs.datarobot.com/en/docs/gen-ai/genai-code/genai-chat-completion-api.html) or in the [OpenAI docs](https://platform.openai.com/docs/api-reference/chat).

To enable Chat API, select a deployment that supports it and set the runtime parameter `ENABLE_CHAT_API` to `True`.
If the selected deployment does _not_ support Chat API, it will automatically use the `datarobot-predict`
library by default.

DataRobot only supports streaming for GPT blueprints and the response always contains only one chunk due to the applied prompt and/or resulting text guards.

Streaming can be enabled in the runtime parameters by setting `ENABLE_CHAT_API_STREAMING` to `True`.

A system prompt can be configured using the `SYSTEM_PROMPT` runtime parameter. This value will overwrite any previous prompts
set, including configuration from **Workbench > Playground**.

The Q&amp;A app uses the reserved model name `datarobot-deployed-llm` when making requests through the Chat API. This is due to the 
openai client requiring the model parameter to be set. By using this reserved value, the Chat completion endpoint will use the default model used when creating the custom model 
used in the deployment. If you have multiple models within your deployment, you can modify this parameter by changing
the `DEFAULT_CHAT_MODEL_NAME` in `constants.py`

## VDB metadata filtering

When the deployment is backed by a Vector Database (VDB), the app can filter which documents are searched before retrieval. This narrows the context passed to the LLM — useful for scoping responses to a specific topic, document set, or time period.

> **Note:** Metadata filtering is a retrieval hint, not an access control mechanism. Filters are supplied by the client and are not enforced server-side. Do not rely on them for security or tenant isolation.

Filtering is opt-in and controlled by two runtime parameters:

| Parameter | Type | Description |
|-----------|------|-------------|
| `VDB_METADATA_COLUMNS` | `string` | Comma-separated list of metadata column names available in the VDB. When set, a **Document Filters** sidebar appears and users can add filters at runtime. Example: `source` |
| `VDB_METADATA_FILTER` | `string` | Default filter applied silently to every request, regardless of the sidebar. JSON object. Example: `{"source": "onboarding.txt"}` |

**What columns can I use?**

Available columns depend on how the VDB was created:
- A VDB built from a plain ZIP of text files only has `source` (the document filename inside the ZIP).
- A VDB created with an attached metadata CSV can have additional columns (`department`, `version`, etc.) — check the VDB configuration in **Console > GenAI > Vector Databases**.

**How filtering works**

Filters are passed to the Chat API as `metadata_filter` in the request body. The VDB restricts its similarity search to chunks whose metadata matches all active filters (AND logic). Any field name not present in the VDB's metadata columns will cause a 500 error — set `VDB_METADATA_COLUMNS` to the actual column names to prevent users from entering invalid fields.

**Example setup**

For a VDB built from a ZIP of text files, set:
```
VDB_METADATA_COLUMNS = source
```

Users can then filter by filename, e.g. `source = quarterly_report_q1.txt`.

To pre-apply a filter for all users without exposing the sidebar, set only:
```
VDB_METADATA_FILTER = {"source": "quarterly_report_q1.txt"}
```

## LLM Gateway mode

When `DEPLOYMENT_ID` is not set, the app routes requests through the DataRobot LLM Gateway via [LiteLLM](https://github.com/BerriAI/litellm) instead of a specific deployment. This is useful for prototyping without a dedicated deployment.

The model is configured via the `DATAROBOT_LLM_MODEL` runtime parameter (default: `datarobot/azure/gpt-5-1-2025-11-13`). Available models can be listed with `datarobot.genai.LLMGatewayCatalog().list_as_dict()`.

In this mode, feedback buttons and citations are not available (these require a deployment).

## App modifications

The app is split into multiple files to make it easy to modify:

- `qa_chat_bot.py`: The main app function that includes all other necessary files. Here you can modify the basic page
  configuration (title, favicon, width) and add any additional elements such as sidebar or links to additional subpages.
- `config.py`: Typed configuration class using `DataRobotAppFrameworkBaseSettings`. Add fields here to expose new runtime parameters.
- `constants.py`: This file contains all translatable strings, app and user configuration.
- `components.py`: Here you will find the render functions for both customized and default streamlit elements used
  within the app.
- `dr_requests.py`: In this file you will find all DataRobot API request functions.
- `styles/main.scss`: This SASS stylesheet will be compiled to CSS on app start, it is used to customize Streamlit
  native components via SAL. You can compile it manually by running `streamlit-sal compile`.
- `styles/variables.scss`: Here you can modify various CSS variables such as colors, or borders.
- `.streamlit/config.toml`: This is the Streamlit configuration file. Under `[theme]` you can define your own app
  colors. Please note that a full app restart is necessary for the values to take effect.

## How to add and use runtime parameters?

Declare parameters in `metadata.yaml` in your application source folder:

```yaml
runtimeParameterDefinitions:
- fieldName: EXAMPLE_VALUE
  type: string
```

Once this file is part of your Application source in DataRobot, it will display the new runtime parameter(s) as part of the app configuration.

Add the corresponding field to `Config` in `config.py`:

```python
class Config(DataRobotAppFrameworkBaseSettings):
    example_value: str = "default"
```

`Config()` reads the runtime parameter value automatically — no `start-app.sh` changes needed.

If you'd like to know more about runtime parameters, you can read more in
our [DataRobot Docs](https://docs.datarobot.com/en/docs/workbench/nxt-registry/nxt-apps-workshop/nxt-manage-custom-app.html#runtime-parameters)

## Feedback custom metric

The application uses the association ID from the deployment to match the LLM response with the given feedback. Navigate
to **Console -> Deployment -> Settings -> Custom metrics** and set the `Association ID` to `message_id`. 

Feedback buttons on LLM responses will only appear if the `CUSTOM_METRIC_ID` environment variable has been set.
Below is an example of a metric for thumbs up and down, you can add it by navigating to **Console -> Deployment ->
Monitoring ->Custom metrics** .

- Name: Feedback
- Metric ID: -- Copy this for the runtime parameter --
- Description: Feedback on LLM response
- Y-axis: +1/-1
- Baseline: 0
- Aggregation type: Average
- Higher is better

![Custom Metric Example](https://github.com/datarobot-oss/qa-app-streamlit/blob/main/assets/custom_metric_example.png)

## Troubleshooting

| Error                                                                                                                         | Solution                                                                                                                              |
|:------------------------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------|
| `Could not find root directory. Did you run 'streamlit-sal init'?`                                                            | Make sure that all application src files have been uploaded, including dotfiles: `.streamlit-sal` (file) and `.streamlit` (directory) |
| `500 Internal Server Error - ERROR: <any>`                                                                                    | Check the deployment runtime logs for additional error details. Navigate to **Console > Deployments > Actions > View logs**           |
| `Amazon Bedrock invalid request error: [400] Code: ValidationException. Message: The provided model identifier is invalid.."` | Make sure that the AWS_REGION set in the Model registry matches your AWS credentials                                                  |
| `500 Chat API returned an error — Vector database request returned an error`                                                  | A metadata filter uses a field not present in the VDB schema. Set `VDB_METADATA_COLUMNS` to the actual column names (e.g. `source`) so users can only select valid fields. |
