#!/usr/bin/env python3
"""Inject session_state handler into the deployed REST proxy Lambda."""
import zipfile, io, boto3, json, urllib.request
from urllib.parse import urlparse

client = boto3.client("lambda", region_name="us-east-1")
resp = client.get_function(FunctionName="disruptionai-rest-proxy")
code_url = resp["Code"]["Location"]

# Validate URL scheme before opening (B310 remediation)
parsed_url = urlparse(code_url)
if parsed_url.scheme not in ("https",):
    raise ValueError(f"Refusing to open URL with scheme: {parsed_url.scheme}")

with urllib.request.urlopen(code_url) as r:  # noqa: B310 - scheme validated above
    zip_bytes = r.read()

z = zipfile.ZipFile(io.BytesIO(zip_bytes))
code = z.read("index.py").decode()

if "session_state" in code:
    print("session_state handler already exists!")
    exit(0)

handler = '''
    # Session state endpoint — reads workflow-state + tracker from DynamoDB
    if action == "session_state":
        if not session_id:
            return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "sessionId required"})}
        try:
            d = get_ddb()
            ws_table = d.Table("disruptionai-workflow-state")
            ws_resp = ws_table.query(KeyConditionExpression=Key("session_id").eq(session_id))
            ws_items = ws_resp.get("Items", [])
            workflow_state = {}
            for item in ws_items:
                key = item.get("state_key", "")
                data = item.get("data")
                if key and data is not None:
                    workflow_state[key] = data
            tracker = None
            try:
                tracker_t = d.Table("disruptionai-tracker")
                t_resp = tracker_t.get_item(Key={"session_id": session_id})
                tracker = t_resp.get("Item")
            except Exception:
                pass
            result = {"workflowState": workflow_state, "tracker": tracker}
            return {"statusCode": 200, "headers": headers, "body": json.dumps(result, cls=DecimalEncoder)}
        except Exception as e:
            logger.error(f"Session state query failed: {e}", exc_info=True)
            return {"statusCode": 500, "headers": headers, "body": json.dumps({"error": str(e)})}

'''

insertion_point = code.find("    if not user_message:")
if insertion_point == -1:
    print("ERROR: Could not find insertion point")
    exit(1)

new_code = code[:insertion_point] + handler + code[insertion_point:]

buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
    zout.writestr("index.py", new_code)
buf.seek(0)

client.update_function_code(
    FunctionName="disruptionai-rest-proxy",
    ZipFile=buf.read(),
)
print(f"Done. Code: {len(code)} -> {len(new_code)} chars")
