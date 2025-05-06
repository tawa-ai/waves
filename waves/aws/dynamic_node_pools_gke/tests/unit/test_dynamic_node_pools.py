import base64
import gzip
import json
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest
from aws_lambda_typing import context as context_
from aws_lambda_typing import events

from dynamic_node_pools_gke import handler as handler
