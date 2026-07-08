#!/usr/bin/env bash
set -euo pipefail

# Update the frontend runtime config.json in S3 and invalidate CloudFront cache.
#
# Usage:
#   ./update-frontend-config.sh [WEBSOCKET_API_URL]
#
# If WEBSOCKET_API_URL is omitted, the script reads it from CloudFormation exports.

WEBSOCKET_API_URL="${1:-}"

# Resolve from CloudFormation exports if not provided
if [[ -z "$WEBSOCKET_API_URL" ]]; then
  echo "No WebSocket URL provided — reading from CloudFormation exports..."
  WEBSOCKET_API_URL=$(aws cloudformation list-exports \
    --query "Exports[?Name=='disruptionai-websocket-api-url'].Value" \
    --output text)
  if [[ -z "$WEBSOCKET_API_URL" || "$WEBSOCKET_API_URL" == "None" ]]; then
    echo "ERROR: Could not resolve WebSocket API URL from CloudFormation exports." >&2
    exit 1
  fi
fi

# Resolve S3 bucket and CloudFront distribution ID from CloudFormation exports
BUCKET=$(aws cloudformation list-exports \
  --query "Exports[?Name=='disruptionai-frontend-bucket'].Value" \
  --output text)
DISTRIBUTION_ID=$(aws cloudformation list-exports \
  --query "Exports[?Name=='disruptionai-distribution-id'].Value" \
  --output text)

if [[ -z "$BUCKET" || "$BUCKET" == "None" ]]; then
  echo "ERROR: Could not resolve frontend S3 bucket from CloudFormation exports." >&2
  exit 1
fi

if [[ -z "$DISTRIBUTION_ID" || "$DISTRIBUTION_ID" == "None" ]]; then
  echo "ERROR: Could not resolve CloudFront distribution ID from CloudFormation exports." >&2
  exit 1
fi

echo "WebSocket URL : $WEBSOCKET_API_URL"
echo "S3 Bucket     : $BUCKET"
echo "Distribution  : $DISTRIBUTION_ID"

# Generate config.json
CONFIG_FILE=$(mktemp)
cat > "$CONFIG_FILE" <<EOF
{
  "VITE_WS_URL": "$WEBSOCKET_API_URL"
}
EOF

# Upload to S3
echo "Uploading config.json to s3://$BUCKET/config.json ..."
aws s3 cp "$CONFIG_FILE" "s3://$BUCKET/config.json" \
  --content-type "application/json" \
  --cache-control "no-cache, no-store, must-revalidate"

rm -f "$CONFIG_FILE"

# Invalidate CloudFront cache for /config.json
echo "Invalidating CloudFront cache for /config.json ..."
aws cloudfront create-invalidation \
  --distribution-id "$DISTRIBUTION_ID" \
  --paths "/config.json" \
  --output text

echo "Done."
