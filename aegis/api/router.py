from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
import time
import logging

from ..models.api import EvaluationRequest, EvaluationResponse, ErrorResponse
from ..models.config import Config
from ..services.policy_engine import PolicyEngine
from ..services.policy_store import PolicyStore
from ..services.monitoring import MonitoringService
from ..services.escalation_manager import EscalationManager
from ..core.dependencies import get_config, get_services
from ..core.auth import verify_api_key
from .admin import admin_router

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/v1/evaluate", response_model=EvaluationResponse)
async def evaluate_action(
    request: EvaluationRequest,
    req: Request,
    authenticated: bool = Depends(verify_api_key),
    config: Config = Depends(get_config),
    services = Depends(get_services)
):
    """evaluate action against policies"""
    start_time = time.time()

    try:
        # validate request
        if not request.request_id:
            raise HTTPException(status_code=400, detail="request_id is required")

        if not request.agent or not request.agent.type or not request.agent.id:
            raise HTTPException(status_code=400, detail="agent.type and agent.id are required")

        if not request.action or not request.action.name:
            raise HTTPException(status_code=400, detail="action.name is required")

        # evaluate request
        policy_engine: PolicyEngine = services["policy_engine"]
        escalation_manager: EscalationManager = services["escalation_manager"]
        monitoring: MonitoringService = services["monitoring"]

        response = await policy_engine.evaluate_request(request)

        # handle escalations
        if response.matched_policy and response.matched_rule:
            # check for escalations
            policy_store: PolicyStore = services["policy_store"]
            policy = await policy_store.get_policy(response.matched_policy)

            if policy:
                # find rule escalation
                for rule in policy.spec.rules:
                    if rule.name == response.matched_rule and rule.result.on_match:
                        await escalation_manager.handle_escalation(
                            rule.result.on_match,
                            request,
                            response
                        )

        # log evaluation
        processing_time_ms = int((time.time() - start_time) * 1000)
        await monitoring.log_evaluation(request, response, processing_time_ms)

        # log metrics
        await monitoring.log_metric("request_latency", response.latency_ms, {
            "decision": response.decision.value,
            "matched_policy": response.matched_policy or "none"
        })

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error evaluating request {request.request_id}: {e}")

        # log error
        monitoring: MonitoringService = services["monitoring"]
        await monitoring.log_error(str(e), request.request_id if 'request' in locals() else None)

        error_response = ErrorResponse(
            error="Internal server error",
            error_code="INTERNAL_ERROR",
            request_id=request.request_id if 'request' in locals() else None
        )

        return JSONResponse(
            status_code=500,
            content=error_response.model_dump()
        )


@router.get("/health")
async def health_check(services = Depends(get_services)):
    """health check"""
    try:
        # check redis
        policy_store: PolicyStore = services["policy_store"]
        await policy_store.redis_client.ping()

        return {"status": "healthy", "service": "aegis-guardrail"}

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )


@router.get("/metrics")
async def get_metrics(services = Depends(get_services)):
    """get metrics"""
    try:
        monitoring: MonitoringService = services["monitoring"]
        stats = await monitoring.get_stats()

        return stats

    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to retrieve metrics"}
        )
