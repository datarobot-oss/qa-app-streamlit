API_URL = '{base_url}/predApi/v1.0/deployments/{deployment_id}/predictions'  # noqa

# Don't change this. It is enforced server-side too.
MAX_PREDICTION_INPUT_SIZE_BYTES = 52428800  # 50 MB

DEFAULT_PROMPT_COLUMN_NAME = 'promptText'
DEFAULT_RESULT_COLUMN_NAME = 'resultText'

# Chat API
CHAT_CAPABILITIES_KEY = 'supports_chat_api'
# To disable chat api even when deployment supports it. Default set to True until there is full support
FORCE_DISABLE_CHAT_API = True

# Timeouts
CUSTOM_METRIC_SUBMIT_TIMEOUT_SECONDS = 60
PREDICTIONS_TIMEOUT_SECONDS = 60
CAPABILITIES_TIMEOUT_SECONDS = 20

# Set asset path or remote url
APP_LOGO = './assets/dr-logo-for-dark-bg.svg'
APP_FAVICON = './assets/favicon.png'
# Set app layout to either 'centered' or 'wide'
APP_LAYOUT = 'centered'
APP_EMPTY_CHAT_IMAGE = 'assets/empty_chat.svg'
APP_EMPTY_CHAT_IMAGE_WIDTH = 150


# If you have additional information to show in a sidebar, you can enable it here
SHOW_SIDEBAR = False
# Set whether sidebar should be expanded at app load. ('collapsed'/'expanded')
SIDEBAR_DEFAULT_STATE = 'expanded'

# Static current user info
USER_ID = "1"  # Currently remaining static
USER_DISPLAY_NAME = "You"
# Material icons codes: https://fonts.google.com/icons?icon.set=Material+Symbols&icon.style=Outlined
USER_AVATAR = ":material/person:"
LLM_AVATAR = ":material/smart_toy:"
LLM_DISPLAY_NAME = "LLM Deployment"

# Translations
I18N_APP_NAME = "Q&A Chat Application"
I18N_APP_DESCRIPTION = ""

I18N_RESPONSE_COST = "Cost"
I18N_RESPONSE_TOKENS = "Tokens"
I18N_RESPONSE_LATENCY = "Latency"
I18N_RESPONSE_CONFIDENCE = "Confidence"
I18N_FORMAT_CURRENCY = "${}"  # Place the currency before or after {}
I18N_FORMAT_LATENCY = "{}s"  # Place time unit before or after {}
I18N_FORMAT_CONFIDENCE = "{}%"  # Place unit before or after {}
I18N_INPUT_PLACEHOLDER = "Send a prompt"
I18N_LOADING_MESSAGE = "Waiting for LLM response..."
I18N_SPLASH_TITLE = "What do you want to know?"
I18N_SPLASH_TEXT = "Ask a question"
I18N_CITATION_BUTTON = "Citation"
I18N_CITATION_DIALOG_TITLE = "Citation"
I18N_CITATION_KEY_PROMPT = 'User prompt'
I18N_CITATION_KEY_ANSWER = 'Answer'
I18N_CITATION_KEY_CITATION = 'Citation'
I18N_CITATION_SOURCE_PAGE = '{} - Page: {}'
I18N_SHARE_BUTTON = "Share"
I18N_SHARE_DIALOG_TITLE = "Share Application"
I18N_DIALOG_CLOSE_BUTTON = "Close"
I18N_ACCESSIBILITY_LABEL_YOU = 'you'  # Name is not shown in the UI but is only set as an accessibility label
I18N_ACCESSIBILITY_LABEL_LLM = 'ai'  # Name is not shown in the UI but is only set as an accessibility label
I18N_NO_DEPLOYMENT_ID = "Required environment variable `DEPLOYMENT_ID` is not defined. Set the variable and rebuild the application"
I18N_NO_DEPLOYMENT_FOUND = "Could not find deployment with given id: {}"

STATUS_PENDING = 'PENDING'
STATUS_ERROR = 'ERROR'
STATUS_COMPLETED = 'COMPLETED'

ROLE_SYSTEM = 'system'
ROLE_USER = 'user'
ROLE_ASSISTANT = 'assistant'
