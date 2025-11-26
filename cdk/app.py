#!/usr/bin/env python3
import aws_cdk as cdk
from stack import OrderAssistantStack
import boto3

# Get account and region from AWS session (uses AWS profile configuration)
session = boto3.Session()
sts_client = session.client("sts")
account = sts_client.get_caller_identity()["Account"]
region = session.region_name

app = cdk.App()
OrderAssistantStack(
    app,
    "OrderAssistantStack",
    env=cdk.Environment(account=account, region=region),
)

app.synth()
