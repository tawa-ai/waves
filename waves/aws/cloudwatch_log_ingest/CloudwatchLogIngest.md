# Cloudwatch Log Ingest

Log ingestion from AWS Cloudwatch to GCP Logging for Sagemaker Jobs in Sagemaker.

## Overview

Cloudwatch Log Ingest Lambda is an AWS Lambda function used to forward the logs from a
Sagemaker job running in any region and environment to GCP Logging. This Lambda does the
forwarding by reading the Cloudwatch log stream and forwarding the messages directly to GCP
Logging (formerly called StackDriver) through IAM Federation. Users then view the logs in 
GCP Logging console on the project for Sagemaker training views.

## Use Case

AWS Cloudwatch logs are not very good and provide a poor interface for users to understand/debug
their workflows. These logs are deficient in that they lack an 
Elasticsearch deployment to search through the logs easily and orient by global timestamp.
Teams have asked for a solution to this problem. This Lambda provides that solution by forwarding the logs
to the much more user friendly service provided by GCP (GCP Logging). This allows teams to easily search 
through all of their global logs (from each rank and each gpu rank) which is not as easily doable in AWS.

## Implementation Details

- The Lambda is developed inside the latest (at the time of development) py3.8 Lambda base container.
  This comes with the Lambda client pre-installed making it easy to implement the python handler on
  top and containerize the workflow.
- This Lambda gets access to GCP through IAM Federation.
- This lambda should be pushed to ECR for each environment and regio 
- This Lambda is tested on local dev machine and in the deployment container as part of the CI. A more full integration  test will also be added in a subsequent PR and this will be updated.

## Input Contract

The input of the function is defined by the [CloudwatchLogsEvent](https://docs.aws.amazon.com/lambda/latest/dg/log-structure.html) and the function invocation [context](https://docs.aws.amazon.com/lambda/latest/dg/python-context.html).
These combine to form the input contract that is metabolized by the Lambda and used to log to GCP.

## Output Contract

The Lambda has two output pathways, the logs it forwards to GCP and its own operation logs saved to Cloudwatch Logs.

### GCP Logs

The Lambda defines its output logs by the GCP Project linked at GCP_PROJECT env variable.

A logger is created through the python gcp pypi package and links internally to the specified project. A 
[log struct](https://cloud.google.com/python/docs/reference/logging/latest/logger) call is then 
made through the logger object. This uses the 
[write rest endpoint](https://cloud.google.com/logging/docs/reference/v2/rest/v2/entries/write) 
to write the dict object to the service.

### Cloudwatch Logs

The Lambda function logs it's own telemetry to Cloudwatch and has the 
[roles](https://github.tmc-stargate.com/arene-ai/arene-ai-infra/blob/master/terraform/modules/user/aws/lambdas/cloudwatch_log_forwarder/iam.tf#L54-L67) to do that properly. These have the same contract as the Cloudwatch logs 
described above.

## Future Changes

These are small features that will be added in the future as this moves to prod deployment

1. [Pushing logs to different sinks based off meta data from the Sagemaker run](https://cloud.google.com/logging/docs/export/configure_export_v2)
2. [Restricting permissions for the svc accounts to improve least ownership principle](https://cloud.google.com/logging/docs/routing/user-managed-service-accounts)
3. [Hook up to Grafana](https://grafana.com/docs/grafana/latest/datasources/google-cloud-monitoring/)

## Development

Development of Lambdas is tricky because of the stateless nature of operation and the requirment of deployment
for full testing. Lambda also lacks an easy to use integration test feature, which might be the proper implementation.
For these reasons this module is hard to integration test fully leading to a slightly complex development cycle.

### Setup

This module comes with two development paths, local and containerized, the recommended pathway is containerized
on an x86 system, as the images are built on x86 arch in gh actions. Testing on arm is possible as lambda supports
both deployments, but is not recommended as it is not 1-1 with prod cloud deployments.

#### Local

As a python module you can simply pip install this package, for the management of the venv `pyenv virtualenv` is 
recommended. Follow the below steps, using `pyenv virtualenv`, to create a dev environment.

```bash

pyenv virtualenv 3.8.13 cloudwatch_log_forwarder
pyenv activate cloudwatch_log_forwarder
pip install --upgrade pip
pip install -e .

```

You can then run `pytest .` in the root of the submodule.

### Containerized

Because this is a containerized lambda you can simply build the docker image and run and develop from inside.
This requires mounting the current dir into the docker fs as read/write and running in interactive. Vim is already
installed in the dev target of the image for convience. Run the following to develop inside the container

```bash

docker build . --target dev -t cloudwatch_log_forwarder:latest
docker run -it -v $(pwd):/var/task:rw cloudwatch_log_forwarder

# Can run pytest inside for testing
pytest .

```
