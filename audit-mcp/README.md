# Audit MCP Server

> **⚠️ Note:** This is a demo/sample component, not intended for production use without security review.

MCP server providing audit trail read/write for DisruptionAI.

## Tools

| Tool | Description |
|------|-------------|
| `write_audit_entry` | Write a decision or action to the audit trail |
| `get_audit_trail` | Read audit entries with optional agent and time filters |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run

```bash
audit-mcp-server
```

## Test

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

## Configuration

| Env Variable | Default | Description |
|-------------|---------|-------------|
| `AWS_REGION` | us-east-1 | AWS region |
| `DYNAMODB_TABLE_AUDIT` | disruptionai-audit | Audit table name |
| `LOG_LEVEL` | INFO | Logging level |
