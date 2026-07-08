# NFR Design Patterns — Unit 1: ERP Data MCP Server

## Pattern 1: Resilience — Exponential Backoff Retry

**Applies to**: All DynamoDB operations (REL-01)

**Implementation**:
- Configure boto3 `Config` with built-in retry mode `adaptive`
- Max attempts: 4 (1 initial + 3 retries)
- Backoff: exponential (100ms, 200ms, 400ms)
- Retryable: ThrottlingException, ProvisionedThroughputExceededException, InternalServerError
- Non-retryable: ValidationException, ConditionalCheckFailedException, ResourceNotFoundException

```python
# Pattern: boto3 retry configuration
from botocore.config import Config

dynamodb_config = Config(
    retries={
        "mode": "adaptive",
        "max_attempts": 4
    },
    connect_timeout=5,
    read_timeout=10
)
```

**Circuit Breaker Assessment**: Not needed for MVP. DynamoDB is a managed service with built-in availability. boto3 adaptive retry handles transient failures. Circuit breaker adds complexity without benefit at single-user scale.

---

## Pattern 2: Resilience — Tool Handler Wrapper

**Applies to**: All 10 MCP tool handlers (REL-02, SECURITY-15)

**Implementation**:
- Decorator wraps every tool handler in try/except
- Catches specific exceptions and maps to error codes
- Logs errors with full context server-side
- Returns sanitized error response to caller

```python
# Pattern: tool handler error wrapper
def tool_error_handler(func):
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ValidationError as e:
            logger.warning("Input validation failed", extra={"tool": func.__name__, "error": str(e)})
            return {"error": {"code": "INVALID_INPUT", "message": str(e)}}
        except ConditionalCheckFailedException:
            logger.warning("Status transition rejected", extra={"tool": func.__name__})
            return {"error": {"code": "INVALID_TRANSITION", "message": "Status transition not allowed"}}
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ResourceNotFoundException":
                return {"error": {"code": "NOT_FOUND", "message": "Resource not found"}}
            logger.error("DynamoDB error", extra={"tool": func.__name__, "error": str(e)})
            return {"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}}
        except Exception as e:
            logger.error("Unexpected error", extra={"tool": func.__name__, "error": str(e)}, exc_info=True)
            return {"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}}
    return wrapper
```

---

## Pattern 3: Observability — Structured Logging Middleware

**Applies to**: All tool invocations (OBS-01, OBS-02, SECURITY-03)

**Implementation**:
- JSON-formatted log entries to stdout
- Automatic timing of tool invocations
- Correlation via session_id when available
- Log fields: timestamp, level, tool_name, correlation_id, duration_ms, message

```python
# Pattern: logging configuration
import logging
from pythonjsonlogger import jsonlogger

def configure_logging():
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        rename_fields={"asctime": "timestamp", "levelname": "level"}
    )
    handler.setFormatter(formatter)
    logger = logging.getLogger("erp_data_mcp")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
```

```python
# Pattern: tool invocation logging decorator
import time

def log_tool_invocation(func):
    async def wrapper(*args, **kwargs):
        start = time.monotonic()
        logger.info("Tool invoked", extra={"tool": func.__name__})
        try:
            result = await func(*args, **kwargs)
            duration = (time.monotonic() - start) * 1000
            logger.info("Tool completed", extra={"tool": func.__name__, "duration_ms": round(duration, 2)})
            return result
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            logger.error("Tool failed", extra={"tool": func.__name__, "duration_ms": round(duration, 2), "error": str(e)})
            raise
    return wrapper
```

---

## Pattern 4: Security — Pydantic Input Validation Layer

**Applies to**: All 10 MCP tool inputs (SEC-01, SECURITY-05)

**Implementation**:
- Pydantic models for every tool's input schema
- Validation runs before any DynamoDB operation
- Regex patterns for IDs, enum constraints for categorical fields
- Validation errors return INVALID_INPUT immediately (no retry)

```python
# Pattern: Pydantic input models
from pydantic import BaseModel, Field, field_validator
import re

class GetOrdersInput(BaseModel):
    plant: str = Field(..., pattern="^(Florida|Ohio)$")
    status: str | None = Field(None, pattern="^(Active|Delayed|Transferred|Cancelled)$")

class UpdateOrderPriorityInput(BaseModel):
    order_id: str = Field(..., pattern=r"^PO-\d{4}-\d{3}$")
    priority: str = Field(..., pattern="^(P1|P2|P3)$")

class UpdateRunningTrackerInput(BaseModel):
    session_id: str
    tracker_data: dict

    @field_validator("session_id")
    @classmethod
    def validate_uuid(cls, v):
        uuid_pattern = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
        if not uuid_pattern.match(v):
            raise ValueError("Invalid session ID format")
        return v
```

---

## Pattern 5: Security — Environment-Based Configuration

**Applies to**: All AWS resource references (SEC-03, SECURITY-12)

**Implementation**:
- Table names, region, log level from environment variables
- No hardcoded AWS credentials or resource identifiers
- Pydantic Settings for configuration validation at startup

```python
# Pattern: environment configuration
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    aws_region: str = "us-east-1"
    dynamodb_table_orders: str = "disruptionai-orders"
    dynamodb_table_capacity: str = "disruptionai-capacity"
    dynamodb_table_manpower: str = "disruptionai-manpower"
    dynamodb_table_materials: str = "disruptionai-materials"
    dynamodb_table_customers: str = "disruptionai-customers"
    dynamodb_table_tracker: str = "disruptionai-tracker"
    log_level: str = "INFO"

    class Config:
        env_prefix = ""
```

---

## Pattern 6: Data Access — DynamoDB Client Singleton

**Applies to**: All DynamoDB operations (PERF-01, PERF-03)

**Implementation**:
- Single boto3 DynamoDB resource initialized at startup
- Connection pooling via boto3 default session
- Retry configuration applied at client level
- Table references cached after first access

```python
# Pattern: DynamoDB client singleton
import boto3
from botocore.config import Config

class DynamoDBClient:
    _instance = None

    @classmethod
    def get_instance(cls, settings: Settings) -> "DynamoDBClient":
        if cls._instance is None:
            cls._instance = cls(settings)
        return cls._instance

    def __init__(self, settings: Settings):
        config = Config(
            retries={"mode": "adaptive", "max_attempts": 4},
            connect_timeout=5,
            read_timeout=10,
            region_name=settings.aws_region
        )
        self._resource = boto3.resource("dynamodb", config=config)
        self._tables = {}

    def get_table(self, table_name: str):
        if table_name not in self._tables:
            self._tables[table_name] = self._resource.Table(table_name)
        return self._tables[table_name]
```

---

## Decorator Composition

Tool handlers apply decorators in this order (outermost first):

```
@mcp.tool()              # MCP registration
@log_tool_invocation     # Timing + logging
@tool_error_handler      # Error catching + sanitization
async def get_orders(input: GetOrdersInput):
    # Pydantic validates input automatically
    # DynamoDB client handles retries
    ...
```

This layered approach ensures:
1. MCP framework handles transport
2. Logging captures every invocation with timing
3. Error handler catches all exceptions and returns safe responses
4. Pydantic validates input before business logic executes
5. boto3 handles DynamoDB retries transparently
