# Q&A Custom Application Template

![App Demo gif](https://github.com/datarobot-oss/qa-app-streamlit/blob/main/assets/qa_app_demo.gif)

## Repository overview

In this repository you will find the Q&amp;A Streamlit application code template used within DataRobot. The application uses a styling library for Streamlit called `streamlit-sal`, ([read more](https://github.com/datarobot-oss/streamlit-sal)).

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

## Feedback custom metric

Feedback buttons on LLM responses will only appear if the `CUSTOM_METRIC_ID` environment variable has been set. Below is an example of a metric for thumbs up and down, you can add it by naviagting to **Console -> Deployment -> Monitoring ->Custom metrics** .

![Custom Metric Example](https://github.com/datarobot-oss/qa-app-streamlit/blob/main/assets/custom_metric_example.png)
