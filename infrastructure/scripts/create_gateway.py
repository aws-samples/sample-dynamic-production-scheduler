"""Create AgentCore Gateway with Cognito JWT authorizer.

Based on the official AWS sample:
https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/02-use-cases/device-management-agent

Usage:
    python3 infrastructure/scripts/create_gateway.py \
        --cognito-user-pool-id <pool-id> \
        --cognito-app-client-id <client-id> \
        --role-arn <gateway-management-role-arn>
"""
import argparse
import json
import logging
import sys

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REGION = "us-east-1"
GATEWAY_NAME = "disruptionai-mcp-gateway"
GATEWAY_DESCRIPTION = "DisruptionAI MCP Gateway for ERP Data and Audit tools"
CONFIG_PATH = "infrastructure/scripts/.gateway-config.json"


def create_gateway(user_pool_id: str, app_client_id: str, role_arn: str) -> dict:
    """Create an AgentCore Gateway with Cognito JWT authorizer.

    Args:
        user_pool_id: Cognito User Pool ID.
        app_client_id: Cognito App Client ID used as audience and allowed client.
        role_arn: IAM role ARN with bedrock-agentcore gateway permissions.

    Returns:
        dict with gateway_id, gateway_arn, and endpoint.
    """
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    discovery_url = (
        f"https://cognito-idp.{REGION}.amazonaws.com/{user_pool_id}"
        f"/.well-known/openid-configuration"
    )

    auth_config = {
        "customJWTAuthorizer": {
            "allowedClients": [app_client_id],
            "discoveryUrl": discovery_url,
        }
    }

    logger.info("Creating AgentCore Gateway '%s' ...", GATEWAY_NAME)
    logger.info("  Cognito discovery URL: %s", discovery_url)
    logger.info("  Role ARN: %s", role_arn)

    try:
        response = client.create_gateway(
            name=GATEWAY_NAME,
            roleArn=role_arn,
            protocolType="MCP",
            authorizerType="CUSTOM_JWT",
            authorizerConfiguration=auth_config,
            description=GATEWAY_DESCRIPTION,
        )
    except ClientError as exc:
        logger.error("Failed to create gateway: %s", exc)
        sys.exit(1)

    gateway_id = response.get("gatewayId")
    gateway_arn = response.get("gatewayArn")
    endpoint = (
        f"https://{gateway_id}.gateway.bedrock-agentcore.{REGION}.amazonaws.com/mcp"
    )

    logger.info("Gateway created successfully.")
    logger.info("  Gateway ID  : %s", gateway_id)
    logger.info("  Gateway ARN : %s", gateway_arn)
    logger.info("  Endpoint    : %s", endpoint)

    config = {
        "gateway_id": gateway_id,
        "gateway_arn": gateway_arn,
        "endpoint": endpoint,
        "name": GATEWAY_NAME,
        "region": REGION,
        "cognito_user_pool_id": user_pool_id,
        "cognito_app_client_id": app_client_id,
        "role_arn": role_arn,
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    logger.info("Gateway config saved to %s", CONFIG_PATH)

    return {"gateway_id": gateway_id, "gateway_arn": gateway_arn, "endpoint": endpoint}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Create AgentCore Gateway with Cognito JWT authorizer."
    )
    parser.add_argument(
        "--cognito-user-pool-id",
        required=True,
        help="Cognito User Pool ID (e.g. us-east-1_AbCdEfGhI)",
    )
    parser.add_argument(
        "--cognito-app-client-id",
        required=True,
        help="Cognito App Client ID used as JWT audience",
    )
    parser.add_argument(
        "--role-arn",
        required=True,
        help="IAM role ARN with bedrock-agentcore gateway permissions",
    )
    args = parser.parse_args()
    create_gateway(args.cognito_user_pool_id, args.cognito_app_client_id, args.role_arn)
