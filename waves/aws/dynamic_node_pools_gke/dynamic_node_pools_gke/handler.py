import base64
import gzip
import json
import logging
import os

from aws_lambda_typing import context as context_
from aws_lambda_typing import events
from google.cloud.logging import Client as GCloudLoggingClient

LOG_NAME = "aws-eventbridge"

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


def handler(event: events.CloudWatchLogsEvent, context: context_.Context) -> None:
    """Handles the creation of node pools dynamically in gke from aws lambda.  

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
    gcloud_logger = logging_client.logger(LOG_NAME)
    cw_data = event["awslogs"]["data"]
    cw_logs = base64.b64decode(cw_data)
    uncompressed_payload = gzip.decompress(cw_logs)
    payload = json.loads(uncompressed_payload)
    pass
