from fastapi import APIRouter, HTTPException, Depends, Request
import logging
import yaml

from ..models.api import PolicyCreateRequest, PolicyUpdateRequest, PolicyResponse, ErrorResponse
from ..models.policy import Policy
from ..services.policy_engine import PolicyEngine
from ..services.policy_store import PolicyStore
from ..core.dependencies import get_services

logger = logging.getLogger(__name__)

admin_router = APIRouter()


@admin_router.post("/policies", response_model=PolicyResponse)
async def create_policy(
    request: PolicyCreateRequest,
    services = Depends(get_services)
):
    """create policy"""
    try:
        policy_store: PolicyStore = services["policy_store"]
        policy_engine: PolicyEngine = services["policy_engine"]

        # validate yaml
        is_valid, error, policy = await policy_engine.validate_policy_yaml(request.policy_yaml)

        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid policy: {error}")

        # store policy
        success = await policy_store.store_policy(policy)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store policy")

        return PolicyResponse(
            name=policy.metadata.name,
            policy_yaml=request.policy_yaml
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating policy: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@admin_router.get("/policies")
async def list_policies(services = Depends(get_services)):
    """list policies"""
    try:
        policy_store: PolicyStore = services["policy_store"]
        policies = await policy_store.list_policies()

        return [
            {
                "name": policy.metadata.name,
                "description": policy.metadata.description,
                "rules_count": len(policy.spec.rules)
            }
            for policy in policies
        ]

    except Exception as e:
        logger.error(f"Error listing policies: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@admin_router.get("/policies/{policy_name}")
async def get_policy(
    policy_name: str,
    services = Depends(get_services)
):
    """get policy"""
    try:
        policy_store: PolicyStore = services["policy_store"]
        policy = await policy_store.get_policy(policy_name)

        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found")

        return PolicyResponse(
            name=policy.metadata.name,
            policy_yaml=yaml.dump(policy.dict(), default_flow_style=False)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting policy {policy_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@admin_router.put("/policies/{policy_name}")
async def update_policy(
    policy_name: str,
    request: PolicyUpdateRequest,
    services = Depends(get_services)
):
    """update policy"""
    try:
        policy_store: PolicyStore = services["policy_store"]
        policy_engine: PolicyEngine = services["policy_engine"]

        # check exists
        existing_policy = await policy_store.get_policy(policy_name)
        if not existing_policy:
            raise HTTPException(status_code=404, detail="Policy not found")

        # validate yaml
        is_valid, error, new_policy = await policy_engine.validate_policy_yaml(request.policy_yaml)

        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid policy: {error}")

        # check name match
        if new_policy.metadata.name != policy_name:
            raise HTTPException(status_code=400, detail="Policy name in YAML must match URL parameter")

        # replace policy
        await policy_store.delete_policy(policy_name)
        success = await policy_store.store_policy(new_policy)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to update policy")

        return PolicyResponse(
            name=new_policy.metadata.name,
            policy_yaml=request.policy_yaml
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating policy {policy_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@admin_router.delete("/policies/{policy_name}")
async def delete_policy(
    policy_name: str,
    services = Depends(get_services)
):
    """delete policy"""
    try:
        policy_store: PolicyStore = services["policy_store"]

        # check exists
        existing_policy = await policy_store.get_policy(policy_name)
        if not existing_policy:
            raise HTTPException(status_code=404, detail="Policy not found")

        # delete policy
        success = await policy_store.delete_policy(policy_name)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete policy")

        return {"message": f"Policy {policy_name} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting policy {policy_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@admin_router.post("/policies/{policy_name}/validate")
async def validate_policy(
    policy_name: str,
    request: PolicyCreateRequest,
    services = Depends(get_services)
):
    """validate policy yaml"""
    try:
        policy_engine: PolicyEngine = services["policy_engine"]

        is_valid, error, policy = await policy_engine.validate_policy_yaml(request.policy_yaml)

        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid policy: {error}")

        return {
            "valid": True,
            "policy_name": policy.metadata.name,
            "description": policy.metadata.description,
            "rules_count": len(policy.spec.rules)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating policy: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@admin_router.get("/cache/stats")
async def get_cache_stats(services = Depends(get_services)):
    """get cache stats"""
    try:
        policy_store: PolicyStore = services["policy_store"]
        stats = await policy_store.get_cache_stats()

        return stats

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@admin_router.post("/cache/clear")
async def clear_cache(services = Depends(get_services)):
    """clear cache"""
    try:
        policy_store: PolicyStore = services["policy_store"]
        await policy_store.clear_cache()

        return {"message": "Cache cleared successfully"}

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
