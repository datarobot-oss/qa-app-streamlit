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

Define the variables for the app to communicate with DataRobot. If you run the app locally or via another environment, then you'll need to set the env variables. When this app is run via
the **Applications** page, the variables are set automatically via runtime parameters set in the application source.

```shell
export token="$DATAROBOT_API_TOKEN"  # Your API token from DR developer tools page
export endpoint="$DATAROBOT_ENDPOINT"  # Example: https://app.datarobot.com/api/v2/
export deployment_id="$DEPLOYMENT_ID"  # ID of the deployment
export custom_metric_id="$CUSTOM_METRIC_ID"  # Optional: Response feedback custom metric id 
```

```sh
pip install --no-cache-dir -r requirements.txt

cd src/
streamlit-sal compile
streamlit run --server.port=8080 qa_chat_bot.py
```

Alternatively, run the `start-app.sh` directly from the app src:

```sh
cd src/
./start-app.sh
```

To run the tests use the shell script in the project root:

```sh
pip install -r requirements-dev.txt
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
openai client requiring the model parameter to be set. The Chat completion endpoint will then use the baked-in default model
of the deployment. If you have multiple models within your deployment, you can modify this parameter by changing
the `DEFAULT_CHAT_MODEL_NAME` in `constants.py`

## App modifications

The app is split into multiple files to make it easy to modify:

- `qa_chat_bot.py`: The main app function that includes all other necessary files. Here you can modify the basic page
  configuration (title, favicon, width) and add any additional elements such as sidebar or links to additional subpages.
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

Variables can be added in the metadata.yaml file in your application source folder. Here is an example of an API_TOKEN
which will create an environment variable called `MLOPS_RUNTIME_PARAM_EXAMPLE_VALUE`:
```yaml
runtimeParameterDefinitions:
- fieldName: EXAMPLE_VALUE
  type: string
```

Once this file is part of your Application source in DataRobot, it will display the new runtime parameter(s) as part of
the app configuration.

To use the parameters we recommend to add them via `start-app.sh`, add this conditional export before the
`streamlit-sal` and `streamlit` commands:
```shell
if [ -n "$MLOPS_RUNTIME_PARAM_EXAMPLE_VALUE" ]; then
  export example_value="$MLOPS_RUNTIME_PARAM_EXAMPLE_VALUE"
fi
```

Now you can use `os.getenv("example_value")` within your application code.
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
