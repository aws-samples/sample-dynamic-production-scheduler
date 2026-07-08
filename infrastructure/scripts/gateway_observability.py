"""Enable CloudWatch logging for AgentCore Gateway.

Based on the official AWS sample:
https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/02-use-cases/device-management-agent

Creates a CloudWatch vended-logs log group and delivery destination
for the gateway (SECURITY-14 compliant: 90-day retention).

Usage:
    python3 infrastructure/scripts/gateway_observability.py \
        --gateway-id <gateway-id> \
        --gateway-arn <gateway-arn>
"""
import argparse
import logging
import sys

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

REGION = "us-east-1"
RETENTION_DAYS = 90


def enable_gateway_logging(gateway_id: str, gateway_arn: str) -> None:
    """Create CloudWatch vended-logs log group and delivery destination.

    Args:
        gateway_id: AgentCore Gateway ID.
        gateway_arn: AgentCore Gateway ARN.
    """
    logs_client = boto3.client("logs", region_name=REGION)

    # Resolve AWS account ID for ARN construction
    try:
        sts_client = boto3.client("sts", region_name=REGION)
        account_id = sts_client.get_caller_identity()["Account"]
        logger.info("AWS Account ID: %s", account_id)
    except ClientError as exc:
        logger.error("Failed to get AWS account ID: %s", exc)
        sys.exit(1)

    # Step 1: Create vended-logs log group
    log_group_name = f"/aws/vendedlogs/bedrock-agentcore/{gateway_id}"
    logger.info("Creating CloudWatch log group: %s", log_group_name)
    try:
        logs_client.create_log_group(logGroupName=log_group_name)
        logger.info("Log group created.")
    except logs_client.exceptions.ResourceAlreadyExistsException:
        logger.info("Log group already exists — skipping creation.")
    except ClientError as exc:
        logger.error("Failed to create log group: %s", exc)
        sys.exit(1)

    # Step 2: Set retention policy (SECURITY-14: 90 days minimum)
    logger.info("Setting retention to %d days ...", RETENTION_DAYS)
    try:
        logs_client.put_retention_policy(
            logGroupName=log_group_name,
            retentionInDays=RETENTION_DAYS,
        )
        logger.info("Retention policy set.")
    except ClientError as exc:
        logger.error("Failed to set retention policy: %s", exc)
        sys.exit(1)

    # Step 3: Create delivery destination
    log_group_arn = f"arn:aws:logs:{REGION}:{account_id}:log-group:{log_group_name}"
    destination_name = f"{gateway_id}-logs-destination"
    logger.info("Creating delivery destination: %s", destination_name)
    try:
        logs_client.put_delivery_destination(
            name=destination_name,
            deliveryDestinationType="CWL",
            deliveryDestinationConfiguration={
                "destinationResourceArn": log_group_arn,
            },
        )
        logger.info("Delivery destination created.")
    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        if error_code in ("ConflictException", "ResourceAlreadyExistsException"):
            logger.info("Delivery destination already exists — skipping.")
        else:
            logger.error("Failed to create delivery destination: %s", exc)
            sys.exit(1)

    logger.info("Gateway observability enabled successfully.")
    logger.info("  Log group  : %s", log_group_name)
    logger.info("  Retention  : %d days", RETENTION_DAYS)
    logger.info("  Gateway    : %s", gateway_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Enable CloudWatch logging for AgentCore Gateway."
    )
    parser.add_argument("--gateway-id", required=True, help="AgentCore Gateway ID")
    parser.add_argument("--gateway-arn", required=True, help="AgentCore Gateway ARN")
    args = parser.parse_args()
    enable_gateway_logging(args.gateway_id, args.gateway_arn)
