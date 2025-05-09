import asyncio
import base64
import gzip
import json
import logging
import os
from dataclasses import asdict
from enum import Enum
from typing import Dict

from aws_lambda_typing import context as context_
from aws_lambda_typing import events
from dacite import Config, from_dict
from google.cloud.logging import Client as GCloudLoggingClient
from templafirm.core.templater import Templater

from dynamic_node_pools_gke.contract_structs import MRDMAResourceCreationContract
from dynamic_node_pools_gke.terraform import apply_changes, init_terraform, plan_changes

LOG_NAME = "aws-eventbridge"

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


class CastingMap(Enum):
    """Casting mapping for fields in payload to python types.

    Only field right now is the reservation_duration which goes from
    string to int, seconds of operation.
    """

    int = "details.payload.reservation_duration"


dacite_config = Config(cast=[CastingMap])


NODE_SA_EMAIL = "maxweirz@gmail.com"  # ToDo: SA account email service
TF_PLAN_COMMAND = "terraform plan -out plan.tfplan"


def contract_to_resource_template_dict(resource_data: MRDMAResourceCreationContract) -> Dict[str, str]:
    """Construct resource template dict from contract defined in the handler doc string.

    Args:
        resource_data (MRDMAResourceCreationContract): Resource data class, created from parsed contract.

    Returns:
        Dict[str, str]: Output dict corresponding to node pool template inputs.
    """
    resource_dict = asdict(resource_data.details.payload.node_information)
    resource_dict["resource_name"] = f"mrdma_node_pool_{resource_data.details.payload.reservation_id}"
    resource_dict["labels"] = {
        "reservation_id": resource_data.details.payload.reservation_id,
        "reservation_time": resource_data.details.payload.reservation_time,
        "reservation_duration": str(resource_data.details.payload.reservation_duration),
    }
    resource_dict["node_sa_email"] = NODE_SA_EMAIL  # todo: replace with service that knows the svc accounts per project
    resource_dict["reservation_ids"] = [resource_data.details.payload.reservation_id]
    resource_dict["reservation_type"] = resource_data.details.payload.reservation_type

    node_pool_name = f"mrdma_node_pool_{resource_data.source}_{resource_data.details.payload.reservation_id}"
    resource_dict["node_pool_name"] = node_pool_name
    return resource_dict


async def generate_template_file(resource_data: MRDMAResourceCreationContract) -> str:
    """Generate the template file through templater.

    Args:
        resource_data (MRDMAResourceCreationContract): Data corresponding to templating.

    Raises:
        ValueError: Raises if the version between request and provided diverges.

    Returns:
        str: Path to the created template file.
    """
    templater = Templater()
    templater.activate_provider("gke")
    if (
        templater.return_provider("gke").provider["mrdma_node_pool"].version
        != resource_data.details.payload.resource_version
    ):
        raise ValueError(
            f"Resource version is not consistent with expectation.\nRequested: {resource_data.details.payload.resource_version} but current templafirm version is {templater.return_provider('gke').provider['mrdma_node_pool'].version}"
        )

    template_input_dict = contract_to_resource_template_dict(resource_data)
    node_pool_dir = os.path.join(templater.return_provider("gke").provider.template_directory_path(), "node_pools")
    output_path = os.path.join(node_pool_dir, "mrdma_node_pool_template.tf")

    await templater.render_template_resource_to_file(
        output_path, template_input_dict, template_resource_name="mrdma_node_pool"
    )
    return output_path


def handler(event: events.EventBridgeEvent, context: context_.Context) -> None:
    """Handles the creation of node pools dynamically in gke from aws lambda.

    Input Contract (simplified for now):
    {
        "source": ["multicont"],
        "event-type": ["node_pool_creation"],
        "details": {
            "eventType": "ResourceCreation",
            "resourceId": {
                "type": "string",
                "value": <requester_uuid>
            },
            "payload": {
                "namespace": <uuid> (corresponds to namespace id in k8s),
                "reservation_time": <datetime> (time that the node pool reservation starts),
                "reservation_duration": <int> (seconds that the reservation exists),
                "reservation_id": <uuid> (corresponds to reservation and will tag the nodes),
                "resource_version": <int> (corresponds to the version of the resource),
                "node_information": {
                  "instance_type": <enum> (corresponds to instance type on gke), [eventually all cloud providers.],
                  "cluster_name" : <str> (name of the cluster in which to add node pool),
                  "disk_size": <int> (size of the disc to attach to vm),
                  "dist_type": <str> (type of disc to attach to vm),
                  "ephemeral_storage_local_ssd_count": <int> (count of ssd),
                  "gcp_project_id": <str> (project in which cluster resides),
                  "gpu_accelerator_count": <int> (count of gpus for the vms),
                  "gpu_accelerator_type": <str> (type of gpu attached to vm),
                  "image_type": <str> (what type of image to run on vm),
                  "labels": <mapping str -> str> (node labes),
                  "machine_type": <str> (type of vm),
                  "node_region": <str> (region of node pool),
                  "node_zone": <str> (zone of node pool),
                  "placement_policy_type": <str> (how to place the nodes),
                  "reservation_type": <str> (type of the reservation),
                  "total_max_node_count": <int> (total node count possible),
                  "total_min_node_count": <int> (min node count possible, keep at zero unless required.)
                }
            }
        }
    }

    Authentication:
    This is authenticated to gcp through iam federation, that is better seen in the infra repo in the
    same org. In that repo the lambda has an iam federation pool that is authenticated to this lambdas
    specific arn. This means that no more authentication is required in the source in this lambda.

    Args:
        event: Event in the function corresponds to aws eventbridge with input contract.
        context: Lambda function context, can see details here https://docs.aws.amazon.com/lambda/latest/dg/python-context.html
    """
    logging.debug(f"Started handler, request id is {context.aws_request_id}.")
    if context.client_context and context.client_context.get("client") and context.client_context:
        logging.debug(
            f"Handler was invoked with the following app title and version {context.client_context['client']['app_title']}, {context.client_context['client']['app_version_name']}:{context.client_context['client']['app_version_code']}."
        )

    logging.info("New event, creating gcloud client.")
    logging_client = GCloudLoggingClient()
    logging.info("GCloud logging client created")

    # create logging session for telemetry
    gcloud_logger = logging_client.logger(LOG_NAME)
    gcloud_logger.log_struct(
        {"message": "Beggining node pool creation lambda."}, labels={"event_type": "node_pool_creation"}
    )

    if event["event_type"] != "node_pool_creation":  # type: ignore
        gcloud_logger.log_struct({"message": ""})
        raise KeyError(f"Node pool creation event required. Got {event['event_type']}")  # type: ignore

    # provider includes gke as a default
    creation_event = base64.b64decode(event["detail"]["encoded_payload"])
    uncompressed_payload = gzip.decompress(creation_event)
    payload = json.loads(uncompressed_payload)

    node_pool_creation_contract = from_dict(
        data_class=MRDMAResourceCreationContract, data=payload, config=dacite_config
    )
    local_tf_path = asyncio.run(generate_template_file(node_pool_creation_contract))

    stdout, stderr = asyncio.run(init_terraform(local_tf_path))
    logging.debug(f"tf init stderr: \n{stderr.decode('utf-8')}")
    logging.debug(f"tf init stdout: \n{stdout.decode('utf-8')}")

    stdout, stderr = asyncio.run(
        plan_changes(
            local_tf_path,
            target_resource_name=f"mrdma_node_pool_{node_pool_creation_contract.details.payload.reservation_id}",
        )
    )
    logging.debug(f"tf plan stderr: \n{stderr.decode('utf-8')}")
    logging.debug(f"tf plan stdout: \n{stdout.decode('utf-8')}")

    stdout, stderr = asyncio.run(apply_changes(local_tf_path))
    logging.debug(f"tf plan stderr: \n{stderr.decode('utf-8')}")
    logging.debug(f"tf plan stdout: \n{stdout.decode('utf-8')}")
