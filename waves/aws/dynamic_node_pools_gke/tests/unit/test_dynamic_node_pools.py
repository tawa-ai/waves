import base64
import gzip
import json
import os
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

import pytest
from aws_lambda_typing import context as context_
from aws_lambda_typing import events
from templafirm.core.templater import Templater

from dynamic_node_pools_gke import handler as handler

from ..utils.contract_utils import form_input_contract_mrdma_node_pool


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


async def mock_apply(tf_file_path: str) -> Tuple[bytes, bytes]:
    return f"ran apply for {tf_file_path}".encode("utf-8"), b""


@pytest.mark.parametrize(
    "node_pool_creation_kwargs, expected_tf_file_content",
    [
        (
            {
                "namespace": "test-namespace",
                "node_information": {
                    "cluster_name": "test-cluster",
                    "disk_size": 1000,
                    "disk_type": "hyper-disk",
                    "ephemeral_storage_local_ssd_count": 1,
                    "gpu_accelerator_count": 4,
                    "gpu_accelerator_type": "h100",
                    "gcp_project_id": "test-project",
                    "image_type": "cos",
                    "machine_type": "a3-highgpu-8g",
                    "node_region": "us-central1",
                    "node_zone": "a",
                    "placement_policy_type": "COMPACT",
                    "total_max_node_count": 0,
                    "total_min_node_count": 8,
                },
                "reservation_duration": 100,
                "reservation_id": "test-id",
                "reservation_time": "<datetime>",
                "reservation_type": "SPECIFIC_RESERVATION",
                "resource_version": "0.0.1",
            },
            'module "mrdma_node_pool_test-id" {\n  source = "../../modules/mrdma_node_pool/"\n\n  account_id                        = "test-project"\n  autoscaling                       = {\n    total_min_node_count = "8"\n    total_max_node_count = "0"\n  }\n  cluster_name                      = "test-cluster"\n  disk_size                         = "1000"\n  disk_type                         = "hyper-disk"\n  ephemeral_storage_local_ssd_count = "1"\n  gpu_accelerator                   = {\n    count = "4"\n    type  = "h100"\n  }\n  image_type                        = "cos"\n  labels                            = {"reservation_id": "test-id", "reservation_time": "<datetime>", "reservation_duration": "100"}\n  machine_type                      = "a3-highgpu-8g"\n  node_pool_name                    = "mrdma_node_pool_tester_test-id" \n  node_region                       = "us-central1"\n  node_sa_email                     = "maxweirz@gmail.com" \n  node_zone                         = "a"\n  placement_policy                  = {\n    type = "COMPACT"\n  }\n  reservation_affinity              = {\n    type = "SPECIFIC_RESERVATION"\n    reservations = ["test-id"]\n  }\n}',
        )
    ],
)
def test_handler(node_pool_creation_kwargs: Dict[str, str], expected_tf_file_content: str) -> None:
    input_contract = form_input_contract_mrdma_node_pool(node_pool_creation_kwargs)
    json_data = json.dumps(input_contract)
    compressed_data = gzip.compress(json_data.encode("ascii"))
    encoded_data = base64.b64encode(compressed_data)

    creation_event = events.EventBridgeEvent(  # type: ignore
        account="some_account",
        detail={"encoded_payload": encoded_data},
        event_type="node_pool_creation",
        id="test-id",
        region="us-west-2",
        resources=["some_resources(usually rule arn)"],
        source="controller",
        time="now",
        version="1",
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
    with patch("dynamic_node_pools_gke.handler.GCloudLoggingClient", return_value=mocked_client):
        with patch("dynamic_node_pools_gke.handler.apply_changes", mock_apply):
            handler.handler(event=creation_event, context=test_context)

            # find the path to the file
            templater = Templater()
            templater.activate_provider("gke")
            node_pool_dir = os.path.join(
                templater.return_provider("gke").provider.template_directory_path(), "node_pools"
            )
            output_path = os.path.join(node_pool_dir, "mrdma_node_pool_template.tf")

            assert os.path.exists(output_path)

            with open(output_path, "r") as open_template_buffer:
                templated_resource = "".join(open_template_buffer.readlines())
            assert templated_resource == expected_tf_file_content
