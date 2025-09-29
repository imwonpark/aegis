import asyncio
import hashlib
import hmac
import json
import logging
from typing import Dict, Any, Optional
import httpx

from ..models.policy import Escalation, Severity
from ..models.api import EvaluationRequest, EvaluationResponse
from ..models.config import EscalationConfig

logger = logging.getLogger(__name__)


class EscalationManager:
    """webhook escalation"""

    def __init__(self, config: EscalationConfig, webhook_secret_key: str):
        self.config = config
        self.webhook_secret_key = webhook_secret_key
        self.http_client = httpx.AsyncClient()

    async def handle_escalation(
        self,
        escalation: Escalation,
        request: EvaluationRequest,
        response: EvaluationResponse
    ) -> bool:
        """handle escalation"""
        try:
            payload = self._build_webhook_payload(escalation, request, response)
            signature = self._sign_payload(payload)

            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Aegis-Guardrail/1.0",
                "X-Aegis-Signature": signature,
                "X-Aegis-Severity": escalation.severity.value
            }

            return await self._send_webhook_with_retry(
                escalation.webhook_url,
                payload,
                headers
            )

        except Exception as e:
            logger.error(f"Failed to handle escalation: {e}")
            return False

    def _build_webhook_payload(
        self,
        escalation: Escalation,
        request: EvaluationRequest,
        response: EvaluationResponse
    ) -> Dict[str, Any]:
        """build payload"""
        return {
            "timestamp": response.timestamp_utc,
            "severity": escalation.severity.value,
            "policy_name": response.matched_policy,
            "rule_name": response.matched_rule,
            "decision": response.decision.value,
            "reason": response.reason,
            "request": {
                "request_id": request.request_id,
                "agent": {
                    "type": request.agent.type,
                    "id": request.agent.id,
                    "ip_address": request.agent.ip_address
                },
                "action": {
                    "name": request.action.name,
                    "parameters": request.action.parameters
                },
                "context": {
                    "environment": request.context.environment.dict() if request.context.environment else None,
                    "originator": request.context.originator.dict() if request.context.originator else None,
                    "custom_fields": request.context.custom_fields
                }
            },
            "response": {
                "decision": response.decision.value,
                "reason": response.reason,
                "matched_policy": response.matched_policy,
                "matched_rule": response.matched_rule,
                "latency_ms": response.latency_ms
            }
        }

    def _sign_payload(self, payload: Dict[str, Any]) -> str:
        """sign payload"""
        payload_json = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            self.webhook_secret_key.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"

    async def _send_webhook_with_retry(
        self,
        webhook_url: str,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> bool:
        """send webhook"""
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                response = await self.http_client.post(
                    webhook_url,
                    json=payload,
                    headers=headers,
                    timeout=self.config.timeout_seconds
                )

                if response.status_code < 400:
                    logger.info(f"Successfully sent webhook to {webhook_url}")
                    return True
                else:
                    logger.warning(f"Webhook returned status {response.status_code}: {response.text}")

            except Exception as e:
                last_exception = e
                logger.warning(f"Webhook attempt {attempt + 1} failed: {e}")

                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay_seconds)

        logger.error(f"Failed to send webhook to {webhook_url} after {self.config.max_retries + 1} attempts: {last_exception}")
        return False

    async def verify_webhook_signature(
        self,
        payload: str,
        signature: str,
        timestamp: str
    ) -> bool:
        """verify signature"""
        try:
            # check timestamp for replay attacks
            expected_signature = self._sign_payload(json.loads(payload))
            return hmac.compare_digest(signature, expected_signature)
        except Exception:
            return False

    async def close(self):
        """close client"""
        await self.http_client.aclose()
