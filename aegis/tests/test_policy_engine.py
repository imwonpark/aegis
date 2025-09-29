import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from ..models.api import EvaluationRequest
from ..models.policy import Policy, ActionDecision
from ..services.policy_engine import PolicyEngine
from ..services.policy_store import PolicyStore


class TestPolicyEngine:
    """policy engine tests"""

    @pytest.fixture
    def sample_policy(self):
        """sample policy"""
        return Policy(
            apiVersion="aegis.io/v1",
            kind="Policy",
            metadata={
                "name": "test-policy",
                "description": "Test policy"
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

    @pytest.fixture
    def sample_request(self):
        """sample request"""
        return EvaluationRequest(
            request_id="test-123",
            agent={
                "type": "thermostat",
                "id": "thermo-1",
                "ip_address": "192.168.1.100"
            },
            action={
                "name": "set_temperature",
                "parameters": {
                    "temperature_celsius": 25
                }
            },
            context={
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
        )

    @pytest.fixture
    def mock_policy_store(self, sample_policy):
        """mock store"""
        mock_store = AsyncMock(spec=PolicyStore)
        mock_store.get_policies_for_request.return_value = [sample_policy]
        return mock_store

    def test_policy_yaml_validation_valid(self, sample_policy):
        """test valid yaml"""
        import yaml

        policy_engine = PolicyEngine(policy_store=AsyncMock())

        # serialize enums properly
        policy_dict = sample_policy.model_dump()
        # convert enums
        policy_dict['spec']['rules'][0]['result']['action'] = policy_dict['spec']['rules'][0]['result']['action'].value
        policy_dict['spec']['rules'][0]['conditions'][0]['operator'] = policy_dict['spec']['rules'][0]['conditions'][0]['operator'].value
        
        policy_yaml = yaml.dump(policy_dict, default_flow_style=False)
        is_valid, error, parsed_policy = asyncio.run(
            policy_engine.validate_policy_yaml(policy_yaml)
        )

        assert is_valid is True
        assert error is None
        assert parsed_policy.metadata.name == "test-policy"

    def test_policy_yaml_validation_invalid(self):
        """test invalid yaml"""
        policy_engine = PolicyEngine(policy_store=AsyncMock())

        invalid_yaml = "invalid: yaml: content: ["
        is_valid, error, parsed_policy = asyncio.run(
            policy_engine.validate_policy_yaml(invalid_yaml)
        )

        assert is_valid is False
        assert error is not None
        assert parsed_policy is None

    def test_evaluate_request_with_matching_policy(self, mock_policy_store, sample_request):
        """test matching policy"""
        policy_engine = PolicyEngine(
            policy_store=mock_policy_store,
            default_decision=ActionDecision.ALLOW
        )

        response = asyncio.run(policy_engine.evaluate_request(sample_request))

        assert response.request_id == "test-123"
        assert response.decision == ActionDecision.DENY
        assert response.matched_policy == "test-policy"
        assert response.matched_rule == "test-rule"
        assert response.reason == "Temperature too high"

    def test_evaluate_request_no_matching_policy(self, sample_request):
        """test no matching policy"""
        mock_store = AsyncMock(spec=PolicyStore)
        mock_store.get_policies_for_request.return_value = []

        policy_engine = PolicyEngine(
            policy_store=mock_store,
            default_decision=ActionDecision.ALLOW
        )

        response = asyncio.run(policy_engine.evaluate_request(sample_request))

        assert response.decision == ActionDecision.ALLOW
        assert response.matched_policy is None
        assert response.matched_rule is None
        assert "No policies matched" in response.reason

    def test_evaluate_request_with_allow_policy(self, sample_policy, sample_request):
        """test allow policy"""
        # modify policy to allow temp
        sample_policy.spec.rules[0].conditions[0].value = 20  # Lower than 25
        sample_policy.spec.rules[0].result.action = ActionDecision.ALLOW

        mock_store = AsyncMock(spec=PolicyStore)
        mock_store.get_policies_for_request.return_value = [sample_policy]

        policy_engine = PolicyEngine(
            policy_store=mock_store,
            default_decision=ActionDecision.DENY
        )

        response = asyncio.run(policy_engine.evaluate_request(sample_request))

        assert response.decision == ActionDecision.ALLOW
        assert response.matched_policy == "test-policy"
        assert response.matched_rule == "test-rule"
