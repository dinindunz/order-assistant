"""
Lambda handler for PostgreSQL MCP Server
This Lambda function hosts the awslabs.postgres-mcp-server
"""

import json
import os
import subprocess
import sys
import boto3
from pathlib import Path

# Initialize AWS clients
secrets_client = boto3.client("secretsmanager")


def get_db_credentials():
    """Retrieve database credentials from Secrets Manager"""
    secret_arn = os.environ.get("POSTGRES_SECRET_ARN")
    if not secret_arn:
        raise ValueError("POSTGRES_SECRET_ARN environment variable not set")

    response = secrets_client.get_secret_value(SecretId=secret_arn)
    secret = json.loads(response["SecretString"])

    return {
        "username": secret["username"],
        "password": secret["password"],
    }


def handler(event, context):
    """
    Lambda handler that runs the PostgreSQL MCP server

    The MCP server is executed using uvx (uv's command runner)
    Environment variables are passed through from Lambda configuration
    """

    # Get database credentials from Secrets Manager
    credentials = get_db_credentials()

    # Set up environment variables from Lambda configuration
    env = os.environ.copy()

    # Add database credentials to environment
    env["POSTGRES_USER"] = credentials["username"]
    env["POSTGRES_PASSWORD"] = credentials["password"]

    # Parse the incoming MCP request
    try:
        body = (
            json.loads(event.get("body", "{}"))
            if isinstance(event.get("body"), str)
            else event.get("body", {})
        )

        # For MCP protocol, we need to handle JSON-RPC style requests
        method = body.get("method", "")
        params = body.get("params", {})
        request_id = body.get("id", 1)

        # Run the MCP server command
        # The PostgreSQL MCP server uses environment variables for connection:
        # - POSTGRES_HOST
        # - POSTGRES_PORT
        # - POSTGRES_DB
        # - POSTGRES_USER
        # - POSTGRES_PASSWORD

        result = subprocess.run(
            ["uvx", "awslabs.postgres-mcp-server@latest"],
            input=json.dumps(body),
            capture_output=True,
            text=True,
            env=env,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode == 0:
            response_data = json.loads(result.stdout) if result.stdout else {}
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(response_data),
            }
        else:
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(
                    {
                        "error": "MCP server error",
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                    }
                ),
            }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e), "type": type(e).__name__}),
        }
