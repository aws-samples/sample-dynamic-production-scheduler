"""Validate Cognito OAuth2 configuration for agent gateway access.

Agents authenticate to the AgentCore Gateway by obtaining Cognito
client_credentials tokens directly (no AgentCore Identity registration
needed). This script validates the Cognito setup is correct.

Usage:
    python3 infrastructure/scripts/cognito_credentials_provider.py \
        --cognito-token-endpoint <token-endpoint> \
        --cognito-app-client-id <client-id> \
        --cognito-app-client-secret <secret>
"""
import argparse
import logging
import sys

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

RESOURCE_SERVER_ID = "disruptionai-gateway"

# Scopes each agent needs
AGENT_SCOPES: dict[str, list[str]] = {
    "orchestrator": [
        f"{RESOURCE_SERVER_ID}/erp-data",
        f"{RESOURCE_SERVER_ID}/audit",
    ],
    "impact-assessment": [
        f"{RESOURCE_SERVER_ID}/erp-data",
    ],
    "capacity-optimization": [
        f"{RESOURCE_SERVER_ID}/erp-data",
    ],
    "constraint-matching": [
        f"{RESOURCE_SERVER_ID}/erp-data",
    ],
}


def validate_cognito_tokens(
    token_endpoint: str,
    app_client_id: str,
    app_client_secret: str,
) -> dict[str, bool]:
    """Validate that each agent can obtain a Cognito token for its scopes.

    Args:
        token_endpoint: Cognito OAuth2 token endpoint URL.
        app_client_id: Cognito App Client ID.
        app_client_secret: Cognito App Client secret.

    Returns:
        Mapping of agent name to validation result (True/False).
    """
    results: dict[str, bool] = {}

    for agent_name, scopes in AGENT_SCOPES.items():
        scope_str = " ".join(scopes)
        logger.info(
            "Validating token for agent '%s' (scope_count: %d) ...",
            agent_name, len(scopes),
        )

        try:
            resp = requests.post(
                token_endpoint,
                data={
                    "grant_type": "client_credentials",
                    "client_id": app_client_id,
                    "client_secret": app_client_secret,
                    "scope": scope_str,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10,
            )

            if resp.status_code == 200:
                token_data = resp.json()
                access_token = token_data.get("access_token", "")
                expires_in = token_data.get("expires_in", 0)
                logger.info(
                    "  OK: token obtained (expires_in=%ds, token_len=%d)",
                    expires_in, len(access_token),
                )
                results[agent_name] = True
            else:
                logger.error(
                    "  FAILED: HTTP %d — %s", resp.status_code, resp.text[:200],
                )
                results[agent_name] = False
        except Exception as exc:
            logger.error("  FAILED: %s", exc)
            results[agent_name] = False

    # Summary
    logger.info("--- Validation Summary ---")
    all_ok = True
    for agent_name, ok in results.items():
        status = "PASS" if ok else "FAIL"
        logger.info("  %-25s %s", agent_name, status)
        if not ok:
            all_ok = False

    if not all_ok:
        logger.error("Some agents failed token validation.")
        sys.exit(1)

    logger.info("All agents validated successfully.")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Validate Cognito OAuth2 tokens for agent gateway access."
    )
    parser.add_argument(
        "--cognito-token-endpoint",
        required=True,
        help="Cognito OAuth2 token endpoint URL",
    )
    parser.add_argument(
        "--cognito-app-client-id",
        required=True,
        help="Cognito App Client ID",
    )
    parser.add_argument(
        "--cognito-app-client-secret",
        required=True,
        help="Cognito App Client secret for client_credentials grant",
    )
    args = parser.parse_args()
    validate_cognito_tokens(
        args.cognito_token_endpoint,
        args.cognito_app_client_id,
        args.cognito_app_client_secret,
    )
