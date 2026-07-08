# Performance Test Instructions — DisruptionAI

## Purpose

Validate system performance under expected load to ensure response times and throughput meet NFR requirements.

## Performance Requirements (from NFR Design)

| Metric | Target | Source |
|--------|--------|--------|
| MCP tool response time | < 500ms (p95) | Units 1, 3 |
| Agent round-trip (single agent) | < 30s | Units 4, 5, 6 |
| Full workflow (2 rounds) | < 5 min | Unit 7 |
| WebSocket first-token latency | < 2s | Unit 8 |
| DynamoDB read latency | < 10ms (p99) | Unit 9 |
| Concurrent sessions | 10 simultaneous | Unit 7 |

## Test 1: MCP Tool Latency

**Tool**: Python script with boto3 timer

```bash
# Run from within activated venv
python -c "
import time, boto3
ddb = boto3.resource('dynamodb')
table = ddb.Table('disruptionai-orders')

times = []
for _ in range(100):
    start = time.perf_counter()
    table.scan(Limit=50)
    times.append((time.perf_counter() - start) * 1000)

times.sort()
print(f'p50: {times[49]:.1f}ms')
print(f'p95: {times[94]:.1f}ms')
print(f'p99: {times[98]:.1f}ms')
"
```

**Pass criteria**: p95 < 500ms for scan operations

## Test 2: Agent Response Time

**Tool**: Direct agent invocation with timer

```bash
python -c "
import time
from impact_assessment_agent.agent import create_agent

agent = create_agent()
start = time.perf_counter()
result = agent('Assess impact of Florida plant shutdown')
elapsed = time.perf_counter() - start
print(f'Impact Assessment: {elapsed:.1f}s')
assert elapsed < 30, f'Exceeded 30s target: {elapsed:.1f}s'
print('PASS')
"
```

Repeat for capacity-optimization-agent and constraint-matching-agent.

**Pass criteria**: Each agent completes within 30s

## Test 3: Full Workflow Duration

**Tool**: Orchestrator invocation with timer

```bash
python -c "
import time
from orchestrator_agent.agent import create_agent

agent = create_agent()
start = time.perf_counter()
# Round 1
result = agent('Florida plant shutdown due to hurricane, 2-week duration')
r1 = time.perf_counter() - start
print(f'Round 1: {r1:.1f}s')

# Round 2
start2 = time.perf_counter()
result = agent('Approve all critical order transfers')
r2 = time.perf_counter() - start2
print(f'Round 2: {r2:.1f}s')
print(f'Total: {r1 + r2:.1f}s')
assert (r1 + r2) < 300, f'Exceeded 5min target: {r1+r2:.1f}s'
print('PASS')
"
```

**Pass criteria**: Total workflow < 5 minutes (300s)

## Test 4: WebSocket First-Token Latency

**Tool**: Browser DevTools or wscat

```bash
# Install wscat if needed: npm install -g wscat
wscat -c "wss://<websocket-api-url>/prod"

# Once connected, send:
{"action": "sendMessage", "data": "Florida plant shutdown"}

# Measure time from send to first response frame
```

**Pass criteria**: First token received within 2s of message send

## Test 5: Concurrent Session Load

**Tool**: Python concurrent script

```bash
python -c "
import concurrent.futures, time, json, websocket

URL = 'wss://<websocket-api-url>/prod'

def run_session(session_num):
    ws = websocket.create_connection(URL)
    ws.send(json.dumps({'action':'sendMessage','data':f'Test session {session_num}'}))
    result = ws.recv()
    ws.close()
    return session_num

start = time.perf_counter()
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
    futures = [pool.submit(run_session, i) for i in range(10)]
    results = [f.result(timeout=60) for f in futures]
elapsed = time.perf_counter() - start
print(f'10 concurrent sessions: {elapsed:.1f}s')
print(f'All completed: {len(results)} / 10')
"
```

**Pass criteria**: All 10 sessions connect and receive responses

## Test 6: DynamoDB Throttle Check

After running load tests, check CloudWatch:

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=disruptionai-orders \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

**Pass criteria**: ThrottledRequests = 0 (on-demand billing should handle load)

## Results Summary Template

After running all performance tests, record results:

```
| Test | Target | Actual | Status |
|------|--------|--------|--------|
| MCP tool p95 | < 500ms | ___ms | PASS/FAIL |
| Agent round-trip | < 30s | ___s | PASS/FAIL |
| Full workflow | < 5 min | ___s | PASS/FAIL |
| WebSocket first-token | < 2s | ___s | PASS/FAIL |
| Concurrent sessions | 10 | ___ | PASS/FAIL |
| DynamoDB throttles | 0 | ___ | PASS/FAIL |
```

## Performance Optimization

If any test fails:

1. **MCP tool slow**: Check DynamoDB table metrics, consider adding GSIs for frequent queries
2. **Agent slow**: Check Bedrock model latency in CloudWatch, reduce max_tokens if possible
3. **Workflow slow**: Profile sub-agent invocations, check AgentCore cold start times
4. **WebSocket slow**: Check Lambda cold start, consider provisioned concurrency
5. **Throttled**: Verify on-demand billing mode, check for hot partitions
