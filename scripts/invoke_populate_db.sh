#!/bin/bash

# Script to invoke the populate database Lambda function
# This runs the Lambda to populate the PostgreSQL database with product data

set -e

REGION="ap-southeast-2"
STACK_NAME="OrderAssistantStack"

echo "🔍 Getting Lambda function name from CloudFormation stack..."
LAMBDA_NAME=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query "Stacks[0].Outputs[?OutputKey=='PopulateDBLambdaName'].OutputValue" \
    --output text)

if [ -z "$LAMBDA_NAME" ]; then
    echo "❌ Error: Could not find PopulateDBLambdaName in stack outputs"
    echo "   Make sure the stack is deployed with the populate DB Lambda"
    exit 1
fi

echo "✓ Found Lambda function: $LAMBDA_NAME"
echo ""

# Check if we should clear existing data
CLEAR_EXISTING="false"
if [ "$1" == "--clear" ]; then
    CLEAR_EXISTING="true"
    echo "⚠️  Will clear existing data before inserting"
fi

echo "🚀 Invoking Lambda function to populate database..."
echo ""

# Invoke the Lambda function
RESPONSE=$(aws lambda invoke \
    --function-name $LAMBDA_NAME \
    --region $REGION \
    --payload "{\"clear_existing\": $CLEAR_EXISTING}" \
    --cli-binary-format raw-in-base64-out \
    /tmp/populate_db_response.json)

echo "Response metadata:"
echo "$RESPONSE" | jq '.'
echo ""

echo "Lambda function output:"
cat /tmp/populate_db_response.json | jq '.'
echo ""

# Check if the invocation was successful
STATUS_CODE=$(cat /tmp/populate_db_response.json | jq -r '.statusCode // 0')

if [ "$STATUS_CODE" -eq 200 ]; then
    echo "✅ Database populated successfully!"

    # Show summary
    BODY=$(cat /tmp/populate_db_response.json | jq -r '.body')
    echo ""
    echo "Summary:"
    echo "$BODY" | jq '.'
else
    echo "❌ Error populating database"
    cat /tmp/populate_db_response.json | jq '.'
    exit 1
fi

# Clean up
rm /tmp/populate_db_response.json
