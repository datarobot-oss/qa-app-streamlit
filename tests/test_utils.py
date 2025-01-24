import json
import os
import sys
from collections import namedtuple
from unittest.mock import patch

import pandas as pd
import pytest
import responses
from streamlit.testing.v1 import AppTest

from src import utils
from .conftest import find_request_by_url



def test_sanitize_messages_for_request():
    """Test when the input has no dollar signs."""
    input = [
        {"role": "system", "content": "Answer with just a number."},
        {"role": "user", "content": "What is 2+3?", "some_other_value": False, "meta_id": '123-321'},
        {"role": "assistant", "content": "5", "meta_id": '123-321'},
        {"role": "user", "content": "Now multiply the result by 4.", "meta_id": '987-321'},
        {"role": "assistant", "content": None, "meta_id": '987-321'},
        {"role": "user", "content": "Now divide the result by 2.", "meta_id": '444-666'},
        {"role": "assistant", "content": "2.5", "meta_id": '444-666'},
    ]

    expected_output = [
        {"role": "system", "content": "Answer with just a number."},
        {"role": "user", "content": "What is 2+3?"},
        {"role": "assistant", "content": "5"},
        {"role": "user", "content": "Now divide the result by 2."},
        {"role": "assistant", "content": "2.5"},
    ]
    assert utils.sanitize_messages_for_request(input) == expected_output