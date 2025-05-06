import base64
import gzip
import json
import logging
import os

from aws_lambda_typing import context as context_
from aws_lambda_typing import events
from google.cloud.logging import Client as GCloudLoggingClient

LOG_NAME = "aws-sagemaker"

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


def handler(event: events.CloudWatchLogsEvent, context: context_.Context) -> None:
    """Handles the transfer of data to GCP from Sagemaker Logs

    Args:
        event: Event in this function consists of raw data coming from awslogs
        in the sagemaker stream.
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

    if "logStream" in payload and payload["logStream"]:
        log_stream = payload["logStream"]
        job_name = log_stream.split("/")[0]
        logging.info(f"Set jobName to {job_name}")
    else:
        log_stream = "unnamed"
        job_name = "unnamed"
        logging.warning("No 'logStream' key in payload or is none, setting logStream and jobName to 'unnamed'")

    logging.debug(f"Starting events processing, have {context.get_remaining_time_in_millis()} millis remaining.")
    if "logEvents" in payload:
        for log_event in payload["logEvents"]:
            labels = {"jobName": job_name, "logStream": log_stream}
            gcloud_logger.log_struct({"message": log_event["message"]}, labels=labels)
            logging.debug(f"Finished processing event, have {context.get_remaining_time_in_millis()} millis remaining.")
    logging.info("All events logged to GCP, exiting")
