import boto3
import base64
from strands import tool

s3_client = boto3.client('s3')

@tool
def get_s3_image(bucket: str, key: str) -> dict:
    """
    Retrieve an image from S3 and return it as base64 encoded data.

    Args:
        bucket: S3 bucket name
        key: S3 object key

    Returns:
        Dictionary with base64 encoded image data and metadata
    """
    response = s3_client.get_object(Bucket=bucket, Key=key)
    image_data = response['Body'].read()

    return {
        "image_base64": base64.b64encode(image_data).decode('utf-8'),
        "content_type": response['ContentType'],
        "size": response['ContentLength'],
        "key": key
    }
