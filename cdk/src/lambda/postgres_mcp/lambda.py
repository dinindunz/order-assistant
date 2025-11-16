"""
Lambda handler for PostgreSQL MCP Server
This Lambda function hosts the awslabs.postgres-mcp-server
"""

import json
import os
import subprocess
import boto3
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
secrets_client = boto3.client("secretsmanager")


def get_db_credentials():
    """Retrieve database credentials from Secrets Manager"""
    logger.info("Retrieving database credentials from Secrets Manager")
    secret_arn = os.environ.get("POSTGRES_SECRET_ARN")
    if not secret_arn:
        logger.error("POSTGRES_SECRET_ARN environment variable not set")
        raise ValueError("POSTGRES_SECRET_ARN environment variable not set")

    logger.info(f"Fetching secret from ARN: {secret_arn}")
    response = secrets_client.get_secret_value(SecretId=secret_arn)
    secret = json.loads(response["SecretString"])

    logger.info(f"Successfully retrieved credentials for user: {secret['username']}")
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
    logger.info("=== PostgreSQL MCP Lambda Handler Started ===")
    logger.info(f"Request ID: {context.aws_request_id}")

    # Log the incoming event (sanitized)
    logger.info(f"Event keys: {list(event.keys())}")

    # Get database credentials from Secrets Manager
    try:
        credentials = get_db_credentials()
    except Exception as e:
        logger.error(f"Failed to retrieve database credentials: {str(e)}", exc_info=True)
        raise

    # Set up environment variables from Lambda configuration
    env = os.environ.copy()

    # Add database credentials to environment
    env["POSTGRES_USER"] = credentials["username"]
    env["POSTGRES_PASSWORD"] = credentials["password"]

    # Log database connection details (without password)
    logger.info(f"Database connection config:")
    logger.info(f"  POSTGRES_HOST: {env.get('POSTGRES_HOST', 'NOT SET')}")
    logger.info(f"  POSTGRES_PORT: {env.get('POSTGRES_PORT', 'NOT SET')}")
    logger.info(f"  POSTGRES_DB: {env.get('POSTGRES_DB', 'NOT SET')}")
    logger.info(f"  POSTGRES_USER: {env.get('POSTGRES_USER', 'NOT SET')}")

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

        logger.info(f"MCP Request - Method: {method}, Request ID: {request_id}")
        logger.info(f"MCP Request - Params: {json.dumps(params, indent=2)}")

        # Run the MCP server command
        # The PostgreSQL MCP server uses environment variables for connection:
        # - POSTGRES_HOST
        # - POSTGRES_PORT
        # - POSTGRES_DB
        # - POSTGRES_USER
        # - POSTGRES_PASSWORD

        logger.info("Executing PostgreSQL MCP server via uvx...")
        logger.info(f"Input to MCP server: {json.dumps(body, indent=2)}")

        result = subprocess.run(
            ["uvx", "awslabs.postgres-mcp-server@latest"],
            input=json.dumps(body),
            capture_output=True,
            text=True,
            env=env,
            timeout=300,  # 5 minute timeout
        )

        logger.info(f"MCP server process completed with return code: {result.returncode}")

        if result.stdout:
            logger.info(f"MCP server stdout: {result.stdout}")
        if result.stderr:
            logger.warning(f"MCP server stderr: {result.stderr}")

        if result.returncode == 0:
            try:
                response_data = json.loads(result.stdout) if result.stdout else {}
                logger.info(f"MCP server response parsed successfully")
                logger.info(f"Response data: {json.dumps(response_data, indent=2)}")
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(response_data),
                }
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse MCP server response as JSON: {str(e)}")
                logger.error(f"Raw stdout: {result.stdout}")
                return {
                    "statusCode": 500,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(
                        {
                            "error": "Failed to parse MCP server response",
                            "details": str(e),
                            "raw_output": result.stdout,
                        }
                    ),
                }
        else:
            logger.error(f"MCP server failed with return code {result.returncode}")
            logger.error(f"stderr: {result.stderr}")
            error_response = {
                "error": "MCP server error",
                "stderr": result.stderr,
                "stdout": result.stdout,
                "returncode": result.returncode,
            }
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(error_response),
            }

    except subprocess.TimeoutExpired as e:
        logger.error(f"MCP server execution timed out after 300 seconds", exc_info=True)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "MCP server execution timeout",
                "type": "TimeoutExpired",
                "details": str(e),
            }),
        }
    except Exception as e:
        logger.error(f"Unexpected error in Lambda handler: {str(e)}", exc_info=True)
        logger.error(f"Exception type: {type(e).__name__}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": str(e),
                "type": type(e).__name__,
            }),
        }
