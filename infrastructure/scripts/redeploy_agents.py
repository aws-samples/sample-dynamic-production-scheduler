#!/usr/bin/env python3
"""Redeploy all 4 agents to AgentCore Runtime.

Downloads existing deployment.zip from S3, replaces agent.py with the
updated version (MCP client fix), re-uploads, and triggers update.
"""

import boto3
import json
import os
import shutil
import subprocess
import tempfile
import time
import zipfile

REGION = "us-east-1"
BUCKET = f"bedrock-agentcore-codebuild-sources-{os.environ.get('ACCOUNT_ID', 'REPLACE_ACCOUNT_ID')}-us-east-1"
WORKSPACE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

AGENTS = {
    "orchestrator_agent": {
        "runtime_id": "orchestrator_agent-1YfV9m46l5",
        "s3_prefix": "orchestrator_agent/deployment.zip",
        "files": [
            ("orchestrator-agent/src/orchestrator_agent/agent.py", "src/orchestrator_agent/agent.py"),
            ("orchestrator-agent/src/orchestrator_agent/config.py", "src/orchestrator_agent/config.py"),
            ("orchestrator-agent/src/orchestrator_agent/agentcore_server.py", "src/orchestrator_agent/agentcore_server.py"),
            ("orchestrator-agent/src/orchestrator_agent/prompts/system_prompt.py", "src/orchestrator_agent/prompts/system_prompt.py"),
            ("orchestrator-agent/src/orchestrator_agent/models/schemas.py", "src/orchestrator_agent/models/schemas.py"),
            ("orchestrator-agent/src/orchestrator_agent/workflow_state.py", "src/orchestrator_agent/workflow_state.py"),
        ],
    },
    "impact_assessment_agent": {
        "runtime_id": "impact_assessment_agent-FNJvbQBqOl",
        "s3_prefix": "impact_assessment_agent/deployment.zip",
        "files": [
            ("impact-assessment-agent/src/impact_assessment_agent/agent.py", "src/impact_assessment_agent/agent.py"),
            ("impact-assessment-agent/src/impact_assessment_agent/config.py", "src/impact_assessment_agent/config.py"),
            ("impact-assessment-agent/src/impact_assessment_agent/agentcore_server.py", "src/impact_assessment_agent/agentcore_server.py"),
            ("impact-assessment-agent/src/impact_assessment_agent/models/schemas.py", "src/impact_assessment_agent/models/schemas.py"),
            ("impact-assessment-agent/src/impact_assessment_agent/prompts/system_prompt.py", "src/impact_assessment_agent/prompts/system_prompt.py"),
            ("impact-assessment-agent/src/impact_assessment_agent/scoring.py", "src/impact_assessment_agent/scoring.py"),
        ],
    },
    "capacity_optimization_agent": {
        "runtime_id": "capacity_optimization_agent-hdKAx3DZJX",
        "s3_prefix": "capacity_optimization_agent/deployment.zip",
        "files": [
            ("capacity-optimization-agent/src/capacity_optimization_agent/agent.py", "src/capacity_optimization_agent/agent.py"),
            ("capacity-optimization-agent/src/capacity_optimization_agent/config.py", "src/capacity_optimization_agent/config.py"),
            ("capacity-optimization-agent/src/capacity_optimization_agent/agentcore_server.py", "src/capacity_optimization_agent/agentcore_server.py"),
            ("capacity-optimization-agent/src/capacity_optimization_agent/models/schemas.py", "src/capacity_optimization_agent/models/schemas.py"),
            ("capacity-optimization-agent/src/capacity_optimization_agent/prompts/system_prompt.py", "src/capacity_optimization_agent/prompts/system_prompt.py"),
        ],
    },
    "constraint_matching_agent": {
        "runtime_id": "constraint_matching_agent-EuLExyBsv5",
        "s3_prefix": "constraint_matching_agent/deployment.zip",
        "files": [
            ("constraint-matching-agent/src/constraint_matching_agent/agent.py", "src/constraint_matching_agent/agent.py"),
            ("constraint-matching-agent/src/constraint_matching_agent/config.py", "src/constraint_matching_agent/config.py"),
            ("constraint-matching-agent/src/constraint_matching_agent/agentcore_server.py", "src/constraint_matching_agent/agentcore_server.py"),
            ("constraint-matching-agent/src/constraint_matching_agent/models/schemas.py", "src/constraint_matching_agent/models/schemas.py"),
            ("constraint-matching-agent/src/constraint_matching_agent/prompts/system_prompt.py", "src/constraint_matching_agent/prompts/system_prompt.py"),
            ("constraint-matching-agent/src/constraint_matching_agent/tracker.py", "src/constraint_matching_agent/tracker.py"),
            ("constraint-matching-agent/src/constraint_matching_agent/funnel.py", "src/constraint_matching_agent/funnel.py"),
        ],
    },
}


def update_zip_multi(zip_path: str, replacements: dict[str, bytes]) -> str:
    """Replace or add files inside a zip archive.

    Args:
        zip_path: Path to the zip file.
        replacements: Dict of {zip_internal_path: new_content_bytes}.

    Returns path to the updated zip file.
    """
    new_zip_path = zip_path + ".new"
    replaced = set()
    with zipfile.ZipFile(zip_path, "r") as zin:
        with zipfile.ZipFile(new_zip_path, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                if item.filename in replacements:
                    zout.writestr(item, replacements[item.filename])
                    replaced.add(item.filename)
                else:
                    zout.writestr(item, zin.read(item.filename))
            # Add any new files not already in the zip
            for path, content in replacements.items():
                if path not in replaced:
                    zout.writestr(path, content)
    os.replace(new_zip_path, zip_path)
    return zip_path


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="Redeploy only this agent (e.g. orchestrator_agent)")
    args = parser.parse_args()

    s3 = boto3.client("s3", region_name=REGION)
    control = boto3.client("bedrock-agentcore-control", region_name=REGION)

    agents_to_deploy = AGENTS
    if args.only:
        if args.only not in AGENTS:
            print(f"Unknown agent: {args.only}. Available: {list(AGENTS.keys())}")
            return
        agents_to_deploy = {args.only: AGENTS[args.only]}

    for agent_name, cfg in agents_to_deploy.items():
        print(f"\n{'='*60}")
        print(f"Redeploying: {agent_name}")
        print(f"{'='*60}")

        # 1. Download existing deployment.zip
        local_zip = os.path.join(tempfile.gettempdir(), f"{agent_name}_deployment.zip")
        print(f"  Downloading s3://{BUCKET}/{cfg['s3_prefix']}...")
        s3.download_file(BUCKET, cfg["s3_prefix"], local_zip)

        # 2. Read updated files from workspace
        replacements = {}
        for local_rel, zip_internal in cfg["files"]:
            source_path = os.path.join(WORKSPACE, local_rel)
            with open(source_path, "rb") as f:
                content = f.read()
            replacements[zip_internal] = content
            print(f"  {zip_internal}: {len(content)} bytes")

        # 3. Replace files inside the zip
        update_zip_multi(local_zip, replacements)
        zip_size = os.path.getsize(local_zip)
        print(f"  Updated zip: {zip_size} bytes")

        # 4. Upload back to S3
        print(f"  Uploading to s3://{BUCKET}/{cfg['s3_prefix']}...")
        s3.upload_file(local_zip, BUCKET, cfg["s3_prefix"])

        # 5. Trigger update_agent_runtime
        runtime_id = cfg["runtime_id"]
        current = control.get_agent_runtime(agentRuntimeId=runtime_id)
        artifact = current.get("agentRuntimeArtifact", {})
        role_arn = current.get("roleArn", "")
        network_config = current.get("networkConfiguration", {})
        env_vars = current.get("environmentVariables", {})

        # Clean artifact — remove None values
        if "containerConfiguration" in artifact and artifact["containerConfiguration"] is None:
            del artifact["containerConfiguration"]
        if "codeConfiguration" in artifact:
            code_cfg = artifact["codeConfiguration"]
            if "code" in code_cfg and "s3" in code_cfg["code"]:
                s3_cfg = code_cfg["code"]["s3"]
                if s3_cfg.get("versionId") is None:
                    s3_cfg.pop("versionId", None)

        print(f"  Triggering update_agent_runtime for {runtime_id}...")
        response = control.update_agent_runtime(
            agentRuntimeId=runtime_id,
            agentRuntimeArtifact=artifact,
            roleArn=role_arn,
            networkConfiguration=network_config,
            environmentVariables=env_vars,
        )
        status = response.get("status", "UNKNOWN")
        version = response.get("agentRuntimeVersion", "?")
        print(f"  Status: {status}, Version: {version}")

        # Cleanup temp file
        os.remove(local_zip)

    # Wait for all agents to reach READY
    print(f"\n{'='*60}")
    print("Waiting for all agents to reach READY status...")
    print(f"{'='*60}")

    max_wait = 600  # 10 minutes
    poll_interval = 15
    elapsed = 0

    while elapsed < max_wait:
        all_ready = True
        statuses = {}
        for agent_name, cfg in agents_to_deploy.items():
            rt = control.get_agent_runtime(agentRuntimeId=cfg["runtime_id"])
            st = rt.get("status", "UNKNOWN")
            statuses[agent_name] = st
            if st != "READY":
                all_ready = False

        if all_ready:
            print("\nAll 4 agents are READY.")
            break

        not_ready = {k: v for k, v in statuses.items() if v != "READY"}
        print(f"  [{elapsed}s] Not ready: {not_ready}")
        time.sleep(poll_interval)
        elapsed += poll_interval
    else:
        print(f"\nTIMEOUT after {max_wait}s. Current statuses:")
        for agent_name, cfg in agents_to_deploy.items():
            rt = control.get_agent_runtime(agentRuntimeId=cfg["runtime_id"])
            print(f"  {agent_name}: {rt.get('status', 'UNKNOWN')}")
        return

    print("\nRedeployment complete.")


if __name__ == "__main__":
    main()
