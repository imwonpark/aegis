import asyncio
import yaml
import logging
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
import time

from ..models.policy import Policy, Rule, matches_selector, evaluate_condition, ActionDecision
from ..models.api import EvaluationRequest, EvaluationResponse

logger = logging.getLogger(__name__)


class PolicyEngine:
    """policy engine"""

    def __init__(self, policy_store, default_decision: ActionDecision = ActionDecision.ALLOW):
        self.policy_store = policy_store
        self.default_decision = default_decision

    async def evaluate_request(self, request: EvaluationRequest) -> EvaluationResponse:
        """eval request"""
        start_time = time.time()

        try:
            # get policies
            policies = await self.policy_store.get_policies_for_request(
                request.agent.type,
                request.agent.id,
                request.action.name
            )

            logger.debug(f"Found {len(policies)} policies for request {request.request_id}")

            # eval policies
            for policy in policies:
                result = await self._evaluate_policy(policy, request)
                if result:
                    latency_ms = int((time.time() - start_time) * 1000)
                    return EvaluationResponse(
                        request_id=request.request_id,
                        decision=result["decision"],
                        reason=result["reason"],
                        matched_policy=policy.metadata.name,
                        matched_rule=result["rule_name"],
                        latency_ms=latency_ms
                    )

            # no match = default
            latency_ms = int((time.time() - start_time) * 1000)
            return EvaluationResponse(
                request_id=request.request_id,
                decision=self.default_decision.value,
                reason="No policies matched the request",
                latency_ms=latency_ms
            )

        except Exception as e:
            logger.error(f"Error evaluating request {request.request_id}: {e}")
            latency_ms = int((time.time() - start_time) * 1000)
            return EvaluationResponse(
                request_id=request.request_id,
                decision=self.default_decision.value,
                reason=f"Evaluation error: {str(e)}",
                latency_ms=latency_ms
            )

    async def _evaluate_policy(self, policy: Policy, request: EvaluationRequest) -> Optional[Dict[str, Any]]:
        """eval policy"""

        # merge context
        context_data = self._build_context_data(request)

        # eval rules
        for rule in policy.spec.rules:
            if await self._evaluate_rule(rule, request, context_data):
                return {
                    "decision": rule.result.action.value,
                    "reason": rule.result.message,
                    "rule_name": rule.name
                }

        return None

    async def _evaluate_rule(self, rule: Rule, request: EvaluationRequest, context_data: Dict[str, Any]) -> bool:
        """eval rule"""

        # check selector
        if not matches_selector(
            rule.selector,
            request.agent.type,
            request.agent.id,
            request.action.name
        ):
            return False

        # eval conditions
        for condition in rule.conditions:
            if not evaluate_condition(condition, context_data):
                return False

        return True

    def _build_context_data(self, request: EvaluationRequest) -> Dict[str, Any]:
        """build context"""
        context = {}

        # add agent
        context["agent"] = {
            "type": request.agent.type,
            "id": request.agent.id,
            "ip_address": request.agent.ip_address
        }

        # add action
        context["action"] = {
            "name": request.action.name,
            "parameters": request.action.parameters
        }

        # add env
        if request.context.environment:
            context["environment"] = {
                "time_of_day_utc": request.context.environment.time_of_day_utc,
                "location": request.context.environment.location,
                "is_occupied": request.context.environment.is_occupied
            }

        # add originator
        if request.context.originator:
            context["originator"] = {
                "type": request.context.originator.type,
                "id": request.context.originator.id
            }

        # add custom
        if request.context.custom_fields:
            context.update(request.context.custom_fields)

        return context

    async def validate_policy_yaml(self, policy_yaml: str) -> Tuple[bool, Optional[str], Optional[Policy]]:
        """validate yaml"""
        try:
            policy_dict = yaml.safe_load(policy_yaml)
            if not policy_dict:
                return False, "Empty or invalid YAML", None

            policy = Policy(**policy_dict)
            return True, None, policy

        except yaml.YAMLError as e:
            return False, f"Invalid YAML: {e}", None
        except Exception as e:
            return False, f"Policy validation error: {e}", None
