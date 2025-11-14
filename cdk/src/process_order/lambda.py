import boto3
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

agentcore = boto3.client("bedrock-agentcore", region_name="ap-southeast-2")
ssm = boto3.client("ssm", region_name="ap-southeast-2")

# Get Agent ARN from SSM parameter
AGENT_ARN_PARAM = os.environ.get("AGENT_ARN_PARAM")
AGENT_ARN = None

def get_agent_arn():
    """Retrieve agent ARN from SSM parameter"""
    global AGENT_ARN
    if AGENT_ARN is None:
        response = ssm.get_parameter(Name=AGENT_ARN_PARAM)
        AGENT_ARN = response["Parameter"]["Value"]
        logger.info(f"Retrieved agent ARN from SSM: {AGENT_ARN}")
    return AGENT_ARN


def handler(event, context):
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]

    logger.info(f"Processing S3 file: s3://{bucket}/{key}")

    # Get agent ARN from SSM
    agent_arn = get_agent_arn()
    logger.info(f"Using agent ARN: {agent_arn}")

    session_id = f"session-{context.aws_request_id}"

    # Pass S3 location to agent instead of extracting text
    payload = {
        "s3_bucket": bucket,
        "s3_key": key
    }

    response = agentcore.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        runtimeSessionId=session_id,
        payload=json.dumps(payload),
        qualifier="DEFAULT",
    )
    response_body = response["response"].read()
    response_data = json.loads(response_body)
    logger.info("Agent Response received")

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(response_data),
    }
