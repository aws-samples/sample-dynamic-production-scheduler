#!/usr/bin/env python3
"""Update AgentCore Runtime environment variables for gateway migration.

Adds Cognito OAuth2 + Gateway env vars to all 4 agents while preserving
existing env vars (e.g., BEDROCK_AGENTCORE_MEMORY_ID).

Uses bedrock-agentcore-control client's update_agent_runtime API.
"""

import boto3
import json
import os
import time

REGION = "us-east-1"

# Gateway env vars to add to all 4 agents
GATEWAY_ENV_VARS = {
    "GATEWAY_URL": "https://disruptionai-mcp-gateway-p9qpkebcdw.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp",
    "COGNITO_TOKEN_ENDPOINT": os.environ.get("COGNITO_TOKEN_ENDPOINT", "REPLACE_WITH_COGNITO_TOKEN_URL"),
    "COGNITO_CLIENT_ID": os.environ.get("COGNITO_CLIENT_ID", "REPLACE_WITH_CLIENT_ID"),
    "COGNITO_CLIENT_SECRET": os.environ.get("COGNITO_CLIENT_SECRET", "REPLACE_WITH_CLIENT_SECRET"),
    "ERP_DATA_SCOPE": "disruptionai-gateway/erp-data",
    "AUDIT_SCOPE": "disruptionai-gateway/audit",
}

# Agent runtime IDs
AGENTS = {
    "orchestrator_agent": "orchestrator_agent-1YfV9m46l5",
    "impact_assessment_agent": "impact_assessment_agent-FNJvbQBqOl",
    "capacity_optimization_agent": "capacity_optimization_agent-hdKAx3DZJX",
    "constraint_matching_agent": "constraint_matching_agent-EuLExyBsv5",
}

# AgentCore Memory IDs (per-agent)
MEMORY_IDS = {
    "orchestrator_agent": "orchestrator_agent_mem-tPItRWG4wX",
    "impact_assessment_agent": "impact_assessment_agent_mem-AShWmxAupm",
    "capacity_optimization_agent": "capacity_optimization_agent_mem-UzPD62AR1G",
    "constraint_matching_agent": "constraint_matching_agent_mem-KgRANKE4k3",
}


def main():
    client = boto3.client("bedrock-agentcore-control", region_name=REGION)

    for agent_name, runtime_id in AGENTS.items():
        print(f"\n{'='*60}")
        print(f"Updating: {agent_name} ({runtime_id})")
        print(f"{'='*60}")

        # Get current runtime to preserve existing env vars
        current = client.get_agent_runtime(agentRuntimeId=runtime_id)
        existing_env = current.get("environmentVariables", {})
        print(f"  Existing env vars: {list(existing_env.keys())}")

        # Merge: existing + new gateway vars + memory ID
        agent_memory_id = MEMORY_IDS.get(agent_name, "")
        merged_env = {**existing_env, **GATEWAY_ENV_VARS}
        if agent_memory_id:
            merged_env["AGENTCORE_MEMORY_ID"] = agent_memory_id
        print(f"  Merged env vars:   {list(merged_env.keys())}")

        # Pass through required fields from existing runtime
        artifact = current.get("agentRuntimeArtifact", {})
        role_arn = current.get("roleArn", "")
        network_config = current.get("networkConfiguration", {})

        # Clean artifact — remove None values that cause validation errors
        if "containerConfiguration" in artifact and artifact["containerConfiguration"] is None:
            del artifact["containerConfiguration"]
        if "codeConfiguration" in artifact:
            code_cfg = artifact["codeConfiguration"]
            if "code" in code_cfg:
                code_obj = code_cfg["code"]
                if "s3" in code_obj:
                    s3 = code_obj["s3"]
                    if s3.get("versionId") is None:
                        s3.pop("versionId", None)

        # Update runtime with merged env vars + required fields
        response = client.update_agent_runtime(
            agentRuntimeId=runtime_id,
            agentRuntimeArtifact=artifact,
            roleArn=role_arn,
            networkConfiguration=network_config,
            environmentVariables=merged_env,
        )

        status = response.get("status", "UNKNOWN")
        version = response.get("agentRuntimeVersion", "?")
        print(f"  Status: {status}, Version: {version}")

    # Wait for all agents to reach READY
    print(f"\n{'='*60}")
    print("Waiting for all agents to reach READY status...")
    print(f"{'='*60}")

    max_wait = 300  # 5 minutes
    poll_interval = 10
    elapsed = 0

    while elapsed < max_wait:
        all_ready = True
        for agent_name, runtime_id in AGENTS.items():
            rt = client.get_agent_runtime(agentRuntimeId=runtime_id)
            st = rt.get("status", "UNKNOWN")
            if st != "READY":
                all_ready = False
                print(f"  {agent_name}: {st}")

        if all_ready:
            print("\nAll 4 agents are READY.")
            break

        time.sleep(poll_interval)
        elapsed += poll_interval
        print(f"  ... waiting ({elapsed}s)")
    else:
        print(f"\nTIMEOUT after {max_wait}s. Check agent status manually.")
        return

    # Verify env vars were set
    print(f"\n{'='*60}")
    print("Verification — checking env vars on all agents")
    print(f"{'='*60}")

    for agent_name, runtime_id in AGENTS.items():
        rt = client.get_agent_runtime(agentRuntimeId=runtime_id)
        env = rt.get("environmentVariables", {})
        has_gateway = "GATEWAY_URL" in env
        has_cognito = "COGNITO_CLIENT_ID" in env
        has_memory = any("MEMORY" in k for k in env)
        print(f"  {agent_name}: gateway={has_gateway}, cognito={has_cognito}, memory={has_memory}")
        if not has_gateway or not has_cognito:
            print(f"    WARNING: Missing env vars! Got: {list(env.keys())}")

    print("\nDone.")


if __name__ == "__main__":
    main()
