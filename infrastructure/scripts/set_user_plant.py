#!/usr/bin/env python3
"""Set the custom:plant attribute on a Cognito user.

Usage:
    python3 set_user_plant.py --email user@example.com --plant Florida
    python3 set_user_plant.py --email user@example.com --plant Ohio
"""

import argparse
import boto3

USER_POOL_ID = "us-east-1_FyjcuqH7U"
REGION = "us-east-1"
VALID_PLANTS = ("Florida", "Ohio")


def main() -> None:
    parser = argparse.ArgumentParser(description="Set plant attribute on Cognito user")
    parser.add_argument("--email", required=True, help="User email address")
    parser.add_argument("--plant", required=True, choices=VALID_PLANTS, help="Plant assignment")
    parser.add_argument("--user-pool-id", default=USER_POOL_ID, help="Cognito User Pool ID")
    args = parser.parse_args()

    client = boto3.client("cognito-idp", region_name=REGION)
    client.admin_update_user_attributes(
        UserPoolId=args.user_pool_id,
        Username=args.email,
        UserAttributes=[{"Name": "custom:plant", "Value": args.plant}],
    )
    print(f"Set custom:plant={args.plant} for {args.email}")


if __name__ == "__main__":
    main()
