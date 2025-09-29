from typing import Dict, Any
import logging
from fastapi import Depends, HTTPException

from ..models.config import Config
from ..services.policy_store import PolicyStore
from ..services.policy_engine import PolicyEngine
from ..services.monitoring import MonitoringService
from ..services.escalation_manager import EscalationManager

logger = logging.getLogger(__name__)

# global services
_services: Dict[str, Any] = {}


def get_config() -> Config:
    """get config"""
    # load from env vars, config files, etc
    return Config()


def get_services() -> Dict[str, Any]:
    """get services"""
    global _services

    if not _services:
        try:
            config = get_config()

            # init services
            policy_store = PolicyStore(config.redis_config)

            # init redis
            import asyncio
            asyncio.run(policy_store.connect())

            policy_engine = PolicyEngine(
                policy_store=policy_store,
                default_decision=config.default_decision
            )

            monitoring = MonitoringService(enable_json=config.log_config.enable_json)

            escalation_manager = EscalationManager(
                config=config.escalation_config,
                webhook_secret_key=config.security_config.webhook_secret_key
            )

            _services = {
                "config": config,
                "policy_store": policy_store,
                "policy_engine": policy_engine,
                "monitoring": monitoring,
                "escalation_manager": escalation_manager
            }

            logger.info("Services initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise HTTPException(status_code=500, detail="Service initialization failed")

    return _services


async def cleanup_services():
    """cleanup services"""
    global _services

    if _services:
        try:
            policy_store: PolicyStore = _services.get("policy_store")
            if policy_store:
                await policy_store.disconnect()

            escalation_manager: EscalationManager = _services.get("escalation_manager")
            if escalation_manager:
                await escalation_manager.close()

            logger.info("Services cleaned up successfully")

        except Exception as e:
            logger.error(f"Error during service cleanup: {e}")
        finally:
            _services.clear()
