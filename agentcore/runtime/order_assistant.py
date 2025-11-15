from bedrock_agentcore.runtime import BedrockAgentCoreApp
import logging
from core import process_grocery_list

logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload):
    """Handler for Bedrock agent invocation"""
    logger.info(f"Received payload type: {type(payload)}, value: {payload}")

    # Expect standardized payload format: {"action": "...", "instruction": "...", "customer_id": "..."}
    if not isinstance(payload, dict) or "instruction" not in payload:
        logger.error(
            f"Invalid payload format. Expected dict with 'instruction' field: {payload}"
        )
        return "Error: Invalid payload format"

    action = payload.get("action", "UNKNOWN")
    instruction = payload["instruction"]
    customer_id = payload.get("customer_id", "unknown")

    logger.info(f"Processing action '{action}' for customer {customer_id}")
    logger.info(f"Instruction: {instruction}")

    # Process the instruction through the orchestrator
    result = process_grocery_list([instruction])

    logger.info(f"Processing completed")

    return result


if __name__ == "__main__":
    app.run()
