## Disclaimer: 

This README.md was primarily written by an LLM, based on the Technical Design document I have written. There may be outdated/inaccurate information. 

# Aegis Guardrail

Policy enforcement and observability middleware for autonomous agents and IoT devices.

## Overview

The Aegis Guardrail acts as a centralized checkpoint, intercepting every intended action from an agent or its controller, evaluating it against a set of declarative policies, and then allowing, denying, or escalating the action. By decoupling policy from execution, Aegis provides a scalable and extensible framework for trust and safety across any autonomous platform.

## Features

- **Real-time Policy Evaluation**: Low-latency evaluation of actions against configurable policies
- **Declarative Policy Language**: Human-readable YAML-based policy definitions
- **Flexible Conditions**: Support for various operators (eq, gt, lt, regex, etc.)
- **Webhook Escalations**: Automatic notifications for policy violations
- **Comprehensive Logging**: Structured audit trails for all decisions
- **Redis-backed Storage**: High-performance policy storage with caching
- **RESTful API**: Simple HTTP API for integration
- **Admin Interface**: Policy management via admin API endpoints

## Quick Start

### Using Docker Compose (Recommended)

1. **Start the services:**
   ```bash
   docker-compose up -d
   ```

2. **Load sample policies:**
   ```bash
   # Create policies using the admin API
   curl -X POST http://localhost:8000/admin/policies \
     -H "Content-Type: application/json" \
     -d @sample_policies/thermostat_nursery.yaml
   ```

3. **Test the service:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/evaluate \
     -H "Content-Type: application/json" \
     -d '{
       "request_id": "test-123",
       "agent": {
         "type": "thermostat",
         "id": "thermo-nursery-1",
         "ip_address": "192.168.1.55"
       },
       "action": {
         "name": "set_temperature",
         "parameters": {
           "temperature_celsius": 25
         }
       },
       "context": {
         "environment": {
           "time_of_day_utc": "2025-09-26T23:00:00Z",
           "location": "nursery",
           "is_occupied": false
         },
         "originator": {
           "type": "user",
           "id": "user-jane-doe"
         }
       }
     }'
   ```

### Manual Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start Redis:**
   ```bash
   redis-server
   ```

3. **Run the service:**
   ```bash
   python -m aegis.main
   ```

## API Reference

### Evaluate Action

**Endpoint:** `POST /api/v1/evaluate`

Evaluate an action against configured policies.

**Request Body:**
```json
{
  "request_id": "uuid-1234-abcd-5678",
  "agent": {
    "type": "thermostat",
    "id": "thermo-nursery-1",
    "ip_address": "192.168.1.55"
  },
  "action": {
    "name": "set_temperature",
    "parameters": {
      "temperature_celsius": 25,
      "mode": "heat"
    }
  },
  "context": {
    "environment": {
      "time_of_day_utc": "2025-09-26T23:00:00Z",
      "location": "nursery",
      "is_occupied": true
    },
    "originator": {
      "type": "user",
      "id": "user-jane-doe"
    }
  }
}
```

**Response:**
```json
{
  "request_id": "uuid-1234-abcd-5678",
  "decision": "deny",
  "reason": "Attempted to set nursery temperature above 24°C.",
  "matched_policy": "thermostat-nursery-safety",
  "matched_rule": "temp-too-high",
  "timestamp_utc": "2025-09-26T18:05:12Z",
  "latency_ms": 15
}
```

### Policy Management

**Create Policy:** `POST /admin/policies`
**List Policies:** `GET /admin/policies`
**Get Policy:** `GET /admin/policies/{name}`
**Update Policy:** `PUT /admin/policies/{name}`
**Delete Policy:** `DELETE /admin/policies/{name}`

## Policy Schema

Policies are defined in YAML format:

```yaml
apiVersion: aegis.io/v1
kind: Policy
metadata:
  name: thermostat-nursery-safety
  description: "Prevents the nursery thermostat from being set too high or low."
spec:
  - rule:
      name: temp-too-high
      selector:
        agent_type: "thermostat"
        agent_id: "thermo-nursery-1"
        action_name: "set_temperature"
      conditions:
        - context_field: "action.parameters.temperature_celsius"
          operator: "gt"
          value: 24
      result:
        action: "deny"
        message: "Attempted to set nursery temperature above 24°C."
        on_match:
          escalate:
            webhook_url: "https://notify.example.com/ops-alerts"
            severity: "critical"
```

### Supported Operators

- `eq`, `neq`: Equality operators
- `gt`, `lt`, `gte`, `lte`: Comparison operators
- `in`, `not_in`: List membership operators
- `contains`, `not_contains`: String containment operators
- `regex`: Regular expression matching

### Selectors

- `agent_type`: Type of agent (e.g., "thermostat", "security.camera")
- `agent_id`: Specific agent instance (supports wildcards, e.g., "cam-*")
- `action_name`: Name of the action being performed

## Configuration

Configure the service using environment variables:

- `REDIS_HOST`: Redis hostname (default: localhost)
- `REDIS_PORT`: Redis port (default: 6379)
- `LOG_LEVEL`: Logging level (default: INFO)
- `DEFAULT_DECISION`: Default decision when no policies match (default: allow)
- `VALID_API_KEYS`: Comma-separated list of valid API keys for authentication

### Authentication

The service supports API key authentication for the evaluation endpoint:

```bash
# Set valid API keys (comma-separated)
export VALID_API_KEYS="your-api-key-1,your-api-key-2"

# Use API key in requests
curl -X POST http://localhost:8000/api/v1/evaluate \
  -H "X-API-Key: your-api-key-1" \
  -H "Content-Type: application/json" \
  -d @request.json
```

If no API keys are configured, authentication is disabled (development mode).

## Development

### Running Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run all tests
pytest tests/
```

### Code Quality

```bash
# Format code
black aegis/
isort aegis/

# Lint code
flake8 aegis/
```

## Architecture

The service consists of several key components:

- **Policy Engine**: Evaluates requests against policies
- **Policy Store**: Redis-backed storage with caching
- **Escalation Manager**: Handles webhook notifications
- **Monitoring Service**: Structured logging and metrics
- **REST API**: HTTP interface for clients and administrators

## Security

- API key authentication for evaluation endpoint
- HMAC-signed webhook payloads
- Rate limiting support
- Security headers in responses
- Input validation and sanitization

## License

This project is licensed under the MIT License - see the LICENSE file for details.
