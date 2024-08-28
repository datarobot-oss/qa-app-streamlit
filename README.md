# Q&A Custom Application Template


## What's in this repository?
In this repository you will find the Q &amp; A Streamlit application code template that is used within DataRobot.

It comes with a DR components package, a collection of custom components built by DataRobot. A more thorough guide on
the use of these components will follow soon.

## How do I set it up?

You can run the app in a similar environment as to how DataRobot will run it in Docker via Custom Applications
or run the Streamlit app directly.

Make sure to define the variables for the app to talk to DataRobot: 
###
```shell
export token="$DATAROBOT_API_TOKEN"  # Your API token from DR developer tools page
export endpoint="$DATAROBOT_ENDPOINT"  # Example: https://app.datarobot.com/api/v2/
export deployment_id="$DEPLOYMENT_ID"  # ID of the deploy
export custom_metric_id="$CUSTOM_METRIC_ID"  # Optional: Response feedback metric id 
```

### With Docker
```sh
docker build -t your_container_name .
```

### Without Docker
```sh
pip install --no-cache-dir 'streamlit==1.31.0' 'streamlit_extras==0.3.6' 'datarobot==3.3.1' 'responses==0.22.0'
pip install --no-cache-dir ./packages/dr_components-0.1.4-py3-none-any.whl

streamlit run --server.port=8080 qa-streamlit.py
```

## Troubleshooting

### Datarobot Client error
If your DR client within the app doesn't connect properly try to disable `set_client(Client())`
and instead use `dr.Client(token=token, endpoint=endpoint)` at the top of the app code.
You might also need to `import datarobot as dr`

### The app within local Docker does not load
Streamlit within a local Docker can cause issues. Try to add the docker address into your `.streamlit/config.toml` and
restart the app (On Macs this might be `host.docker.internal`)
```toml
[browser]
serverAddress = "172.17.0.1"
```

