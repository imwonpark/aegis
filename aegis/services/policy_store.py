import json
import yaml
import asyncio
import logging
from typing import List, Optional, Dict, Any
import redis.asyncio as redis
import hashlib

from ..models.policy import Policy
from ..models.config import RedisConfig

logger = logging.getLogger(__name__)


class PolicyStore:
    """redis policy store"""

    def __init__(self, config: RedisConfig):
        self.config = config
        self.redis_client: Optional[redis.Redis] = None
        self._cache: Dict[str, List[Policy]] = {}  # In-memory cache for frequently accessed policies

    async def connect(self):
        """connect redis"""
        try:
            self.redis_client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                password=self.config.password,
                decode_responses=self.config.decode_responses
            )
            await self.redis_client.ping()
            logger.info("Connected to Redis policy store")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """disconnect redis"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis policy store")

    async def store_policy(self, policy: Policy) -> bool:
        """store policy"""
        try:
            policy_key = f"policy:{policy.metadata.name}"
            policy_yaml = yaml.dump(policy.dict(), default_flow_style=False)

            # store yaml
            await self.redis_client.set(policy_key, policy_yaml)

            # add to indexes
            await self._add_to_indexes(policy)

            # clear cache
            self._cache.clear()

            logger.info(f"Stored policy: {policy.metadata.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to store policy {policy.metadata.name}: {e}")
            return False

    async def get_policy(self, policy_name: str) -> Optional[Policy]:
        """get policy"""
        try:
            policy_key = f"policy:{policy_name}"
            policy_yaml = await self.redis_client.get(policy_key)

            if not policy_yaml:
                return None

            policy_dict = yaml.safe_load(policy_yaml)
            return Policy(**policy_dict)

        except Exception as e:
            logger.error(f"Failed to retrieve policy {policy_name}: {e}")
            return None

    async def delete_policy(self, policy_name: str) -> bool:
        """delete policy"""
        try:
            policy_key = f"policy:{policy_name}"

            # remove from indexes
            policy = await self.get_policy(policy_name)
            if policy:
                await self._remove_from_indexes(policy)

            # delete policy
            deleted = await self.redis_client.delete(policy_key)

            # clear cache
            self._cache.clear()

            logger.info(f"Deleted policy: {policy_name}")
            return deleted > 0

        except Exception as e:
            logger.error(f"Failed to delete policy {policy_name}: {e}")
            return False

    async def list_policies(self) -> List[Policy]:
        """list policies"""
        try:
            policy_keys = await self.redis_client.keys("policy:*")
            policies = []

            for key in policy_keys:
                policy_yaml = await self.redis_client.get(key)
                if policy_yaml:
                    policy_dict = yaml.safe_load(policy_yaml)
                    policies.append(Policy(**policy_dict))

            return policies

        except Exception as e:
            logger.error(f"Failed to list policies: {e}")
            return []

    async def get_policies_for_request(self, agent_type: str, agent_id: str, action_name: str) -> List[Policy]:
        """get matching policies"""

        # check cache
        cache_key = f"{agent_type}:{agent_id}:{action_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            matching_policies = []

            # get all
            all_policies = await self.list_policies()

            # filter matching
            for policy in all_policies:
                if self._policy_matches_request(policy, agent_type, agent_id, action_name):
                    matching_policies.append(policy)

            # cache result
            self._cache[cache_key] = matching_policies

            return matching_policies

        except Exception as e:
            logger.error(f"Failed to get policies for request: {e}")
            return []

    def _policy_matches_request(self, policy: Policy, agent_type: str, agent_id: str, action_name: str) -> bool:
        """check policy match"""
        for rule in policy.spec.rules:
            selector = rule.selector

            # quick check selectors
            if (selector.agent_type and selector.agent_type != agent_type) or \
               (selector.action_name and selector.action_name != action_name):
                continue

            # check wildcards
            if selector.agent_id:
                import re
                pattern = selector.agent_id.replace('*', '.*')
                if not re.match(f'^{pattern}$', agent_id):
                    continue

            # rule could match
            return True

        return False

    async def _add_to_indexes(self, policy: Policy):
        """add to indexes"""
        try:
            # index by type
            for rule in policy.spec.rules:
                selector = rule.selector

                if selector.agent_type:
                    index_key = f"index:agent_type:{selector.agent_type}"
                    await self.redis_client.sadd(index_key, policy.metadata.name)

                if selector.agent_id:
                    index_key = f"index:agent_id:{selector.agent_id}"
                    await self.redis_client.sadd(index_key, policy.metadata.name)

                if selector.action_name:
                    index_key = f"index:action_name:{selector.action_name}"
                    await self.redis_client.sadd(index_key, policy.metadata.name)

        except Exception as e:
            logger.error(f"Failed to add policy {policy.metadata.name} to indexes: {e}")

    async def _remove_from_indexes(self, policy: Policy):
        """remove from indexes"""
        try:
            # remove indexes
            for rule in policy.spec.rules:
                selector = rule.selector

                if selector.agent_type:
                    index_key = f"index:agent_type:{selector.agent_type}"
                    await self.redis_client.srem(index_key, policy.metadata.name)

                if selector.agent_id:
                    index_key = f"index:agent_id:{selector.agent_id}"
                    await self.redis_client.srem(index_key, policy.metadata.name)

                if selector.action_name:
                    index_key = f"index:action_name:{selector.action_name}"
                    await self.redis_client.srem(index_key, policy.metadata.name)

        except Exception as e:
            logger.error(f"Failed to remove policy {policy.metadata.name} from indexes: {e}")

    async def clear_cache(self):
        """clear cache"""
        self._cache.clear()
        logger.info("Cleared policy cache")

    async def get_cache_stats(self) -> Dict[str, Any]:
        """get cache stats"""
        return {
            "cache_size": len(self._cache),
            "cached_requests": list(self._cache.keys())
        }
