from datarobot.core.config import DataRobotAppFrameworkBaseSettings

from constants import I18N_APP_NAME_DEFAULT


class Config(DataRobotAppFrameworkBaseSettings):
    """Application configuration.

    Reads variables from environment variables (including DataRobot Runtime Parameters),
    .env files, and file secrets — handled automatically by DataRobotAppFrameworkBaseSettings.

    DATAROBOT_API_TOKEN and DATAROBOT_ENDPOINT are provided by the base class and
    are injected automatically when running as a DataRobot Custom Application.

    Runtime Parameter names map directly to env var names (e.g. DEPLOYMENT_ID).
    """

    deployment_id: str | None = None
    custom_metric_id: str | None = None
    app_name: str = I18N_APP_NAME_DEFAULT
    system_prompt: str | None = None
    enable_chat_api: bool = True
    enable_chat_api_streaming: bool = False
    # APPLICATION_ID is injected by the DataRobot platform at runtime
    application_id: str | None = None
    # Full LiteLLM model string for the DataRobot LLM Gateway.
    # Used when DEPLOYMENT_ID is not set (gateway mode).
    # Find available models with: datarobot.genai.LLMGatewayCatalog().list_as_dict()
    # See: https://github.com/carsongee/get-datarobot-llms
    datarobot_llm_model: str = "datarobot/azure/gpt-4o-mini"
