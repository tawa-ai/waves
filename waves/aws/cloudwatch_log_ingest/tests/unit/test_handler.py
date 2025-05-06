import base64
import gzip
import json
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest
from aws_lambda_typing import context as context_
from aws_lambda_typing import events

from cloudwatch_log_ingest import handler as handler


class MockedGCloudLogger:
    def __init__(self, log_name: str) -> None:
        self.log_name = log_name
        self.internal_data_house_struct_data: List[Dict[str, Any]] = []
        self.internal_data_house_label_data: List[Optional[Dict[str, Any]]] = []

    def log_struct(self, struct_data: Dict[str, Any], labels: Optional[Dict[str, Any]] = None) -> None:
        # save the data into the internal data store
        self.internal_data_house_struct_data.append(struct_data)
        self.internal_data_house_label_data.append(labels)


class MockedGCloudLoggingClient:
    def __init__(self) -> None:
        self.tested_logger: Optional[MockedGCloudLogger] = None

    def logger(self, log_name: str) -> MockedGCloudLogger:
        if not self.tested_logger:
            self.tested_logger = MockedGCloudLogger(log_name)
        return self.tested_logger


@pytest.mark.parametrize(
    "log_events,log_stream",
    [
        (
            [{"message": "message zero"}, {"message": "message one"}],
            "unit_test/test_stream/test_event_with_data",
        )
    ],
)
def test_handler(log_events: List[Dict[str, str]], log_stream: str) -> None:
    packaged_data = {"logEvents": log_events, "logStream": log_stream}
    json_data = json.dumps(packaged_data)
    compressed_data = gzip.compress(json_data.encode("ascii"))
    encoded_data = base64.b64encode(compressed_data)
    cloud_watch_log_event = events.CloudWatchLogsEvent(
        awslogs=events.cloud_watch_logs.AWSLogs(
            data=encoded_data  # type: ignore
        )
    )
    test_context = context_.Context()
    test_client_context = context_.ClientContext(
        client=context_.Client(  # type: ignore
            app_title="test_handler", app_version_name="version", app_version_code="1"
        )
    )
    test_context.client_context = test_client_context
    test_context.aws_request_id = "unit test"

    mocked_client = MockedGCloudLoggingClient()
    with patch("cloudwatch_log_ingest.handler.GCloudLoggingClient", return_value=mocked_client):
        expected_job_name = log_stream.split("/")[0]
        expected_log_stream = log_stream
        expected_label_data = [{"jobName": expected_job_name, "logStream": expected_log_stream} for _ in log_events]
        handler.handler(event=cloud_watch_log_event, context=test_context)
        assert mocked_client.tested_logger is not None
        assert mocked_client.tested_logger.internal_data_house_struct_data == log_events
        assert mocked_client.tested_logger.internal_data_house_label_data == expected_label_data
