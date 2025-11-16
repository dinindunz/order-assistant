"""
Lambda handler for Custom DynamoDB Tools
This Lambda function provides custom tools for order management
"""

import json
import os
import boto3
import logging
from datetime import datetime
from decimal import Decimal

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")


def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def place_order(customer_id, customer_name, items, total_amount, delivery_address=None):
    """
    Place a new order in the orders table.
    Args:
        customer_id (str): Unique identifier for the customer
        customer_name (str): Name of the customer
        items (list): List of order items with product details
        total_amount (float): Total order amount
        delivery_address (str, optional): Delivery address
    Returns:
        dict: Order confirmation with order_id and details
    """
    logger.info(f"Placing order for customer: {customer_id}")

    try:
        table_name = os.environ.get("ORDERS_TABLE_NAME")
        if not table_name:
            raise ValueError("ORDERS_TABLE_NAME environment variable not set")

        table = dynamodb.Table(table_name)

        # Generate order ID
        timestamp = datetime.utcnow()
        order_id = f"ORD-{timestamp.strftime('%Y%m%d%H%M%S')}-{customer_id[:8]}"

        # Prepare order item
        order = {
            "order_id": order_id,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "items": items,
            "total_amount": Decimal(str(total_amount)),
            "order_status": "PENDING",
            "created_at": timestamp.isoformat(),
            "updated_at": timestamp.isoformat(),
        }

        if delivery_address:
            order["delivery_address"] = delivery_address

        # Put item in DynamoDB
        table.put_item(Item=order)

        logger.info(f"Order placed successfully: {order_id}")

        # Return confirmation (convert Decimal for JSON serialization)
        return {
            "order_id": order_id,
            "customer_id": customer_id,
            "customer_name": customer_name,
            "total_amount": float(total_amount),
            "order_status": "PENDING",
            "created_at": timestamp.isoformat(),
            "message": f"Order {order_id} placed successfully",
        }

    except Exception as e:
        logger.error(f"Error placing order: {str(e)}", exc_info=True)
        raise


def get_order(order_id):
    """
    Retrieve order details by order_id.
    Args:
        order_id (str): The order ID to retrieve
    Returns:
        dict: Order details
    """
    logger.info(f"Retrieving order: {order_id}")

    try:
        table_name = os.environ.get("ORDERS_TABLE_NAME")
        if not table_name:
            raise ValueError("ORDERS_TABLE_NAME environment variable not set")

        table = dynamodb.Table(table_name)

        response = table.get_item(Key={"order_id": order_id})

        if "Item" not in response:
            logger.info(f"Order not found: {order_id}")
            return {"error": f"Order {order_id} not found"}

        order = response["Item"]
        logger.info(f"Order retrieved successfully: {order_id}")

        # Convert Decimal to float for JSON serialization
        return json.loads(json.dumps(order, default=decimal_default))

    except Exception as e:
        logger.error(f"Error retrieving order: {str(e)}", exc_info=True)
        raise


def update_order_status(order_id, new_status):
    """
    Update the status of an existing order.
    Args:
        order_id (str): The order ID to update
        new_status (str): New status (e.g., CONFIRMED, PROCESSING, SHIPPED, DELIVERED, CANCELLED)
    Returns:
        dict: Updated order details
    """
    logger.info(f"Updating order {order_id} status to {new_status}")

    try:
        table_name = os.environ.get("ORDERS_TABLE_NAME")
        if not table_name:
            raise ValueError("ORDERS_TABLE_NAME environment variable not set")

        table = dynamodb.Table(table_name)

        # Update the order status
        response = table.update_item(
            Key={"order_id": order_id},
            UpdateExpression="SET order_status = :status, updated_at = :updated",
            ExpressionAttributeValues={
                ":status": new_status,
                ":updated": datetime.utcnow().isoformat(),
            },
            ReturnValues="ALL_NEW",
        )

        if "Attributes" not in response:
            logger.warning(f"Order not found for update: {order_id}")
            return {"error": f"Order {order_id} not found"}

        updated_order = response["Attributes"]
        logger.info(f"Order status updated successfully: {order_id}")

        # Convert Decimal to float for JSON serialization
        return json.loads(json.dumps(updated_order, default=decimal_default))

    except Exception as e:
        logger.error(f"Error updating order status: {str(e)}", exc_info=True)
        raise


def handler(event, context):
    """
    Lambda handler - Gateway sends tool parameters directly in event
    Event formats:
    - place_order: {"customer_id": "...", "customer_name": "...", "items": [...], "total_amount": 123.45, "delivery_address": "..."}
    - get_order: {"order_id": "ORD-..."}
    - update_order_status: {"order_id": "ORD-...", "new_status": "CONFIRMED"}
    """
    logger.info("=== DynamoDB Custom Tools Lambda Handler Started ===")
    logger.info(f"Request ID: {context.aws_request_id}")
    logger.info(f"Event: {json.dumps(event, default=str)}")

    try:
        # Determine which tool based on event content
        if "customer_id" in event and "items" in event:
            # place_order
            logger.info("Tool: place_order")
            customer_id = event.get("customer_id")
            customer_name = event.get("customer_name")
            items = event.get("items", [])
            total_amount = event.get("total_amount")
            delivery_address = event.get("delivery_address")

            if (
                not customer_id
                or not customer_name
                or not items
                or total_amount is None
            ):
                raise ValueError(
                    "customer_id, customer_name, items, and total_amount are required"
                )

            result = place_order(
                customer_id, customer_name, items, total_amount, delivery_address
            )

        elif "order_id" in event and "new_status" in event:
            # update_order_status
            logger.info("Tool: update_order_status")
            order_id = event.get("order_id")
            new_status = event.get("new_status")

            if not order_id or not new_status:
                raise ValueError("order_id and new_status are required")

            result = update_order_status(order_id, new_status)

        elif "order_id" in event:
            # get_order
            logger.info("Tool: get_order")
            order_id = event.get("order_id")

            if not order_id:
                raise ValueError("order_id is required")

            result = get_order(order_id)

        else:
            # Unknown format
            logger.error("Unknown event format")
            return {
                "statusCode": 400,
                "body": json.dumps(
                    {
                        "error": "Invalid request format",
                        "expected": "One of: place_order, get_order, update_order_status",
                        "received_keys": list(event.keys()),
                    }
                ),
            }

        logger.info(f"✓ Tool execution successful")

        # Return simple JSON response
        return {
            "statusCode": 200,
            "body": json.dumps(result, default=decimal_default),
        }

    except ValueError as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        return {
            "statusCode": 400,
            "body": json.dumps(
                {
                    "error": "Validation error",
                    "details": str(e),
                }
            ),
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "error": str(e),
                    "type": type(e).__name__,
                }
            ),
        }
