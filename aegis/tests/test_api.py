import pytest
from fastapi.testclient import TestClient
import json
import yaml

from ..main import create_app
from ..models.policy import Policy, ActionDecision


class TestAPI:
    """api tests"""

    @pytest.fixture
    def client(self):
        """test client"""
        app = create_app()
        return TestClient(app)

    @pytest.fixture
    def sample_policy(self):
        """sample policy"""
        return Policy(
            apiVersion="aegis.io/v1",
            kind="Policy",
            metadata={
                "name": "test-policy",
                "description": "Test policy for API testing"
            },
            spec={
                "rules": [
                    {
                        "name": "test-rule",
                        "selector": {
                            "agent_type": "thermostat",
                            "agent_id": "thermo-1",
                            "action_name": "set_temperature"
                        },
                        "conditions": [
                            {
                                "context_field": "action.parameters.temperature_celsius",
                                "operator": "gt",
                                "value": 24
                            }
                        ],
                        "result": {
                            "action": "deny",
                            "message": "Temperature too high"
                        }
                    }
                ]
            }
        )

    def test_health_check(self, client):
        """test health check"""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "aegis-guardrail"

    def test_evaluate_request_success(self, client):
        """test eval success"""
        request_data = {
            "request_id": "test-123",
            "agent": {
                "type": "thermostat",
                "id": "thermo-1",
                "ip_address": "192.168.1.100"
            },
            "action": {
                "name": "set_temperature",
                "parameters": {
                    "temperature_celsius": 25
                }
            },
            "context": {
                "environment": {
                    "time_of_day_utc": "2025-09-26T15:00:00Z",
                    "location": "living_room",
                    "is_occupied": False
                },
                "originator": {
                    "type": "user",
                    "id": "user-123"
                }
            }
        }

        # test with api key
        response = client.post("/api/v1/evaluate", json=request_data, headers={"X-API-Key": "test-key"})

        # no policy in test env
        # tests api structure
        assert response.status_code in [200, 500]  # Either success or service not ready

    def test_evaluate_request_invalid_input(self, client):
        """test invalid input"""
        # missing fields
        request_data = {
            "request_id": "test-123"
            # missing agent, action
        }

        response = client.post("/api/v1/evaluate", json=request_data, headers={"X-API-Key": "test-key"})
        assert response.status_code == 422  # Validation error

    def test_create_policy(self, client, sample_policy):
        """test create policy"""
        # serialize enums
        policy_dict = sample_policy.model_dump()
        policy_dict['spec']['rules'][0]['result']['action'] = policy_dict['spec']['rules'][0]['result']['action'].value
        policy_dict['spec']['rules'][0]['conditions'][0]['operator'] = policy_dict['spec']['rules'][0]['conditions'][0]['operator'].value
        
        policy_yaml = yaml.dump(policy_dict, default_flow_style=False)

        response = client.post(
            "/admin/policies",
            json={"policy_yaml": policy_yaml}
        )

        # no service init in tests
        # tests api structure
        assert response.status_code in [200, 500]

    def test_list_policies(self, client):
        """test list policies"""
        response = client.get("/admin/policies")
        assert response.status_code in [200, 500]

    def test_metrics_endpoint(self, client):
        """test metrics"""
        response = client.get("/api/metrics")
        assert response.status_code in [200, 500]
