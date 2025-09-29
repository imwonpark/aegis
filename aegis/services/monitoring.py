import json
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import time

from ..models.api import EvaluationRequest, EvaluationResponse
from ..models.policy import ActionDecision

logger = logging.getLogger(__name__)


class MonitoringService:
    """logging and monitoring"""

    def __init__(self, enable_json: bool = False):
        self.enable_json = enable_json
        self._setup_logging()

    def _setup_logging(self):
        """setup logging"""
        # aegis decision logger
        self.aegis_logger = logging.getLogger("aegis.decisions")

        if self.enable_json:
            # json formatter
            class JSONFormatter(logging.Formatter):
                def format(self, record):
                    log_entry = {
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "level": record.levelname,
                        "logger": record.name,
                        "message": record.getMessage(),
                    }

                    # add extra fields
                    if hasattr(record, 'decision'):
                        log_entry.update({
                            "decision": record.decision,
                            "latency_ms": getattr(record, 'latency_ms', None),
                            "matched_policy": getattr(record, 'matched_policy', None),
                            "matched_rule": getattr(record, 'matched_rule', None),
                            "request_id": getattr(record, 'request_id', None),
                        })

                    return json.dumps(log_entry)

            handler = logging.StreamHandler()
            handler.setFormatter(JSONFormatter())
            self.aegis_logger.addHandler(handler)
            self.aegis_logger.setLevel(logging.INFO)
            self.aegis_logger.propagate = False

    async def log_evaluation(
        self,
        request: EvaluationRequest,
        response: EvaluationResponse,
        processing_time_ms: int
    ):
        """log evaluation"""

        # create log record
        extra_data = {
            'decision': response.decision.value,
            'latency_ms': response.latency_ms,
            'matched_policy': response.matched_policy,
            'matched_rule': response.matched_rule,
            'request_id': request.request_id,
        }

        # log by decision level
        if response.decision == ActionDecision.DENY:
            self.aegis_logger.warning(f"Request denied: {response.reason}", extra=extra_data)
        elif response.decision == ActionDecision.FLAG:
            self.aegis_logger.warning(f"Request flagged: {response.reason}", extra=extra_data)
        else:
            self.aegis_logger.info(f"Request allowed", extra=extra_data)

        # audit trail
        audit_log = {
            "timestamp": response.timestamp_utc,
            "service_name": "aegis-guardrail",
            "log_level": "INFO",
            "decision": response.decision.value,
            "latency_ms": response.latency_ms,
            "matched_policy": response.matched_policy,
            "matched_rule": response.matched_rule,
            "request": request.model_dump(),
            "response": response.model_dump()
        }

        # log audit
        self.aegis_logger.info(f"Audit log: {json.dumps(audit_log)}", extra=extra_data)

    async def log_error(self, error: str, request_id: Optional[str] = None, **kwargs):
        """log error"""
        extra_data = kwargs.copy()
        if request_id:
            extra_data['request_id'] = request_id

        self.aegis_logger.error(f"Error: {error}", extra=extra_data)

    async def log_metric(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """log metric"""
        metric_data = {
            "metric": metric_name,
            "value": value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if tags:
            metric_data["tags"] = tags

        self.aegis_logger.info(f"Metric: {json.dumps(metric_data)}")

    async def get_stats(self) -> Dict[str, Any]:
        """get stats"""
        # track in memory or metrics store
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": "aegis-guardrail",
            "version": "1.0.0",
            "uptime_seconds": time.time(),  # This would be actual uptime
            "requests_processed": 0,  # Would be tracked
            "decisions_by_type": {
                "allow": 0,
                "deny": 0,
                "flag": 0
            },
            "average_latency_ms": 0.0,
            "error_count": 0
        }
