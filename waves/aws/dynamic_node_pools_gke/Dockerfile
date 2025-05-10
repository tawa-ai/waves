# https://docs.aws.amazon.com/lambda/latest/dg/images-create.html#runtimes-images-lp
# It is generally recommended to use the AWS provided Lambda images to base off
# They provide the runtime interface client already pre-installed and can be thought
# to be generally supported.
FROM public.ecr.aws/lambda/python:3.8.2024.10.30.15 AS base

# Copy from direct path, should be run from submodule root not repo root
COPY . .

RUN python -m pip install .

CMD ["dynamic_node_pools_gke.handler.handler"]
# Test stage is used for testing in CI!
FROM base AS test

# Install in test mode extras
RUN python -m pip install -e ".[test]"

ENTRYPOINT ["pytest"]

# Dev stage is used for local development
FROM test AS dev

# Install dev mode extras
RUN python -m pip install -e ".[dev,test]"

# Install vim as an editor
RUN yum update -y
RUN yum install vim -y

ENTRYPOINT ["/bin/bash"]
