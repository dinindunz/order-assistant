# Use AWS Lambda Python base image
FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.12

# Install PostgreSQL client libraries (runtime dependency for psycopg)
# Amazon Linux 2023 uses dnf instead of yum
RUN dnf install -y postgresql15 && \
    dnf clean all && \
    rm -rf /var/cache/dnf

# Install uv (which includes uvx)
RUN pip install --no-cache-dir uv

# Set UV directories to /opt (readable at runtime, writable at build time)
ENV UV_TOOL_DIR=/opt/uv/tools
ENV UV_TOOL_BIN_DIR=/opt/uv/bin
ENV UV_CACHE_DIR=/tmp/uv_cache
ENV XDG_CACHE_HOME=/tmp

# Pre-install the PostgreSQL MCP server with uv
# This installs to /opt/uv which is readable at runtime
RUN uv tool install awslabs.postgres-mcp-server

# Add uv bin directory to PATH so the tool can be found
ENV PATH="/opt/uv/bin:${PATH}"

# Copy function code
COPY lambda.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler
CMD [ "lambda.handler" ]
