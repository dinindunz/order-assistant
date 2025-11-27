#!/usr/bin/env python3
import aws_cdk as cdk
from stack import OrderAssistantStack
import boto3

# Get account and region from AWS session (uses AWS profile configuration)
session = boto3.Session()
sts_client = session.client("sts")
account = sts_client.get_caller_identity()["Account"]
region = session.region_name

# Set region-specific phone number ID
phone_number_id_map = {
    "ap-southeast-2": "phone-number-id-f82a097f349f44798c5926fb29db1ac1",
    "us-west-2": "phone-number-id-cd90e10a5b8e40de869491764db21904",
}

if region not in phone_number_id_map:
    raise ValueError(f"Unsupported region: {region}. Supported regions: {list(phone_number_id_map.keys())}")

phone_number_id = phone_number_id_map[region]

app = cdk.App()
OrderAssistantStack(
    app,
    "OrderAssistantStack",
    phone_number_id=phone_number_id,
    env=cdk.Environment(account=account, region=region),
)

app.synth()
