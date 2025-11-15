from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_lambda as _lambda,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subs,
    aws_iam as iam,
    aws_dynamodb as dynamodb,
    aws_ssm as ssm,
    Duration,
    CfnOutput,
)
from constructs import Construct
import yaml
import pathlib


class OrderAssistantStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Read agent ARN from bedrock_agentcore.yaml
        agentcore_config_path = (
            pathlib.Path(__file__).parent.parent
            / "agentcore"
            / "runtime"
            / ".bedrock_agentcore.yaml"
        )
        with open(agentcore_config_path, "r") as f:
            agentcore_config = yaml.safe_load(f)

        agent_arn = agentcore_config["agents"]["order_assistant"]["bedrock_agentcore"][
            "agent_arn"
        ]

        # Create IAM role for AgentCore Runtime
        agentcore_execution_role = iam.Role(
            self,
            "AgentCoreExecutionRole",
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            description="Execution role for AgentCore order assistant runtime",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")
            ],
        )

        # Create SSM parameter for agent ARN
        agent_arn_param = ssm.StringParameter(
            self,
            "AgentRuntimeArn",
            parameter_name="/order-assistant/agent-runtime-arn",
            string_value=agent_arn,
            description="AgentCore Runtime ARN for order assistant",
        )

        bucket = s3.Bucket(self, "OrderAssistantBucket")

        catalog_table = dynamodb.Table(
            self,
            "ProductCatalog",
            partition_key=dynamodb.Attribute(
                name="product_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )

        process_order_lambda = _lambda.Function(
            self,
            "ProcessOrder",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda.handler",
            code=_lambda.Code.from_asset("src/process_order"),
            environment={
                "PHONE_NUMBER_ID": "phone-number-id-b71b760ca9774fe9bd465120e4c00b4a",  # Your WhatsApp phone number ID
                "MEDIA_BUCKET_NAME": bucket.bucket_name,
                "AGENT_ARN_PARAM": agent_arn_param.parameter_name,
            },
            timeout=Duration.minutes(15),
        )

        process_order_lambda.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")
        )

        # Grant Lambda permission to read SSM parameter
        agent_arn_param.grant_read(process_order_lambda)

        # Grant Lambda permission to read/write S3 bucket
        bucket.grant_read_write(process_order_lambda)

        # Create SNS topic for WhatsApp messages
        whatsapp_topic = sns.Topic(
            self,
            "WhatsAppMessageTopic",
            display_name="WhatsApp Message Topic",
            topic_name="OrderAssistant-WhatsAppMessages",
        )

        # Subscribe Lambda to SNS topic
        whatsapp_topic.add_subscription(
            sns_subs.LambdaSubscription(process_order_lambda)
        )

        # DynamoDB MCP Server Lambda
        dynamodb_mcp_lambda = _lambda.DockerImageFunction(
            self,
            "DynamoDBMCPServer",
            code=_lambda.DockerImageCode.from_image_asset(
                directory="src/lambda/dynamodb_mcp", file="Dockerfile"
            ),
            timeout=Duration.minutes(5),
            memory_size=512,
            environment={
                "DDB_MCP_READONLY": "true",
                "FASTMCP_LOG_LEVEL": "ERROR",
            },
        )

        dynamodb_mcp_lambda.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AdministratorAccess")
        )

        # Output the Lambda function ARN and name
        CfnOutput(
            self,
            "DynamoDBMCPLambdaArn",
            value=dynamodb_mcp_lambda.function_arn,
            description="DynamoDB MCP Server Lambda Function ARN",
        )
        CfnOutput(
            self,
            "DynamoDBMCPLambdaName",
            value=dynamodb_mcp_lambda.function_name,
            description="DynamoDB MCP Server Lambda Function Name",
        )
        CfnOutput(
            self,
            "ProductCatalogTableName",
            value=catalog_table.table_name,
            description="Product Catalog DynamoDB Table Name",
        )
        CfnOutput(
            self,
            "OrderAssistantBucketName",
            value=bucket.bucket_name,
            description="S3 Bucket for Order Documents",
        )
        CfnOutput(
            self,
            "AgentCoreExecutionRoleArn",
            value=agentcore_execution_role.role_arn,
            description="AgentCore Runtime Execution Role ARN",
        )
        CfnOutput(
            self,
            "WhatsAppTopicArn",
            value=whatsapp_topic.topic_arn,
            description="SNS Topic ARN for WhatsApp Messages",
        )
